"""Единый протокол оценки: один конфиг -> все модели и наборы признаков на одних фолдах.

Один и тот же код запускается для любого региона (Henan, Енисейский кряж, ...).
Так сравнение справедливо: отличаются данные, а не способ проверки.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .folds import fold_report, make_block_folds
from .metrics import random_budget, summarize_folds
from .models import LogisticModel, WoEModel
from .stability import leave_one_deposit_out, stability_summary
from .validation import run_spatial_cv, save_outputs
from .woe import FOLD, TARGET


def resolve_features(columns, spec):
    """Список признаков из конфига: либо явный список, либо {"prefix": "geochem_"}, либо {"prefixes": [...]}."""
    if isinstance(spec, list):
        missing = [c for c in spec if c not in columns]
        if missing:
            raise ValueError(f"Нет столбцов в таблице: {missing}")
        return spec
    prefixes = [spec["prefix"]] if "prefix" in spec else list(spec["prefixes"])
    features = [c for c in columns if any(c.startswith(p) for p in prefixes)]
    if not features:
        raise ValueError(f"Ни один столбец не начинается с {prefixes}.")
    return features


def make_factory(spec: dict, features, categorical):
    """Конструктор модели по записи из конфига. Возвращает (имя, функция-фабрика)."""
    kind = spec["kind"]
    if kind == "woe":
        opts = dict(
            n_bins=spec.get("n_bins", 3),
            alpha=spec.get("alpha", 0.5),
            categorical_prior=spec.get("categorical_prior", "uniform"),
            missing_as_neutral=spec.get("missing_as_neutral", False),
        )
        make = lambda: WoEModel(features, categorical=categorical, **opts)
    elif kind == "logreg":
        make = lambda: LogisticModel(features, categorical=categorical)
    else:
        raise ValueError(f"Неизвестный тип модели: {kind}")
    return spec.get("label") or make().name, make


def run_protocol(cfg: dict, root=".") -> dict:
    """Запускает протокол по конфигу (см. configs/*.json) и сохраняет результаты. Возвращает таблицы."""
    root = Path(root)
    table_path = root / cfg["table"]
    data = pd.read_csv(table_path, encoding="utf-8-sig")
    if "folds" in cfg:  # фолды пересобираются здесь, чтобы их можно было менять, не трогая таблицу
        f = cfg["folds"]
        data[FOLD] = make_block_folds(data.x, data.y, data[TARGET], f.get("block_km", 10), f.get("n_folds", 5), f.get("seed", 42))
    for col in ("x", "y", TARGET, FOLD):
        if col not in data:
            raise ValueError(f"В таблице нет столбца {col}.")

    fractions = tuple(cfg.get("fractions", (0.01, 0.05, 0.10)))
    buffer_km = float(cfg.get("buffer_km", 0.0))
    cat_prefixes = tuple(cfg.get("categorical_prefixes", ()))
    cat_names = set(cfg.get("categorical", ()))
    stab = cfg.get("stability", {})

    per_fold, ranks, coverage, stability, stability_sum = [], [], [], [], []
    for fs_name, fs_spec in cfg["feature_sets"].items():
        features = resolve_features(list(data.columns), fs_spec)
        categorical = [c for c in features if c in cat_names or c.startswith(cat_prefixes)] if (cat_names or cat_prefixes) else []
        for model_spec in cfg["models"]:
            name, factory = make_factory(model_spec, features, categorical)
            tags = {"feature_set": fs_name, "model": name}
            result = run_spatial_cv(data, factory, fractions, buffer_km)
            per_fold.append(result["per_fold"].assign(**tags))
            ranks.append(result["deposit_ranks"].assign(**tags))
            if not result["coverage"].empty:
                coverage.append(result["coverage"].assign(**tags))
            wanted = stab.get("enabled", False) and name in stab.get("models", [name]) and fs_name in stab.get("feature_sets", [fs_name])
            if wanted:
                frac = stab.get("fraction", 0.10)
                long = leave_one_deposit_out(data, factory, frac, buffer_km, stab.get("entity_col"))
                stability.append(long.assign(**tags))
                stability_sum.append(stability_summary(long, frac).assign(**tags))

    per_fold_all = pd.concat(per_fold, ignore_index=True)
    first = per_fold[0]
    one_fraction = first[first.area_fraction.eq(first.area_fraction.iloc[0])]
    tables = {
        "per_fold": per_fold_all,
        "summary": summarize_folds(per_fold_all, keys=["feature_set", "model"]),
        "deposit_ranks": pd.concat(ranks, ignore_index=True),
        "coverage": pd.concat(coverage, ignore_index=True) if coverage else pd.DataFrame(),
        "random_budget": random_budget(one_fraction.test_cells.tolist(), one_fraction.test_deposits.tolist(), fractions),
        "fold_report": fold_report(data, buffer_km).astype({"nearest_train_deposit_km": str}),
        "stability": pd.concat(stability, ignore_index=True) if stability else pd.DataFrame(),
        "stability_summary": pd.concat(stability_sum, ignore_index=True) if stability_sum else pd.DataFrame(),
    }
    save_outputs(tables, root / cfg["out_dir"], input_path=table_path, settings=cfg)
    return tables
