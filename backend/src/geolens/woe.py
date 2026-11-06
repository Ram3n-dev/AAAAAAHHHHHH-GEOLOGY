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
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

TARGET = "is_deposit"  # 1 — известное месторождение, 0 — фон
FOLD = "fold_id"  # номер пространственного фолда
MISSING = "<missing>"  # название категории для пропуска в категориальном признаке


def _quantile_edges(series: pd.Series, n_bins: int) -> np.ndarray:
    """Границы интервалов по квантилям. Считаем ТОЛЬКО по переданным (train) данным."""
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return np.array([-np.inf, np.inf], dtype=float)
    edges = np.unique(np.quantile(values, np.linspace(0, 1, n_bins + 1)))
    if len(edges) < 2:
        return np.array([-np.inf, np.inf], dtype=float)
    edges[0], edges[-1] = -np.inf, np.inf  # крайние интервалы открыты
    return edges.astype(float)


def _log_ratio(pos_count, unl_count, pos_den, unl_den, alpha) -> float:
    """ln((доля среди месторождений) / (доля среди фона)) со сглаживанием alpha."""
    return float(np.log(((pos_count + alpha) / pos_den) / ((unl_count + alpha) / unl_den)))


def fit_woe(train, features, n_bins=5, alpha=0.5, categorical=()):
    """Обучает таблицы весов. Возвращает словарь «признак -> модель признака».

    train        — таблица ячеек; ДОЛЖНА содержать только обучающие фолды
                   (иначе в оценку качества утечёт информация о тесте).
    features     — какие столбцы использовать.
    n_bins       — на сколько интервалов делить числовые признаки.
    alpha        — сглаживание, чтобы не брать логарифм от нуля.
    categorical  — какие из features категориальные (например, литология).
    """
    pos = train.loc[train[TARGET].eq(1)]
    unl = train.loc[train[TARGET].eq(0)]
    if len(pos) == 0 or len(unl) == 0:
        raise ValueError("В train должны быть и месторождения, и фон.")
    if alpha <= 0:
        raise ValueError("alpha должен быть > 0.")

    model = {}
    for feature in features:
        if feature in categorical:
            p = pos[feature].fillna(MISSING).astype(str)
            u = unl[feature].fillna(MISSING).astype(str)
            categories = sorted(set(p.unique()) | set(u.unique()))
            p_counts, u_counts = p.value_counts(), u.value_counts()
            k = max(len(categories), 1)
            p_den, u_den = len(p) + alpha * k, len(u) + alpha * k
            table = {
                c: _log_ratio(p_counts.get(c, 0), u_counts.get(c, 0), p_den, u_den, alpha)
                for c in categories
            }
            model[feature] = {"categorical": True, "edges": None, "table": table}
        else:
            edges = _quantile_edges(train[feature], n_bins)
            p_bins = pd.cut(pd.to_numeric(pos[feature], errors="coerce"), bins=edges, include_lowest=True)
            u_bins = pd.cut(pd.to_numeric(unl[feature], errors="coerce"), bins=edges, include_lowest=True)
            categories = list(p_bins.cat.categories)
            p_counts = p_bins.value_counts().reindex(categories, fill_value=0)
            u_counts = u_bins.value_counts().reindex(categories, fill_value=0)
            k = max(len(categories), 1)
            p_den, u_den = len(pos) + alpha * k, len(unl) + alpha * k
            table = {
                c: _log_ratio(p_counts.loc[c], u_counts.loc[c], p_den, u_den, alpha)
                for c in categories
            }
            model[feature] = {"categorical": False, "edges": edges, "table": table}
    return model


def woe_contributions(data: pd.DataFrame, model: dict) -> pd.DataFrame:
    """Вклад каждого признака в оценку: одна строка на ячейку, один столбец на признак.

    Пропуск значения или неизвестная категория дают вклад 0 (нейтрально).
    """
    result = {}
    for feature, m in model.items():
        if m["categorical"]:
            values = data[feature].fillna(MISSING).astype(str)
        else:
            values = pd.cut(
                pd.to_numeric(data[feature], errors="coerce"),
                bins=m["edges"],
                include_lowest=True,
            )
        contribution = pd.to_numeric(values.map(m["table"]), errors="coerce").fillna(0.0)
        result[feature] = contribution.astype(float)
    return pd.DataFrame(result, index=data.index)


def score_woe(data: pd.DataFrame, model: dict) -> pd.Series:
    """Итоговая оценка ячейки = сумма вкладов признаков (это не вероятность)."""
    contributions = woe_contributions(data, model)
    score = pd.Series(0.0, index=data.index, dtype=float)
    for feature in contributions.columns:  # суммируем по порядку, как раньше
        score = score.add(contributions[feature])
    return score


def explain_cell(row: pd.Series, model: dict) -> pd.DataFrame:
    """Объяснение оценки одной ячейки: значение признака, вклад, по убыванию вклада.

    Это то, что увидит геолог по клику на ячейку (ФТ-4/ФТ-5).
    """
    one = row.to_frame().T
    contributions = woe_contributions(one, model).iloc[0]
    out = pd.DataFrame(
        {
            "feature": list(contributions.index),
            "value": [row[f] for f in contributions.index],
            "contribution": contributions.to_numpy(),
        }
    )
    return out.sort_values("contribution", ascending=False, ignore_index=True)


# ---------- сохранение и загрузка модели (JSON) ----------

def save_model(model: dict, path) -> None:
    """Сохраняет модель в JSON: границы интервалов и веса по порядку интервалов."""
    payload = {}
    for feature, m in model.items():
        if m["categorical"]:
            payload[feature] = {"categorical": True, "weights": m["table"]}
        else:
            payload[feature] = {
                "categorical": False,
                "edges": [float(e) for e in m["edges"]],
                "weights": [float(w) for w in m["table"].values()],
            }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_model(path) -> dict:
    """Читает модель, сохранённую save_model."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    model = {}
    for feature, m in payload.items():
        if m["categorical"]:
            model[feature] = {"categorical": True, "edges": None, "table": dict(m["weights"])}
        else:
            edges = np.array(m["edges"], dtype=float)
            # Ключи таблицы должны быть теми же интервалами, что даёт pd.cut при
            # оценке (он округляет подписи границ), поэтому берём их оттуда же.
            intervals = pd.cut(pd.Series([], dtype=float), bins=edges, include_lowest=True).cat.categories
            model[feature] = {
                "categorical": False,
                "edges": edges,
                "table": dict(zip(intervals, m["weights"])),
            }
    return model
