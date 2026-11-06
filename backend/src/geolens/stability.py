"""Устойчивость: от каких обучающих месторождений зависит результат.

Для каждого тестового фолда по очереди выбрасываем из train ОДИН объект
(месторождение целиком — все его ячейки), переобучаем модель и смотрим, куда
сместились тестовые месторождения. Если попадание в топ исчезает после удаления
одного обучающего объекта, результат держится на этом объекте и ему нельзя
доверять без проверки (разметки, геологии).

«Объект» — значение столбца entity_col (например, deposit_name) или, если
столбец не задан, entity_id (склеенные соседние положительные ячейки).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import TIE_DECIMALS, budget_k
from .validation import split_fold
from .woe import FOLD, TARGET

NONE = "(none)"  # «ничего не удаляли» — полная модель


def _entity_labels(data: pd.DataFrame, entity_col) -> pd.Series:
    col = entity_col or ("entity_id" if "entity_id" in data else None)
    if col is None or col not in data:
        return pd.Series(data.index.astype(str), index=data.index)  # каждая ячейка — свой объект
    return data[col].astype(str)


def leave_one_deposit_out(data, factory, fraction=0.10, buffer_km=0.0, entity_col=None) -> pd.DataFrame:
    """Таблица «удалили обучающий объект -> где оказался тестовый объект».

    Столбцы: fold_id, dropped_entity ("(none)" = полная модель), test_entity,
    best_area_fraction / worst_area_fraction (доля площади фолда до объекта),
    hit_probability (вероятность попасть в top `fraction`).
    """
    entity = _entity_labels(data, entity_col)
    rows = []
    for fold in sorted(data[FOLD].dropna().unique()):
        train_mask, test_mask, _ = split_fold(data, fold, buffer_km)
        train, test = data.loc[train_mask], data.loc[test_mask]
        test_pos = test.index[test[TARGET].eq(1)]
        train_entities = list(pd.unique(entity.loc[train.index[train[TARGET].eq(1)]]))
        if len(test_pos) == 0 or len(train_entities) < 2:
            continue
        k = budget_k(len(test), fraction)
        for dropped in [NONE] + train_entities:
            fit_data = train
            if dropped != NONE:
                fit_data = train.loc[~(train[TARGET].eq(1) & entity.loc[train.index].eq(dropped))]
            scores = pd.Series(np.round(np.asarray(factory().fit(fit_data).score(test), dtype=float), TIE_DECIMALS),
                               index=test.index)
            best = scores.rank(ascending=False, method="min").loc[test_pos]
            worst = scores.rank(ascending=False, method="max").loc[test_pos]
            hit = ((k - best + 1) / (worst - best + 1)).clip(0, 1)
            frame = pd.DataFrame({"test_entity": entity.loc[test_pos].to_numpy(), "best": best.to_numpy(),
                                  "worst": worst.to_numpy(), "hit": hit.to_numpy()})
            for name, g in frame.groupby("test_entity", sort=False):
                top = g.loc[g["best"].idxmin()]  # лучшая ячейка объекта
                rows.append({FOLD: fold, "dropped_entity": dropped, "test_entity": name,
                             "best_area_fraction": top["best"] / len(test),
                             "worst_area_fraction": top["worst"] / len(test),
                             "hit_probability": float(g["hit"].max())})
    return pd.DataFrame(rows)


def stability_summary(long: pd.DataFrame, fraction=0.10) -> pd.DataFrame:
    """По каждому тестовому объекту: положение в полной модели, диапазон при удалениях, самый «вредный» объект."""
    rows = []
    for (fold, name), g in long.groupby([FOLD, "test_entity"], sort=False):
        full = g[g["dropped_entity"].eq(NONE)].iloc[0]
        refits = g[g["dropped_entity"].ne(NONE)]
        in_top = full["best_area_fraction"] <= fraction
        worst = refits.loc[refits["best_area_fraction"].idxmax()] if len(refits) else None
        rows.append({
            FOLD: fold, "test_entity": name,
            "full_best_area_fraction": full["best_area_fraction"],
            "full_worst_area_fraction": full["worst_area_fraction"],
            "min_best_area_fraction": g["best_area_fraction"].min(),
            "max_best_area_fraction": g["best_area_fraction"].max(),
            "in_top_with_all_train": bool(in_top),
            "n_refits": len(refits),
            "refits_leaving_top": int((refits["best_area_fraction"] > fraction).sum()) if in_top else 0,
            "most_damaging_entity": worst["dropped_entity"] if worst is not None else None,
        })
    return pd.DataFrame(rows).sort_values("full_best_area_fraction", ignore_index=True)
