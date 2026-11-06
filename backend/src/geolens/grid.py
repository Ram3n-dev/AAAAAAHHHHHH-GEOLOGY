"""Из растрового стека слоёв — в таблицу «одна строка = одна ячейка».

Функции здесь работают с обычными массивами numpy и не требуют rasterio:
чтение GeoTIFF делают скрипты в backend/scripts. Так логику можно проверить
тестами без реальных файлов.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import ndimage


def label_clusters(labels: np.ndarray, connectivity: int = 8) -> tuple[np.ndarray, int]:
    """Склеивает соседние положительные ячейки в «объекты».

    Одно месторождение может занимать несколько соседних ячеек; считать их
    независимыми примерами нельзя. Возвращает (массив номеров объектов, их число);
    фон = 0.
    """
    structure = np.ones((3, 3)) if connectivity == 8 else None
    return ndimage.label(np.asarray(labels) > 0, structure=structure)


def stack_to_table(
    stack: np.ndarray,
    band_names,
    left: float,
    top: float,
    pixel_size: float,
    labels: np.ndarray,
    nodata=None,
    categorical=(),
    exclude=(),
) -> pd.DataFrame:
    """Строит таблицу ячеек.

    stack       — массив (слои, строки, столбцы).
    band_names  — имена слоёв (столько же, сколько слоёв).
    left, top   — координаты ЛЕВОГО ВЕРХНЕГО УГЛА растра (в метрах проекции), pixel_size — размер ячейки.
    labels      — массив (строки, столбцы): >0 там, где известное месторождение.
    nodata      — значение «нет данных» (превращается в NaN).
    categorical — имена слоёв-категорий (коды классов, не числа).
    exclude     — слои, которые не нужно переносить в таблицу.

    Ячейки, где НЕТ данных ни в одном слое (вне района), отбрасываются.
    Колонки: x, y (центры ячеек), row, col, is_deposit, entity_id (номер объекта, 0 у фона), слои.
    """
    stack = np.asarray(stack)
    names = list(band_names)
    if stack.ndim != 3 or stack.shape[0] != len(names):
        raise ValueError(f"stack {stack.shape} не соответствует {len(names)} именам слоёв.")
    if len(set(names)) != len(names):
        raise ValueError("Имена слоёв должны быть уникальными.")
    bands, rows, cols = stack.shape
    labels = np.asarray(labels)
    if labels.shape != (rows, cols):
        raise ValueError(f"Размеры меток {labels.shape} не совпадают с растром {(rows, cols)}.")
    unknown = (set(categorical) | set(exclude)) - set(names)
    if unknown:
        raise ValueError(f"В categorical/exclude есть неизвестные слои: {sorted(unknown)}")

    data = stack.astype("float64", copy=True)
    if nodata is not None:
        data[data == nodata] = np.nan
    data[~np.isfinite(data)] = np.nan

    row_idx, col_idx = np.indices((rows, cols))
    cluster_ids, _ = label_clusters(labels)
    table = pd.DataFrame(
        {
            "x": left + (col_idx.ravel() + 0.5) * pixel_size,
            "y": top - (row_idx.ravel() + 0.5) * pixel_size,
            "row": row_idx.ravel(),
            "col": col_idx.ravel(),
            "is_deposit": (labels.ravel() > 0).astype(int),
            "entity_id": cluster_ids.ravel(),
        }
    )
    kept = [n for n in names if n not in set(exclude)]
    for name in kept:
        values = pd.Series(data[names.index(name)].ravel())
        if name in categorical:
            values = values.map(lambda v: str(int(v)) if pd.notna(v) else np.nan)
        table[name] = values
    inside = ~np.isnan(data).all(axis=0).ravel()  # есть хоть какие-то данные
    return table.loc[inside].reset_index(drop=True)


def table_qa(table: pd.DataFrame, features) -> dict:
    """Короткий отчёт о качестве таблицы: размеры, метки, пропуски, константные слои."""
    pos = table[table.is_deposit.eq(1)]
    missing = {f: float(table[f].isna().mean()) for f in features}
    constant = [f for f in features if table[f].nunique(dropna=True) <= 1]
    return {
        "cells": int(len(table)),
        "positive_cells": int(len(pos)),
        "positive_objects": int(pos.entity_id.nunique()),
        "duplicate_xy": int(table.duplicated(["x", "y"]).sum()),
        "features_with_missing": {f: round(v, 4) for f, v in missing.items() if v > 0},
        "constant_features": constant,
    }


def parse_band_groups(groups: dict, n_bands: int, categorical_groups=(), exclude_groups=()):
    """Даёт слоям понятные имена по группам и отмечает категориальные и исключаемые.

    groups — например {"geochem": "1-39", "magnetic": [40], "formation": "41-42"}
             (номера слоёв считаются С ЕДИНИЦЫ, как в QGIS; можно списком или диапазоном "a-b").
    Имя слоя: <группа>_b<номер>, например geochem_b07 — так по имени всегда видно, откуда слой.
    Каждый слой должен попасть ровно в одну группу, иначе ошибка (молчаливых пропусков нет).
    Возвращает (band_names, categorical_names, exclude_names).
    """

    def indices(spec):
        if isinstance(spec, str):
            if spec.strip().upper() == "TODO":
                raise ValueError("В конфиге остался TODO: заполните номера слоёв группы.")
            out = []
            for part in spec.split(","):
                a, _, b = part.strip().partition("-")
                out.extend(range(int(a), int(b or a) + 1))
            return out
        return [int(i) for i in spec]

    owner = {}
    for group, spec in groups.items():
        for i in indices(spec):
            if not 1 <= i <= n_bands:
                raise ValueError(f"Слой {i} (группа {group}) вне диапазона 1..{n_bands}.")
            if i in owner:
                raise ValueError(f"Слой {i} входит в две группы: {owner[i]} и {group}.")
            owner[i] = group
    missing = sorted(set(range(1, n_bands + 1)) - set(owner))
    if missing:
        raise ValueError(f"Слои без группы: {missing}. Отнесите каждый слой к какой-то группе.")
    names = [f"{owner[i]}_b{i:02d}" for i in range(1, n_bands + 1)]
    pick = lambda groups_: [n for n, i in zip(names, range(1, n_bands + 1)) if owner[i] in set(groups_)]
    unknown = (set(categorical_groups) | set(exclude_groups)) - set(groups)
    if unknown:
        raise ValueError(f"Неизвестные группы: {sorted(unknown)}")
    return names, pick(categorical_groups), pick(exclude_groups)
