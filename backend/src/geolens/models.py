"""Модели с единым интерфейсом: .fit(train) и .score(data).

Любая модель, у которой есть эти два метода, подходит для run_spatial_cv.
Оценка — число для ранжирования ячеек (чем больше, тем перспективнее),
а не вероятность месторождения.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .woe import (
    TARGET,
    _category_values,
    coverage_audit,
    fit_woe,
    score_woe,
    woe_contributions,
)


class WoEModel:
    """WoE (см. woe.py) в виде объекта с .fit/.score."""

    def __init__(self, features, n_bins=3, alpha=0.5, categorical=(), categorical_prior="uniform", missing_as_neutral=False):
        self.features = list(features)
        self.n_bins, self.alpha = n_bins, alpha
        self.categorical = tuple(categorical)
        self.categorical_prior = categorical_prior
        self.missing_as_neutral = missing_as_neutral
        self.name = f"woe{n_bins}" + ("_bg" if categorical_prior == "background" else "")

    def fit(self, train):
        self.model_ = fit_woe(
            train, self.features, self.n_bins, self.alpha, self.categorical,
            self.categorical_prior, self.missing_as_neutral,
        )
        return self

    def score(self, data):
        return score_woe(data, self.model_).to_numpy()

    def contributions(self, data):
        return woe_contributions(data, self.model_)

    def coverage(self, data):
        return coverage_audit(data, self.model_)


class LogisticModel:
    """Логистическая регрессия с протоколом, зафиксированным заранее (параметры не подбираются).

    L2, C=1, class_weight='balanced'. Всё, что «учится» (медианы, средние, std,
    список пород), берётся только из train. Пропуск числа -> медиана train.
    Пропуск или новая порода -> нули во всех индикаторах породы.
    Ранжируем по decision_function; порог 0.5 не используется.
    """

    name = "logreg"

    def __init__(self, features, categorical=(), C=1.0):
        self.features = list(features)
        self.categorical = tuple(categorical)
        self.numeric = [f for f in self.features if f not in self.categorical]
        self.C = C

    def _levels_values(self, data, feature):
        return _category_values(data[feature], missing_as_neutral=True)

    def _matrix(self, data):
        columns = []
        for f in self.numeric:
            v = pd.to_numeric(data[f], errors="coerce").fillna(self.median_[f])
            columns.append(((v - self.mean_[f]) / self.std_[f]).to_numpy(dtype=float))
        for f in self.categorical:
            values = self._levels_values(data, f)
            for level in self.levels_[f]:
                columns.append((values == level).to_numpy(dtype=float))
        return np.column_stack(columns) if columns else np.zeros((len(data), 0))

    def fit(self, train):
        self.median_, self.mean_, self.std_, self.levels_ = {}, {}, {}, {}
        for f in self.numeric:
            v = pd.to_numeric(train[f], errors="coerce")
            self.median_[f] = float(v.median()) if v.notna().any() else 0.0
            filled = v.fillna(self.median_[f])
            self.mean_[f] = float(filled.mean())
            std = float(filled.std(ddof=0))
            self.std_[f] = std if std > 0 else 1.0  # константный признак не даёт информации
        for f in self.categorical:
            self.levels_[f] = sorted(self._levels_values(train, f).dropna().unique().tolist())
        self.clf_ = LogisticRegression(
            C=self.C, class_weight="balanced", solver="lbfgs", max_iter=5000, tol=1e-8
        )
        self.clf_.fit(self._matrix(train), train[TARGET].to_numpy(dtype=int))
        return self

    def score(self, data):
        return self.clf_.decision_function(self._matrix(data))

    def coverage(self, data):
        rows = []
        for f in self.numeric:
            rows.append({"feature": f, "test_missing": int(pd.to_numeric(data[f], errors="coerce").isna().sum()),
                         "test_unseen": 0, "test_cells": len(data)})
        for f in self.categorical:
            values = self._levels_values(data, f)
            rows.append({"feature": f, "test_missing": int(values.isna().sum()),
                         "test_unseen": int((values.notna() & ~values.isin(self.levels_[f])).sum()),
                         "test_cells": len(data)})
        return pd.DataFrame(rows)
