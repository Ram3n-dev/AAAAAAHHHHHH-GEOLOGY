"""Пространственная кросс-валидация.

Каждый фолд по очереди становится «тестом»: модель обучаем на остальных фолдах,
а оцениваем только на исключённом. Так мы проверяем, умеет ли метод находить
месторождения на территории, которой он «не видел».

Буфер (buffer_km): из обучения убираются ячейки ближе buffer_km к любой тестовой
ячейке. Соседние ячейки похожи (пространственная автокорреляция), и без буфера
на границе фолдов тест «подсматривает» в соседей из train.

Модель — любой объект с методами .fit(train) -> self, .score(data) -> массив
и (необязательно) .coverage(data). Для CV передаётся фабрика: функция без
аргументов, возвращающая НОВУЮ модель (в каждом фолде обучаем заново).
"""

from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .metrics import TOP_FRACTIONS, deposit_ranks_in_test_fold, tie_aware_topk
from .models import WoEModel
from .woe import FOLD, TARGET


def split_fold(data: pd.DataFrame, fold, buffer_km: float = 0.0):
    """Маски (train, test) для фолда и число ячеек train, выброшенных буфером.

    train = все остальные фолды, минус ячейки ближе buffer_km к тестовым.
    """
    test = data[FOLD].eq(fold)
    train = ~test
    dropped = 0
    if buffer_km > 0 and test.any() and train.any():
        distance, _ = cKDTree(data.loc[test, ["x", "y"]].to_numpy()).query(data.loc[train, ["x", "y"]].to_numpy())
        near = distance < buffer_km * 1000.0
        train_index = data.index[train]
        train = pd.Series(False, index=data.index)
        train.loc[train_index[~near]] = True
        dropped = int(near.sum())
    return train, test, dropped


def run_spatial_cv(data, factory, fractions=TOP_FRACTIONS, buffer_km: float = 0.0) -> dict:
    """Полная пространственная кросс-валидация.

    Возвращает словарь таблиц: per_fold (метрики), deposit_ranks, coverage, oof (оценки ячеек).
    Фолды без месторождений в train или в test пропускаются с предупреждением.
    """
    per_fold, ranks, coverage, oof = [], [], [], []
    for fold in sorted(data[FOLD].dropna().unique()):
        train_mask, test_mask, dropped = split_fold(data, fold, buffer_km)
        train, test = data.loc[train_mask], data.loc[test_mask]
        n_train_pos, n_test_pos = int(train[TARGET].sum()), int(test[TARGET].sum())
        if n_train_pos == 0 or n_test_pos == 0:
            warnings.warn(f"Фолд {fold} пропущен: в train {n_train_pos}, в test {n_test_pos} месторождений.")
            continue
        model = factory().fit(train)
        scores = np.asarray(model.score(test), dtype=float)
        metrics = tie_aware_topk(test[TARGET], scores, fractions)
        metrics[FOLD] = fold
        metrics["test_cells"] = len(test)
        metrics["test_deposits"] = n_test_pos
        metrics["train_deposits"] = n_train_pos
        metrics["train_cells"] = len(train)
        metrics["train_cells_dropped_by_buffer"] = dropped
        metrics["n_unique_scores"] = int(pd.Series(scores).nunique())
        per_fold.append(metrics)
        ranks.append(deposit_ranks_in_test_fold(test, scores, fractions))
        if hasattr(model, "coverage"):
            coverage.append(model.coverage(test).assign(**{FOLD: fold}))
        part = test[["x", "y", TARGET, FOLD]].copy()
        if "deposit_name" in test.columns:
            part["deposit_name"] = test["deposit_name"]
        part["score_oof"] = scores
        oof.append(part)
    if not per_fold:
        raise ValueError("Ни один фолд не подошёл для оценки (нужны месторождения и в train, и в test).")
    return {
        "per_fold": pd.concat(per_fold, ignore_index=True),
        "deposit_ranks": pd.concat(ranks, ignore_index=True),
        "coverage": pd.concat(coverage, ignore_index=True) if coverage else pd.DataFrame(),
        "oof": pd.concat(oof, ignore_index=True),
    }


def run_spatial_oof(data, features, n_bins=5, alpha=0.5, categorical=(), categorical_prior="uniform",
                    missing_as_neutral=False, fractions=TOP_FRACTIONS, buffer_km=0.0):
    """Короткая форма для WoE: возвращает (метрики по фолдам, оценки ячеек)."""
    result = run_spatial_cv(
        data,
        lambda: WoEModel(features, n_bins, alpha, categorical, categorical_prior, missing_as_neutral),
        fractions, buffer_km,
    )
    return result["per_fold"], result["oof"]


# ---------------------------------------------------------------- воспроизводимость

def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_outputs(tables: dict, out_dir, input_path=None, settings=None) -> dict:
    """Сохраняет таблицы в CSV (UTF-8 без BOM) и manifest.json: хеш входа, версии, настройки."""
    import sklearn

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        if table is not None and len(table):
            table.to_csv(out / f"{name}.csv", index=False, encoding="utf-8")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_name": Path(input_path).name if input_path else None,
        "input_sha256": sha256_file(input_path) if input_path else None,
        "versions": {"numpy": np.__version__, "pandas": pd.__version__, "scikit-learn": sklearn.__version__},
        "tables": sorted(name for name, t in tables.items() if t is not None and len(t)),
        "settings": settings or {},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return manifest
