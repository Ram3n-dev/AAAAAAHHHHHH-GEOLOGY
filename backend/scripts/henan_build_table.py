"""Шаг 2. Сборка таблицы признаков Henan: одна строка = одна ячейка.

Запуск из корня репозитория:
    python backend/scripts/henan_build_table.py configs/henan.json
Читает GeoTIFF (раздел "build" конфига), даёт слоям имена по группам, отбрасывает
ячейки вне района и сохраняет CSV и отчёт качества. Обучения здесь нет.
"""
import json
import sys
from pathlib import Path

try:
    import numpy as np
    import rasterio
except ImportError:
    sys.exit("Нужен rasterio: pip install -e \".[geo]\"")

from geolens import parse_band_groups, stack_to_table, table_qa


def main():
    cfg_path = Path(sys.argv[1]).resolve()
    root = cfg_path.parent.parent  # корень репозитория: configs/ лежит прямо в нём
    b = json.loads(cfg_path.read_text(encoding="utf-8"))["build"]

    with rasterio.open(root / b["evidence_tif"]) as ev:
        stack, nodata, transform, crs = ev.read(), ev.nodata, ev.transform, ev.crs
    with rasterio.open(root / b["deposit_tif"]) as dep:
        labels, dep_nodata, dep_transform = dep.read(1), dep.nodata, dep.transform
    if stack.shape[1:] != labels.shape or not np.allclose(tuple(transform)[:6], tuple(dep_transform)[:6], atol=1e-6):
        sys.exit("Сетка меток не совпадает с сеткой слоёв. Остановитесь и разберитесь (CRS/смещение/размер).")
    if abs(abs(transform.a) - abs(transform.e)) > 1e-6:
        sys.exit("Ячейки не квадратные: протокол рассчитан на квадратную сетку.")
    if dep_nodata is not None:
        labels = np.where(labels == dep_nodata, 0, labels)
    labels = np.where(np.isfinite(labels) & (labels > 0), 1, 0)

    names, categorical, exclude = parse_band_groups(
        b["groups"], stack.shape[0], b.get("categorical_groups", []), b.get("exclude_groups", []))
    table = stack_to_table(stack, names, transform.c, transform.f, abs(transform.a), labels,
                           nodata=nodata, categorical=categorical, exclude=exclude)

    features = [n for n in names if n not in set(exclude)]
    qa = table_qa(table, features)
    qa.update({"crs": str(crs), "pixel_size_m": abs(transform.a), "excluded_bands": exclude,
               "categorical_bands": categorical, "labels_positive_cells_in_file": int(labels.sum())})
    out = root / b["out_table"]
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False, encoding="utf-8")
    out.with_name("table_qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Сохранено: {out}")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    if qa["positive_cells"] != qa["labels_positive_cells_in_file"]:
        print("ВНИМАНИЕ: часть положительных ячеек вне района (нет данных) — они потеряны. Проверьте!")
    print(f"\nПоложительных ячеек: {qa['positive_cells']}, объектов (склеенных соседей): {qa['positive_objects']}. "
          "Сверьте с числом месторождений в статье (51) и запишите причину расхождения в журнал.")


if __name__ == "__main__":
    main()
