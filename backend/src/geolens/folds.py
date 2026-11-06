"""Пространственные фолды из квадратных блоков территории.

Территорию режем на квадратные блоки (например, 10×10 км). Каждый блок целиком
отдаётся одному фолду, поэтому соседние ячейки почти всегда оказываются в одной
части (train или test). Блоки раздаются так, чтобы месторождения распределились
по фолдам примерно поровну (иначе в каком-то тесте не окажется ни одного объекта).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .validation import split_fold
from .woe import FOLD, TARGET


def make_block_folds(x, y, is_deposit, block_km=10.0, n_folds=5, seed=42) -> pd.Series:
    """Номер фолда (0..n_folds-1) для каждой ячейки. x, y — метры; результат с тем же индексом."""
    x, y = pd.Series(x), pd.Series(y)
    positive = pd.Series(np.asarray(is_deposit), index=x.index).astype(int)
    size = block_km * 1000.0
    bx = np.floor((x - x.min()) / size).astype(int)
    by = np.floor((y - y.min()) / size).astype(int)
    block = bx.astype(str) + "_" + by.astype(str)
    stats = pd.DataFrame({"block": block, "positive": positive}).groupby("block").agg(
        cells=("positive", "size"), positives=("positive", "sum"))
    if len(stats) < n_folds:
        raise ValueError(f"Блоков ({len(stats)}) меньше, чем фолдов ({n_folds}): уменьшите block_km.")
    if int(stats["positives"].sum()) < n_folds:
        raise ValueError("Месторождений меньше, чем фолдов.")

    rng = np.random.default_rng(seed)
    stats = stats.iloc[rng.permutation(len(stats))]  # случайный порядок для равных блоков
    stats = stats.sort_values(["positives", "cells"], ascending=False, kind="stable")
    fold_pos, fold_cells = np.zeros(n_folds), np.zeros(n_folds)
    assignment = {}
    for name, row in stats.iterrows():
        if row["positives"] > 0:  # блоки с месторождениями: в фолд, где их пока меньше (затем ячеек)
            fold = min(range(n_folds), key=lambda f: (fold_pos[f], fold_cells[f]))
        else:  # пустые блоки (идут последними): выравниваем размеры фолдов по числу ячеек
            fold = min(range(n_folds), key=lambda f: fold_cells[f])
        assignment[name] = fold
        fold_pos[fold] += row["positives"]
        fold_cells[fold] += row["cells"]
    return block.map(assignment).astype(int).rename(FOLD)


def fold_report(data: pd.DataFrame, buffer_km: float = 0.0) -> pd.DataFrame:
    """Диагностика фолдов: размеры и расстояние от тестовых месторождений до ближайшего train-объекта.

    Малое расстояние (единицы км) значит, что тест не вполне независим от train.
    """
    rows = []
    for fold in sorted(data[FOLD].dropna().unique()):
        train_mask, test_mask, dropped = split_fold(data, fold, buffer_km)
        test_pos = data.loc[test_mask & data[TARGET].eq(1)]
        train_pos = data.loc[train_mask & data[TARGET].eq(1)]
        if len(test_pos) and len(train_pos):
            km = cKDTree(train_pos[["x", "y"]].to_numpy()).query(test_pos[["x", "y"]].to_numpy())[0] / 1000.0
        else:
            km = np.array([])
        rows.append({
            FOLD: fold, "test_cells": int(test_mask.sum()), "deposits_test": len(test_pos),
            "deposits_train": len(train_pos), "train_cells": int(train_mask.sum()),
            "train_cells_dropped_by_buffer": dropped,
            "nearest_train_deposit_km": ", ".join(f"{v:.1f}" for v in sorted(km)),
            "min_nearest_km": float(km.min()) if len(km) else np.nan,
            "median_nearest_km": float(np.median(km)) if len(km) else np.nan,
        })
    return pd.DataFrame(rows)
