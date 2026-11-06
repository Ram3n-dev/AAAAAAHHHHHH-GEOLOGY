"""Метрики качества ранжирования.

Вопрос геолога: «если я отработаю 5% (10%) площади с самыми высокими оценками,
сколько известных месторождений я найду?»
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .woe import FOLD, TARGET

TOP_FRACTIONS = (0.01, 0.05, 0.10)


def tie_aware_topk(y_true, scores, fractions=TOP_FRACTIONS) -> pd.DataFrame:
    """Сколько месторождений попало в верхние K ячеек, с учётом ничьих.

    Если на границе top-K у нескольких ячеек одинаковая оценка, неизвестно,
    какие из них попадут в K. Поэтому возвращаем минимум, максимум и ожидаемое
    значение (как если бы ничьи разрешались случайно).
    """
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=float)
    if len(y) != len(s):
        raise ValueError("y_true и scores должны быть одной длины.")
    if not np.isfinite(s).all():
        raise ValueError("В scores есть NaN/inf.")
    n, n_pos = len(y), int(y.sum())
    rows = []
    for fraction in fractions:
        k = max(1, int(np.ceil(n * fraction)))
        cutoff = np.sort(s)[::-1][k - 1]
        above, tied = s > cutoff, s == cutoff
        found_above = int(y[above].sum())
        pos_tied = int(y[tied].sum())
        slots = max(k - int(above.sum()), 0)
        n_tied = int(tied.sum())
        expected = found_above + (slots * pos_tied / n_tied if n_tied else 0.0)
        rows.append(
            {
                "area_fraction": fraction,
                "top_k_cells": k,
                "cutoff_score": float(cutoff),
                "found_min": found_above,
                "found_max": found_above + min(slots, pos_tied),
                "found_expected": expected,
                "precision_at_k_expected": expected / k,
                "success_rate_expected": expected / n_pos if n_pos else np.nan,
                "cells_tied_at_cutoff": n_tied,
                "positive_ties_at_cutoff": pos_tied,
            }
        )
    return pd.DataFrame(rows)


def deposit_ranks_in_test_fold(test: pd.DataFrame, scores) -> pd.DataFrame:
    """Где по оценке оказалось каждое известное месторождение среди ВСЕХ ячеек тестового фолда."""
    scores = pd.Series(np.asarray(scores, dtype=float), index=test.index)
    keep = [c for c in ["deposit_name", "x", "y", FOLD] if c in test]
    positive = test.loc[test[TARGET].eq(1), keep].copy()
    positive["score"] = scores.loc[positive.index]
    positive["rank_min_all_cells"] = positive["score"].map(lambda v: int((scores >= v).sum()))
    positive["rank_fraction_all_cells"] = positive["rank_min_all_cells"] / len(test)
    positive["score_percentile"] = positive["score"].rank(ascending=True, pct=True, method="average")
    return positive.sort_values("rank_min_all_cells")
