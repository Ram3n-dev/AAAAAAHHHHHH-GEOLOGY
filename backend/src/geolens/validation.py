"""Пространственная кросс-валидация.

Каждый фолд по очереди становится «тестом»: веса обучаем на остальных фолдах,
а оцениваем только на исключённом. Так мы проверяем, умеет ли метод находить
месторождения на территории, которой он «не видел».
"""

from __future__ import annotations

import warnings

import pandas as pd

from .metrics import tie_aware_topk
from .woe import FOLD, TARGET, fit_woe, score_woe


def run_spatial_oof(data, features, n_bins=5, alpha=0.5, categorical=()):
    """Возвращает (метрики по фолдам, out-of-fold оценки ячеек).

    Фолды без месторождений в train или в test пропускаются с предупреждением.
    """
    rows, parts = [], []
    for fold in sorted(data[FOLD].dropna().unique()):
        train = data.loc[data[FOLD].ne(fold)].copy()
        test = data.loc[data[FOLD].eq(fold)].copy()
        n_train_pos = int(train[TARGET].sum())
        n_test_pos = int(test[TARGET].sum())
        if n_train_pos == 0 or n_test_pos == 0:
            warnings.warn(
                f"Фолд {fold} пропущен: в train {n_train_pos}, в test {n_test_pos} месторождений."
            )
            continue
        model = fit_woe(train, features, n_bins, alpha, categorical)
        scores = score_woe(test, model)
        metrics = tie_aware_topk(test[TARGET], scores)
        metrics[FOLD] = fold
        metrics["test_cells"] = len(test)
        metrics["test_deposits"] = n_test_pos
        metrics["train_deposits"] = n_train_pos
        metrics["n_unique_scores"] = int(scores.nunique())
        rows.append(metrics)

        part = test[["x", "y", TARGET, FOLD]].copy()
        if "deposit_name" in test.columns:
            part["deposit_name"] = test["deposit_name"]
        part["score_oof"] = scores
        part["n_bins"] = n_bins
        part["alpha"] = alpha
        parts.append(part)
    return pd.concat(rows, ignore_index=True), pd.concat(parts, ignore_index=True)
