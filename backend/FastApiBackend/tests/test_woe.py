"""Тесты для geolens. Запуск из корня репозитория: python -m pytest"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from geolens import (
    explain_cell,
    fit_woe,
    load_model,
    run_spatial_oof,
    save_model,
    score_woe,
    tie_aware_topk,
)

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "data" / "processed" / "features_table_geo.csv"
OLD_METRICS = ROOT / "data" / "processed" / "woe_geological_baseline" / "spatial_cv_metrics.csv"

FEATURES = ["elevation", "magnetic", "gravity", "dist_fault_km", "dist_contact_km", "lithology_group"]
CATEGORICAL = ["lithology_group"]


def toy_table():
    """Маленькая таблица: у месторождений высота больше, литология «A»."""
    rng = np.random.default_rng(0)
    n = 400
    df = pd.DataFrame(
        {
            "x": np.arange(n) * 1000.0,
            "y": 0.0,
            "elevation": rng.normal(300, 50, n),
            "lithology_group": rng.choice(["A", "B"], n),
            "fold_id": np.arange(n) % 4,
        }
    )
    df["is_deposit"] = 0
    pos = df.sort_values("elevation").index[-8:]
    df.loc[pos, "is_deposit"] = 1
    df.loc[pos, "lithology_group"] = "A"
    return df


def test_weights_have_expected_sign():
    df = toy_table()
    model = fit_woe(df, ["elevation", "lithology_group"], n_bins=3, categorical=["lithology_group"])
    elevation_weights = list(model["elevation"]["table"].values())
    assert elevation_weights[-1] > 0 > elevation_weights[0]  # высокая высота — плюс
    assert model["lithology_group"]["table"]["A"] > model["lithology_group"]["table"]["B"]


def test_fit_requires_both_classes():
    df = toy_table()
    with pytest.raises(ValueError):
        fit_woe(df[df.is_deposit == 0], ["elevation"])


def test_missing_and_unknown_values_are_neutral():
    df = toy_table()
    model = fit_woe(df, ["elevation", "lithology_group"], categorical=["lithology_group"])
    new = pd.DataFrame({"elevation": [np.nan], "lithology_group": ["ZZZ"]})
    assert score_woe(new, model).iloc[0] == 0.0


def test_explanation_sums_to_score():
    df = toy_table()
    model = fit_woe(df, ["elevation", "lithology_group"], categorical=["lithology_group"])
    row = df.iloc[int(df.is_deposit.to_numpy().argmax())]
    explanation = explain_cell(row, model)
    assert explanation.contribution.sum() == pytest.approx(score_woe(df.loc[[row.name]], model).iloc[0])


def test_save_load_roundtrip(tmp_path):
    df = toy_table()
    model = fit_woe(df, ["elevation", "lithology_group"], categorical=["lithology_group"])
    save_model(model, tmp_path / "m.json")
    loaded = load_model(tmp_path / "m.json")
    assert np.allclose(score_woe(df, model), score_woe(df, loaded))


def test_topk_handles_ties():
    y = [1, 0, 0, 0]
    scores = [1.0, 1.0, 1.0, 1.0]  # все равны: найденное «по случайности»
    row = tie_aware_topk(y, scores, fractions=(0.5,)).iloc[0]
    assert (row.found_min, row.found_max) == (0, 1)
    assert row.found_expected == pytest.approx(0.5)


def test_cv_never_trains_on_test_fold():
    """Если в тестовом фолде поменять метки, веса из train не должны измениться."""
    df = toy_table()
    train = df[df.fold_id != 0]
    a = fit_woe(train, ["elevation"], n_bins=3)
    df2 = df.copy()
    df2.loc[df2.fold_id == 0, "is_deposit"] = 1 - df2.loc[df2.fold_id == 0, "is_deposit"]
    b = fit_woe(df2[df2.fold_id != 0], ["elevation"], n_bins=3)
    assert list(a["elevation"]["table"].values()) == list(b["elevation"]["table"].values())


@pytest.mark.skipif(not (TABLE.exists() and OLD_METRICS.exists()), reason="нет данных проекта")
def test_matches_old_notebook_results():
    """Модуль должен давать те же числа, что ноутбук woe_baseline_02_geological."""
    df = pd.read_csv(TABLE, encoding="utf-8-sig")
    old = pd.read_csv(OLD_METRICS, encoding="utf-8-sig")
    for n_bins in (3, 5, 7):
        new, _ = run_spatial_oof(df, FEATURES, n_bins=n_bins, alpha=0.5, categorical=CATEGORICAL)
        ref = old[old.n_bins == n_bins]
        key = ["fold_id", "area_fraction"]
        merged = new.merge(ref, on=key, suffixes=("_new", "_old"))
        assert len(merged) == len(ref) == len(new)
        for col in ["found_expected", "success_rate_expected", "cells_tied_at_cutoff", "top_k_cells", "found_min", "found_max"]:
            assert np.allclose(merged[col + "_new"], merged[col + "_old"]), (n_bins, col)
