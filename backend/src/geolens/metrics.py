"""Метрики качества ранжирования.

Вопрос геолога: «если я отработаю 5% (10%) площади с самыми высокими оценками,
сколько известных месторождений я найду?» Ответ сравниваем со случайным выбором
такой же площади.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import hypergeom

from .woe import FOLD, TARGET

TOP_FRACTIONS = (0.01, 0.05, 0.10)
TIE_DECIMALS = 12  # оценки, отличающиеся только шумом float, считаем равными


def budget_k(n_cells: int, fraction: float) -> int:
    """Сколько ячеек составляют долю площади (округление вверх, минимум 1)."""
    return min(n_cells, max(1, int(np.ceil(n_cells * fraction))))


def tie_aware_topk(y_true, scores, fractions=TOP_FRACTIONS) -> pd.DataFrame:
    """Сколько месторождений попало в верхние K ячеек, с учётом ничьих.

    Если на границе top-K у нескольких ячеек одинаковая оценка, неизвестно,
    какие из них попадут в K. Поэтому возвращаем минимум, максимум и ожидаемое
    значение (как если бы ничьи разрешались случайно).
    """
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=float)
    if len(y) != len(s) or len(y) == 0:
        raise ValueError("y_true и scores должны быть непустыми и одной длины.")
    if not np.isfinite(s).all():
        raise ValueError("В scores есть NaN/inf.")
    s = np.round(s, TIE_DECIMALS)
    n, n_pos = len(y), int(y.sum())
    rows = []
    for fraction in fractions:
        k = budget_k(n, fraction)
        cutoff = np.sort(s)[::-1][k - 1]
        above, tied = s > cutoff, s == cutoff
        found_above = int(y[above].sum())
        pos_tied, n_tied = int(y[tied].sum()), int(tied.sum())
        slots = k - int(above.sum())  # сколько мест на границе достанется ничьим
        expected = found_above + slots * pos_tied / n_tied
        rows.append(
            {
                "area_fraction": fraction,
                "top_k_cells": k,
                "cutoff_score": float(cutoff),
                "n_positive": n_pos,
                "found_min": found_above + max(0, slots - (n_tied - pos_tied)),
                "found_expected": expected,
                "found_max": found_above + min(slots, pos_tied),
                "random_expected": k / n * n_pos,
                "precision_at_k_expected": expected / k,
                "success_rate_expected": expected / n_pos if n_pos else np.nan,
                "cells_tied_at_cutoff": n_tied,
                "positive_ties_at_cutoff": pos_tied,
            }
        )
    return pd.DataFrame(rows)


def _random_pmf(test_cells, positives, fraction) -> np.ndarray:
    """pmf[j] — вероятность найти ровно j объектов при случайном выборе доли площади в каждом фолде."""
    pmf = np.array([1.0])
    for n, m in zip(test_cells, positives):
        n, m = int(n), int(m)
        pmf = np.convolve(pmf, hypergeom.pmf(np.arange(m + 1), n, m, budget_k(n, fraction)))
    return pmf


def random_budget(test_cells, positives, fractions=TOP_FRACTIONS) -> pd.DataFrame:
    """Случайный ориентир: сколько объектов нашлось бы при случайном выборе той же площади.

    Внутри фолда число находок подчиняется гипергеометрическому закону; фолды
    независимы, поэтому распределения сворачиваются. Колонки: area_fraction, found,
    probability (ровно found), p_at_least (не меньше found). Это не p-value модели,
    а точка отсчёта: «как часто столько нашлось бы при равновероятном выборе».
    """
    rows = []
    for fraction in fractions:
        pmf = _random_pmf(test_cells, positives, fraction)
        tail = np.cumsum(pmf[::-1])[::-1]
        for found, (p, t) in enumerate(zip(pmf, tail)):
            rows.append({"area_fraction": fraction, "found": found,
                         "probability": float(p), "p_at_least": float(t)})
    return pd.DataFrame(rows)


def summarize_folds(per_fold: pd.DataFrame, keys=()) -> pd.DataFrame:
    """Итог по всем фолдам: суммируем находки и делим на ВСЕ известные объекты.

    (Среднее по фолдам неверно: фолд с одним объектом весил бы так же, как фолд с пятью.)
    keys — доп. столбцы группировки, например ["feature_set", "model"].
    """
    group = list(keys) + ["area_fraction"]
    out = per_fold.groupby(group, sort=False).agg(
        found_min=("found_min", "sum"), found_expected=("found_expected", "sum"),
        found_max=("found_max", "sum"), random_expected=("random_expected", "sum"),
        n_positive=("n_positive", "sum"),
    ).reset_index()
    out["recall_expected"] = out["found_expected"] / out["n_positive"].where(out["n_positive"] > 0)
    out["lift_vs_random"] = out["found_expected"] / out["random_expected"].where(out["random_expected"] > 0)
    # среднее по фолдам — только как отдельная диагностика
    macro = (per_fold.assign(_r=per_fold["found_expected"] / per_fold["n_positive"].where(per_fold["n_positive"] > 0))
             .groupby(group, sort=False)["_r"].mean().reset_index(name="macro_fold_recall"))
    return out.merge(macro, on=group, validate="one_to_one")


def deposit_ranks_in_test_fold(test: pd.DataFrame, scores, fractions=TOP_FRACTIONS) -> pd.DataFrame:
    """Где по оценке оказалось каждое известное месторождение среди ВСЕХ ячеек тестового фолда.

    rank_best / rank_worst — позиция при самом удачном / неудачном разрешении ничьих
    (1 = лучшая ячейка фолда). hit_probability_topN — вероятность попасть в top N%.
    """
    scores = pd.Series(np.round(np.asarray(scores, dtype=float), TIE_DECIMALS), index=test.index)
    best = scores.rank(ascending=False, method="min")
    worst = scores.rank(ascending=False, method="max")
    keep = [c for c in ["deposit_name", "x", "y", FOLD] if c in test]
    out = test.loc[test[TARGET].eq(1), keep].copy()
    out["score"] = scores.loc[out.index]
    out["test_cells"] = len(test)
    out["rank_best"] = best.loc[out.index].astype(int)
    out["rank_worst"] = worst.loc[out.index].astype(int)
    out["best_area_fraction"] = out["rank_best"] / len(test)
    out["worst_area_fraction"] = out["rank_worst"] / len(test)
    for fraction in fractions:
        k = budget_k(len(test), fraction)
        share = (k - out["rank_best"] + 1) / (out["rank_worst"] - out["rank_best"] + 1)
        out[f"hit_probability_top{int(round(100 * fraction))}"] = share.clip(0, 1)
    return out.sort_values("rank_best")
