"""Метод весов доказательств (Weights of Evidence, WoE).

Идея в двух словах
------------------
Территория разбита на ячейки. Для каждого признака (например, «высота»)
значения делим на интервалы (бины). Для каждого интервала считаем вес:

    W = ln( доля известных месторождений в интервале
            / доля всех остальных ячеек в интервале )

W > 0: месторождения встречаются в этом интервале чаще, чем «фон».
W < 0: реже. W = 0: так же часто.

Оценка ячейки (score) = сумма весов по всем её признакам.
Это счёт для ранжирования, а НЕ вероятность месторождения.

Важно: ячейки без месторождения (is_deposit = 0) — это «неразмеченный фон»
(Unlabeled), а не доказанное отсутствие золота.

Два переключателя (по умолчанию — прежнее поведение, чтобы старые результаты
воспроизводились; новое включается явно и записывается в журнал решений):

categorical_prior
    "uniform"    — классическое сглаживание.
    "background" — для категорий «виртуальные» месторождения распределяются как
                   фон. Редкая категория с одним объектом не получает раздутый вес.
missing_as_neutral
    False — пропуск в категориальном признаке считается отдельной категорией.
    True  — пропуск, 'unknown', 'cover' = «нет сведений»: вклад 0, в обучении не участвуют.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

TARGET = "is_deposit"  # 1 — известное месторождение, 0 — фон
FOLD = "fold_id"  # номер пространственного фолда
MISSING = "<missing>"  # название категории для пропуска (если он не нейтральный)
UNKNOWN_CATEGORIES = {"", "unknown", "cover", "nan", "none", "<na>"}  # = «нет сведений»
PRIORS = ("background", "uniform")


# ---------------------------------------------------------------- подготовка

def _category_values(series: pd.Series, missing_as_neutral: bool = False) -> pd.Series:
    """Категории как строки.

    missing_as_neutral=True : пропуск, 'unknown', 'cover' и т.п. -> NaN (нет сведений).
    missing_as_neutral=False: пропуск -> категория "<missing>"; остальное как есть.
    """
    values = series.astype("string").str.strip()
    if not missing_as_neutral:
        return values.fillna(MISSING).astype(object)
    unknown = values.isna() | values.str.lower().isin(UNKNOWN_CATEGORIES)
    out = values.mask(unknown).astype(object)
    return out.where(out.notna(), np.nan)


def _quantile_edges(series: pd.Series, n_bins: int) -> np.ndarray:
    """Границы интервалов по квантилям. Считаем ТОЛЬКО по переданным (train) данным."""
    values = pd.to_numeric(series, errors="coerce")
    values = values[np.isfinite(values)]
    if values.empty:
        return np.array([-np.inf, np.inf])
    edges = np.unique(np.quantile(values, np.linspace(0, 1, n_bins + 1)))
    if len(edges) < 2:  # признак-константа: один интервал, вес 0
        return np.array([-np.inf, np.inf])
    edges[0], edges[-1] = -np.inf, np.inf  # крайние интервалы открыты
    return edges.astype(float)


def _numeric_ids(values: pd.Series, edges: np.ndarray) -> pd.Series:
    """Номер интервала для каждого значения; NaN, если значения нет."""
    numeric = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return pd.Series(pd.cut(numeric, bins=edges, labels=False, include_lowest=True), index=values.index)


def _interval_labels(edges: np.ndarray) -> list:
    """Подписи интервалов (для чтения человеком и для model[...]['table'])."""
    return [str(c) for c in pd.cut(pd.Series([], dtype=float), bins=edges, include_lowest=True).cat.categories]


def _weights(pos_counts, unl_counts, n_pos, n_unl, alpha, prior) -> np.ndarray:
    """Веса интервалов/категорий со сглаживанием alpha (см. описание prior в начале файла)."""
    k = len(pos_counts)
    if k == 0 or n_pos == 0 or n_unl == 0:
        return np.zeros(k)  # нет сведений -> нейтрально
    p_unl = (unl_counts + alpha) / (n_unl + alpha * k)
    if prior == "background":
        mass = alpha * k
        p_pos = (pos_counts + mass * p_unl) / (n_pos + mass)
    else:
        p_pos = (pos_counts + alpha) / (n_pos + alpha * k)
    return np.log(p_pos / p_unl)


# ------------------------------------------------------------------- обучение

def fit_woe(train, features, n_bins=5, alpha=0.5, categorical=(), categorical_prior="uniform",
            missing_as_neutral=False):
    """Обучает таблицы весов. Возвращает словарь «признак -> модель признака».

    train        — таблица ячеек; ДОЛЖНА содержать только обучающие фолды
                   (иначе в оценку качества утечёт информация о тесте).
    features     — какие столбцы использовать.
    n_bins       — на сколько интервалов делить числовые признаки.
    alpha        — сглаживание, чтобы не брать логарифм от нуля.
    categorical  — какие из features категориальные (например, литология).
    """
    if alpha <= 0:
        raise ValueError("alpha должен быть > 0.")
    if categorical_prior not in PRIORS:
        raise ValueError(f"categorical_prior должен быть одним из {PRIORS}.")
    is_pos, is_unl = train[TARGET].eq(1), train[TARGET].eq(0)
    if not is_pos.any() or not is_unl.any():
        raise ValueError("В train должны быть и месторождения, и фон.")

    model = {}
    for feature in features:
        is_cat = feature in categorical
        if is_cat:
            values = _category_values(train[feature], missing_as_neutral)
            levels = sorted(values.dropna().unique().tolist())
            ids = values.map({name: i for i, name in enumerate(levels)})
            labels, edges = levels, None
        else:
            edges = _quantile_edges(train[feature], n_bins)
            ids = _numeric_ids(train[feature], edges)
            levels = list(range(len(edges) - 1))
            labels = _interval_labels(edges)
        k = len(levels)
        valid = ids.notna()
        pos_counts = np.bincount(ids[valid & is_pos].to_numpy(dtype=int), minlength=k)
        unl_counts = np.bincount(ids[valid & is_unl].to_numpy(dtype=int), minlength=k)
        if missing_as_neutral:  # «нет сведений» не входит и в знаменатель
            n_pos, n_unl = int(pos_counts.sum()), int(unl_counts.sum())
        else:  # прежнее поведение: знаменатель — все строки класса
            n_pos, n_unl = int(is_pos.sum()), int(is_unl.sum())
        weights = _weights(pos_counts, unl_counts, n_pos, n_unl, alpha, categorical_prior if is_cat else "uniform")
        model[feature] = {
            "categorical": is_cat,
            "missing_as_neutral": bool(missing_as_neutral),
            "edges": edges,
            "levels": labels,
            "weights": weights,
            "table": dict(zip(labels, weights.tolist())),
            "positive_count": pos_counts.tolist(),
            "unlabeled_count": unl_counts.tolist(),
        }
    return model


# --------------------------------------------------------------------- оценка

def _ids_for(data: pd.DataFrame, feature: str, m: dict):
    """(номера уровней или NaN, «нет сведений», «неизвестный уровень»)."""
    if m["categorical"]:
        values = _category_values(data[feature], m["missing_as_neutral"])
        ids = values.map({name: i for i, name in enumerate(m["levels"])})
        missing = values.isna() if m["missing_as_neutral"] else data[feature].isna()
        unseen = values.notna() & ids.isna()
    else:
        ids = _numeric_ids(data[feature], m["edges"])
        missing = ids.isna()
        unseen = pd.Series(False, index=data.index)
    return ids, missing, unseen


def woe_contributions(data: pd.DataFrame, model: dict) -> pd.DataFrame:
    """Вклад каждого признака в оценку: одна строка на ячейку, один столбец на признак.

    Пропуск значения или неизвестная категория дают вклад 0 (нейтрально).
    """
    result = {}
    for feature, m in model.items():
        ids, _, _ = _ids_for(data, feature, m)
        contribution = np.zeros(len(data))
        ok = ids.notna().to_numpy()
        if ok.any():
            contribution[ok] = m["weights"][ids[ok].to_numpy(dtype=int)]
        result[feature] = contribution
    return pd.DataFrame(result, index=data.index)


def score_woe(data: pd.DataFrame, model: dict) -> pd.Series:
    """Итоговая оценка ячейки = сумма вкладов признаков (это не вероятность)."""
    contributions = woe_contributions(data, model)
    score = pd.Series(0.0, index=data.index, dtype=float)
    for feature in contributions.columns:  # суммируем по порядку признаков
        score = score.add(contributions[feature])
    return score


def coverage_audit(data: pd.DataFrame, model: dict) -> pd.DataFrame:
    """Аудит покрытия: сколько ячеек без сведений / с неизвестной категорией, по признакам."""
    rows = []
    for feature, m in model.items():
        _, missing, unseen = _ids_for(data, feature, m)
        rows.append({"feature": feature, "test_missing": int(missing.sum()),
                     "test_unseen": int(unseen.sum()), "test_cells": len(data)})
    return pd.DataFrame(rows)


def explain_cell(row: pd.Series, model: dict) -> pd.DataFrame:
    """Объяснение оценки одной ячейки: значение признака, вклад, по убыванию вклада.

    Это то, что увидит геолог по клику на ячейку (ФТ-4/ФТ-5).
    """
    contributions = woe_contributions(row.to_frame().T, model).iloc[0]
    out = pd.DataFrame(
        {
            "feature": list(contributions.index),
            "value": [row[f] for f in contributions.index],
            "contribution": contributions.to_numpy(),
        }
    )
    return out.sort_values("contribution", ascending=False, ignore_index=True)


# ---------- сохранение и загрузка модели (JSON) ----------

def _edge_to_json(value: float):
    return "-inf" if value == -np.inf else "inf" if value == np.inf else float(value)


def save_model(model: dict, path) -> None:
    """Сохраняет модель в JSON (границы интервалов, подписи, веса, режим пропусков)."""
    payload = {}
    for feature, m in model.items():
        item = {"categorical": m["categorical"], "missing_as_neutral": m["missing_as_neutral"],
                "levels": list(m["levels"]), "weights": [float(w) for w in m["weights"]]}
        if not m["categorical"]:
            item["edges"] = [_edge_to_json(e) for e in m["edges"]]
        payload[feature] = item
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_model(path) -> dict:
    """Читает модель, сохранённую save_model."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    model = {}
    for feature, m in payload.items():
        weights = np.array(m["weights"], dtype=float)
        edges = None if m["categorical"] else np.array([float(e) for e in m["edges"]])
        model[feature] = {
            "categorical": m["categorical"], "missing_as_neutral": m.get("missing_as_neutral", False),
            "edges": edges, "levels": m["levels"], "weights": weights,
            "table": dict(zip(m["levels"], weights.tolist())),
        }
    return model
