"""Шаг 1. Осмотр файлов Henan: сколько слоёв, какая сетка, где «нет данных».

Запуск из корня репозитория:
    python backend/scripts/henan_inspect.py --evidence "data/external/henan/raw/evidence layers_georeferencing.tif" \
                                            --deposit  "data/external/henan/raw/deposit.tif"
Ничего не меняет, только печатает. По выводу вы заполняете configs/henan.json (раздел build).
"""
import argparse
import sys

try:
    import numpy as np
    import rasterio
except ImportError:
    sys.exit("Нужен rasterio: pip install -e \".[geo]\"")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--deposit", required=True)
    a = ap.parse_args()

    with rasterio.open(a.evidence) as ev:
        print(f"== {a.evidence}")
        print(f"слоёв: {ev.count}; строк x столбцов: {ev.height} x {ev.width}; CRS: {ev.crs}")
        print(f"размер ячейки: {ev.res}; левый верхний угол: ({ev.transform.c}, {ev.transform.f}); nodata: {ev.nodata}")
        print(f"типы слоёв: {sorted(set(ev.dtypes))}")
        print("\n№ слоя | описание в файле | min | max | доля NaN/nodata | уник. значений")
        for i in range(1, ev.count + 1):
            arr = ev.read(i).astype("float64")
            if ev.nodata is not None:
                arr[arr == ev.nodata] = np.nan
            valid = arr[np.isfinite(arr)]
            desc = (ev.descriptions[i - 1] or "").strip() or "-"
            if valid.size:
                print(f"{i:>3} | {desc[:40]:<40} | {valid.min():>12.4g} | {valid.max():>12.4g} | "
                      f"{1 - valid.size / arr.size:>6.3f} | {len(np.unique(valid)):>7}")
            else:
                print(f"{i:>3} | {desc[:40]:<40} | (пусто)")
        shape, transform = (ev.height, ev.width), ev.transform

    with rasterio.open(a.deposit) as dep:
        lab = dep.read(1)
        print(f"\n== {a.deposit}")
        print(f"слоёв: {dep.count}; {dep.height} x {dep.width}; CRS: {dep.crs}; nodata: {dep.nodata}")
        print(f"значения: {dict(zip(*np.unique(lab, return_counts=True)))}")
        same = (dep.height, dep.width) == shape and all(
            abs(x - y) < 1e-6 for x, y in zip(dep.transform[:6], transform[:6]))
        print("СЕТКА СОВПАДАЕТ с evidence:", "да" if same else "НЕТ — сначала разберитесь с этим!")


if __name__ == "__main__":
    main()
