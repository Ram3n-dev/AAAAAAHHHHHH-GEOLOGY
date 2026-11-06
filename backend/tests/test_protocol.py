"""Тесты новых частей: метрики, prior, модели, фолды с буфером, устойчивость, сетка."""

import numpy as np
import pandas as pd
import pytest

from geolens import (
    LogisticModel,
    WoEModel,
    coverage_audit,
    deposit_ranks_in_test_fold,
    fit_woe,
    fold_report,
    label_clusters,
    leave_one_deposit_out,
    make_block_folds,
    random_budget,
    run_spatial_cv,
    save_outputs,
    score_woe,
    stability_summary,
    stack_to_table,
    summarize_folds,
    table_qa,
    tie_aware_topk,
)
from geolens.validation import split_fold


# ---------- вспомогательные данные ----------

def synthetic_region(rows=60, cols=80, n_deposits=24, seed=1):
    """Район со СКРЫТЫМ правилом: месторождения тяготеют к высоким значениям слоя «signal»."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((rows, cols))
    signal = np.sin(xx / 9.0) + np.cos(yy / 7.0) + rng.normal(0, 0.3, (rows, cols))
    noise = rng.normal(size=(rows, cols))
    litho = rng.integers(1, 4, size=(rows, cols)).astype(float)
    p = np.exp(3 * signal).ravel()
    p /= p.sum()
    chosen = rng.choice(rows * cols, size=n_deposits, replace=False, p=p)
    labels = np.zeros(rows * cols, dtype=int)
    labels[chosen] = 1
    return np.stack([signal, noise, litho]), labels.reshape(rows, cols)


def region_table(seed=1, **kw):
    stack, labels = synthetic_region(seed=seed, **kw)
    table = stack_to_table(stack, ["signal", "noise", "litho"], left=0.0, top=60 * 500.0, pixel_size=500.0,
                           labels=labels, categorical=["litho"])
    table["fold_id"] = make_block_folds(table.x, table.y, table.is_deposit, block_km=6, n_folds=4, seed=3)
    return table


# ---------- метрики ----------

def test_topk_random_expected_and_min_with_ties():
    # 4 ячейки, все с одинаковой оценкой, одна положительная; в top-50% попадут 2 любые
    row = tie_aware_topk([1, 0, 0, 0], [1.0] * 4, fractions=(0.5,)).iloc[0]
    assert (row.found_min, row.found_max) == (0, 1)
    assert row.found_expected == pytest.approx(0.5) and row.random_expected == pytest.approx(0.5)
    # положительных больше, чем «неположительных» на границе: минимум не 0
    row = tie_aware_topk([1, 1, 1, 0], [1.0] * 4, fractions=(0.75,)).iloc[0]
    assert row.found_min == 2


def test_topk_float_noise_is_a_tie():
    row = tie_aware_topk([1, 0], [1.0, 1.0 + 1e-15], fractions=(0.5,)).iloc[0]
    assert row.cells_tied_at_cutoff == 2


def test_random_budget_matches_known_values():
    """Значения совпадают с независимым расчётом для 5 фолдов Енисейского кряжа."""
    sizes, pos = [4874, 7273, 3359, 17250, 2938], [1, 2, 2, 5, 1]
    table = random_budget(sizes, pos, fractions=(0.10,))
    assert table.probability.sum() == pytest.approx(1.0)
    assert table.loc[table.found == 2, "p_at_least"].iloc[0] == pytest.approx(0.3028, abs=1e-3)
    assert (table.found * table.probability).sum() == pytest.approx(1.10, abs=0.01)


def test_summarize_sums_finds_not_averages():
    a = tie_aware_topk([1, 0, 0, 0, 0, 0, 0, 0, 0, 0], np.arange(10), fractions=(0.1,)).assign(fold_id=0)
    b = tie_aware_topk([0, 0, 0, 0, 0, 0, 0, 0, 0, 0], np.arange(10), fractions=(0.1,)).assign(fold_id=1)
    b["n_positive"] = 0
    s = summarize_folds(pd.concat([a, b]))
    assert s.n_positive.iloc[0] == 1


def test_ranks_best_worst_and_probability():
    test = pd.DataFrame({"is_deposit": [0, 1, 0, 0], "fold_id": 0, "x": 0, "y": 0})
    r = deposit_ranks_in_test_fold(test, [5, 4, 4, 1], fractions=(0.5,)).iloc[0]
    assert (r.rank_best, r.rank_worst) == (2, 3)
    assert r.hit_probability_top50 == pytest.approx(0.5)  # k=2, ничья на местах 2-3: в топ-2 с вероятностью 1/2


# ---------- WoE: prior и пропуски ----------

def test_background_prior_shrinks_rare_category():
    df = pd.DataFrame({"is_deposit": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0], "lith": ["A", "A", "B", "B", "B", "B", "C", "C", "C", "C"]})
    uniform = fit_woe(df, ["lith"], categorical=["lith"], categorical_prior="uniform")["lith"]["table"]
    background = fit_woe(df, ["lith"], categorical=["lith"], categorical_prior="background")["lith"]["table"]
    assert background["A"] > 0 and background["B"] < 0
    assert abs(background["A"]) < abs(uniform["A"])  # осторожнее


def test_unknown_and_cover_are_neutral_when_requested():
    df = pd.DataFrame({"is_deposit": [1, 0, 0, 0, 0, 0], "lith": ["A", "A", "unknown", "cover", None, "B"]})
    model = fit_woe(df, ["lith"], categorical=["lith"], missing_as_neutral=True)
    assert set(model["lith"]["table"]) == {"A", "B"}  # «unknown»/«cover» — не порода
    new = pd.DataFrame({"lith": ["unknown", "cover", None, "ZZZ"]})
    assert (score_woe(new, model) == 0).all()
    audit = coverage_audit(new, model).iloc[0]
    assert (audit.test_missing, audit.test_unseen) == (3, 1)


def test_category_renaming_does_not_change_scores():
    df = pd.DataFrame({"is_deposit": [1, 0, 1, 0, 0, 0], "lith": ["A", "A", "B", "B", "B", None]})
    test = pd.DataFrame({"lith": ["A", "B", None, "C"]})
    base = score_woe(test, fit_woe(df, ["lith"], categorical=["lith"], categorical_prior="background"))
    ren = {"A": "Z", "B": "0"}
    other = score_woe(test.assign(lith=test.lith.replace(ren)),
                      fit_woe(df.assign(lith=df.lith.replace(ren)), ["lith"], categorical=["lith"], categorical_prior="background"))
    assert np.allclose(base, other)


# ---------- модели ----------

def test_both_models_beat_random_on_synthetic_signal():
    table = region_table()
    features, cat = ["signal", "noise", "litho"], ["litho"]
    for factory in (lambda: WoEModel(features, 3, 0.5, cat), lambda: LogisticModel(features, cat)):
        result = run_spatial_cv(table, factory, fractions=(0.10,))
        s = summarize_folds(result["per_fold"])
        assert s.found_expected.iloc[0] > 1.5 * s.random_expected.iloc[0]


def test_logistic_unseen_category_gives_zero_indicators():
    train = pd.DataFrame({"is_deposit": [1, 0, 0, 1, 0, 0], "a": [1.0, 2, 3, 4, 5, 6], "c": list("ABABAB")})
    model = LogisticModel(["a", "c"], ["c"]).fit(train)
    test = pd.DataFrame({"a": [1.0, 1.0], "c": ["A", "NEW"]})
    assert np.isfinite(model.score(test)).all()
    assert model.coverage(test).set_index("feature").loc["c", "test_unseen"] == 1


def test_no_leakage_into_train_statistics():
    table = region_table()
    train = table[table.fold_id != 0]
    a = WoEModel(["signal"], 3).fit(train).model_["signal"]["table"]
    flipped = table.copy()
    flipped.loc[flipped.fold_id == 0, "is_deposit"] = 1 - flipped.loc[flipped.fold_id == 0, "is_deposit"]
    b = WoEModel(["signal"], 3).fit(flipped[flipped.fold_id != 0]).model_["signal"]["table"]
    assert list(a.values()) == list(b.values())


# ---------- фолды ----------

def test_block_folds_keep_blocks_whole_and_are_deterministic():
    table = region_table()
    f1 = make_block_folds(table.x, table.y, table.is_deposit, block_km=6, n_folds=4, seed=3)
    f2 = make_block_folds(table.x, table.y, table.is_deposit, block_km=6, n_folds=4, seed=3)
    assert (f1 == f2).all()
    bx = ((table.x - table.x.min()) // 6000).astype(int)
    by = ((table.y - table.y.min()) // 6000).astype(int)
    assert (table.assign(b=bx.astype(str) + "_" + by.astype(str)).groupby("b").fold_id.nunique() == 1).all()
    pos = table.groupby("fold_id").is_deposit.sum()
    assert pos.max() - pos.min() <= 3  # месторождения распределены достаточно ровно


def test_block_folds_have_comparable_sizes():
    """Пустые блоки выравнивают размеры фолдов: ни один фолд не должен съесть почти всю площадь."""
    rng = np.random.default_rng(5)
    yy, xx = np.indices((93, 209))  # размер сетки Henan
    p = np.exp(2.5 * np.sin(xx / 17) + np.cos(yy / 9)).ravel()
    p /= p.sum()
    labels = np.zeros(93 * 209, int)
    labels[rng.choice(93 * 209, 54, replace=False, p=p)] = 1
    table = pd.DataFrame({"x": xx.ravel() * 500.0, "y": yy.ravel() * 500.0, "is_deposit": labels})
    for block_km in (5, 10):
        folds = make_block_folds(table.x, table.y, table.is_deposit, block_km=block_km, n_folds=5, seed=42)
        sizes = folds.value_counts()
        assert sizes.max() / sizes.min() < 2.0, (block_km, sizes.to_dict())
        assert table.groupby(folds).is_deposit.sum().min() >= 5


def test_buffer_removes_close_training_cells():
    table = region_table()
    train, test, dropped = split_fold(table, 0, buffer_km=3.0)
    assert dropped > 0 and not (train & test).any()
    from scipy.spatial import cKDTree
    d = cKDTree(table.loc[test, ["x", "y"]].to_numpy()).query(table.loc[train, ["x", "y"]].to_numpy())[0]
    assert d.min() >= 3000.0
    # без буфера обучение = все остальные фолды
    train0, _, dropped0 = split_fold(table, 0, 0.0)
    assert dropped0 == 0 and train0.sum() == (table.fold_id != 0).sum()


def test_fold_report_lists_distance_to_train_deposits():
    rep = fold_report(region_table())
    assert rep.deposits_test.sum() == region_table().is_deposit.sum()
    assert (rep.min_nearest_km.dropna() > 0).all()


# ---------- устойчивость ----------

def test_leave_one_deposit_out_summary():
    table = region_table()
    long = leave_one_deposit_out(table, lambda: WoEModel(["signal"], 3), fraction=0.10)
    assert "(none)" in set(long.dropped_entity)
    summary = stability_summary(long, 0.10)
    assert len(summary) <= table.is_deposit.sum() and len(summary) > 0
    assert (summary.max_best_area_fraction >= summary.min_best_area_fraction).all()


# ---------- сетка ----------

def test_stack_to_table_geometry_nodata_and_clusters():
    stack = np.arange(2 * 3 * 4, dtype=float).reshape(2, 3, 4)
    stack[:, 0, 0] = -9999  # вне района
    labels = np.zeros((3, 4), dtype=int)
    labels[1, 1] = labels[1, 2] = 1  # соседи по стороне -> один объект
    labels[2, 3] = 1  # по диагонали к (1, 2): при 8-связности тоже тот же объект
    t = stack_to_table(stack, ["a", "b"], left=1000.0, top=3000.0, pixel_size=500.0, labels=labels, nodata=-9999)
    assert len(t) == 11  # (0,0) без данных отброшена
    cell = t[(t.row == 1) & (t.col == 1)].iloc[0]
    assert (cell.x, cell.y) == (1750.0, 2250.0)  # центр ячейки (col+0.5), а не угол
    assert t.is_deposit.sum() == 3 and t.entity_id.max() == 1  # все три ячейки — один объект
    assert label_clusters(labels, connectivity=8)[1] == 1
    assert label_clusters(labels, connectivity=4)[1] == 2  # без диагоналей — два объекта


def test_stack_to_table_validation():
    with pytest.raises(ValueError):
        stack_to_table(np.zeros((2, 3, 3)), ["a"], 0, 0, 1, np.zeros((3, 3)))
    with pytest.raises(ValueError):
        stack_to_table(np.zeros((1, 3, 3)), ["a"], 0, 0, 1, np.zeros((2, 2)))
    qa = table_qa(region_table(), ["signal", "noise", "litho"])
    assert qa["duplicate_xy"] == 0 and qa["positive_objects"] >= 1


def test_save_outputs_writes_manifest_without_bom(tmp_path):
    csv = tmp_path / "in.csv"
    csv.write_text("a\n1\n", encoding="utf-8")
    save_outputs({"t": pd.DataFrame({"a": [1]})}, tmp_path / "out", input_path=csv, settings={"k": 1})
    assert not (tmp_path / "out" / "t.csv").read_bytes().startswith(b"\xef\xbb\xbf")
    assert "input_sha256" in (tmp_path / "out" / "manifest.json").read_text(encoding="utf-8")
