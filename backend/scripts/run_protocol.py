"""Шаг 3. Запуск протокола оценки по конфигу (любой регион).

Из корня репозитория:
    python backend/scripts/run_protocol.py configs/henan.json
    python backend/scripts/run_protocol.py configs/yenisei.json
Результаты — в папку out_dir из конфига; на экран печатается сводка.
"""
import json
import sys
from pathlib import Path

import pandas as pd

from geolens import run_protocol


def main():
    cfg_path = Path(sys.argv[1]).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))["protocol"]
    tables = run_protocol(cfg, root=cfg_path.parent.parent)

    pd.set_option("display.width", 200, "display.max_columns", 30)
    s = tables["summary"]
    cols = ["feature_set", "model", "area_fraction", "found_min", "found_expected", "found_max",
            "random_expected", "n_positive", "lift_vs_random"]
    print("\n=== Сводка: сколько месторождений найдено в верхних X% площади ===")
    print(s[cols].round(3).to_string(index=False))
    rb = tables["random_budget"]
    print("\n=== Случайный ориентир: вероятность найти не меньше N объектов НАУГАД ===")
    print(rb[rb.p_at_least > 0].round(4).to_string(index=False))
    print(f"\nВсе таблицы и manifest.json: {Path(cfg_path.parent.parent / cfg['out_dir'])}")


if __name__ == "__main__":
    main()
