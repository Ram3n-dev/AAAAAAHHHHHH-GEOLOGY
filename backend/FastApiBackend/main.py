"""
GeoLens backend (костыльный пока что)
"""

import pandas as pd
import csv
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from fastapi.middleware.cors import CORSMiddleware

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from geolens import load_model, explain_cell, score_woe




# Yenisei Ridge prototype area (docs, R-004).
LAT = (58.5, 60.6)
LON = (92.3, 95.0)
FEATURES = ["elevation", "magnetic", "gravity",
            "lithology_group", "dist_fault_km", "dist_contact_km"]



# backend/main.py -> repo/data/processed/features_table_geo.csv
def _find_file(relative: str) -> Path:
    name = Path(relative)
    for base in Path(__file__).resolve().parents:
        candidate = base / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"File not found: {name} (searched upwards from {__file__})")


TABLE = _find_file("data/processed/features_table_geo.csv")
MODEL_PATH = _find_file("data/processed/woe_model.json")
MODEL = load_model(MODEL_PATH)


CELLS = []
with TABLE.open(newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        CELLS.append({
            "x": float(row["x"]), "y": float(row["y"]),
            "latitude": float(row["latitude"]), "longitude": float(row["longitude"]),
            "is_deposit": row["is_deposit"] == "1",
            "deposit_name": row["deposit_name"] or None,
            "fold_id": int(row["fold_id"]),
            "elevation": float(row["elevation"]),
            "magnetic": float(row["magnetic"]),
            "gravity": float(row["gravity"]),
            "lithology_group": row["lithology_group"] or None,
            "dist_fault_km": float(row["dist_fault_km"]),
            "dist_contact_km": float(row["dist_contact_km"]),
        })
DEPOSITS = [c for c in CELLS if c["is_deposit"]]
_SCORES = score_woe(pd.DataFrame(CELLS), MODEL)
_SCORE_PCT = _SCORES.rank(pct=True)
_N_BINS = len(MODEL["elevation"]["edges"]) - 1

# --- Р-5: растр оценок (PNG), строится один раз при старте.
# ячеек 35 694, полный прямоугольник 158 x 236 = 37 288 позиций,
# 1 594 позиции пустые (граница площади неправильной формы) —
# в растре это фон, а не нулевая оценка. цвет — перцентиль (0..1), viridis.
def _build_scores_png() -> bytes:
    xs = sorted({c["x"] for c in CELLS})
    ys = sorted({c["y"] for c in CELLS}, reverse=True)
    xi = {v: i for i, v in enumerate(xs)}
    yi = {v: i for i, v in enumerate(ys)}
    grid = np.full((len(ys), len(xs)), np.nan)
    for n, c in enumerate(CELLS):
        grid[yi[c["y"]], xi[c["x"]]] = float(_SCORE_PCT.iloc[n])
    masked = np.ma.masked_invalid(grid)
    fig, ax = plt.subplots(figsize=(7, 10))
    img = ax.imshow(masked, cmap="viridis", vmin=0, vmax=1,
                    extent=(LON[0], LON[1], LAT[0], LAT[1]), aspect="auto")
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_title("GeoLens WoE score percentile (35,694 cells)")
    fig.colorbar(img, ax=ax, label="score percentile")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()

_SCORES_PNG = _build_scores_png()


app = FastAPI(title="GeoLens API", version="0.3.0")
app.add_middleware(  # dev only: lets the Vite app on :3000 call the API directly
    CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "table": TABLE.name,
            "cells": len(CELLS), "deposits": len(DEPOSITS), "features": FEATURES,
            "model": {"file": MODEL_PATH.name,
                      "features": list(MODEL.keys()),
                      "n_bins": _N_BINS}}


@app.get("/api/deposits")
def deposits():
    return [{"name": c["deposit_name"], "latitude": c["latitude"],
             "longitude": c["longitude"], "fold_id": c["fold_id"]} for c in DEPOSITS]


@app.get("/api/cell")
def cell(latitude: float = Query(..., ge=-90, le=90),
         longitude: float = Query(..., ge=-180, le=180)):
    """Nearest 1x1 km cell for a clicked point; 404 outside the area."""
    if not (LAT[0] <= latitude <= LAT[1] and LON[0] <= longitude <= LON[1]):
        raise HTTPException(404, "Нет данных: точка вне площади проекта "
                            "(58.5-60.6 с. ш., 92.3-95.0 в. д.)")
    idx = min(range(len(CELLS)),
              key=lambda i: (CELLS[i]["latitude"] - latitude) ** 2
                            + (CELLS[i]["longitude"] - longitude) ** 2)
    c = CELLS[idx]
    row = pd.Series({name: c[name] for name in FEATURES})
    explanation = explain_cell(row, MODEL)
    return {"latitude": c["latitude"], "longitude": c["longitude"],
            "x": c["x"], "y": c["y"], "fold_id": c["fold_id"],
            "is_deposit": c["is_deposit"], "deposit_name": c["deposit_name"],
            "features": {name: c[name] for name in FEATURES},
            "score": float(_SCORE_PCT.iloc[idx]),
            "score_raw": float(explanation["contribution"].sum()),
            "contributions": [
                {"feature": str(r.feature), "value": c[str(r.feature)],
                 "contribution": float(r.contribution)}
                for r in explanation.itertuples(index=False)
            ]}

@app.get("/api/scores.png")
def scores_png():
    """Растр перцентилей оценки по площади (Р-5). Строится при старте."""
    return Response(content=_SCORES_PNG, media_type="image/png")


@app.get("/api/scores.csv")
def scores_csv():
    """Все 35 694 ячейки с оценками, для ArcGIS (Р-5).

    Колонки: x, y, latitude, longitude, score, percentile.
    score — сырая сумма WoE (не вероятность);
    percentile — ранг этой суммы среди всех ячеек (0..1),
    то же значение, что /api/cell отдаёт как "score".
    """
    def rows():
        yield "x,y,latitude,longitude,score,percentile\n"
        for n, c in enumerate(CELLS):
            yield (f"{c['x']:.1f},{c['y']:.1f},{c['latitude']:.7f},"
                   f"{c['longitude']:.7f},{float(_SCORES.iloc[n]):.6f},"
                   f"{float(_SCORE_PCT.iloc[n]):.6f}\n")
    return StreamingResponse(rows(), media_type="text/csv",
                             headers={"Content-Disposition":
                                      'attachment; filename="scores.csv"'})


@app.get("/api/stats")
def stats():
    return {"cells": len(CELLS), "deposits": len(DEPOSITS),
            "area": {"lat_min": LAT[0], "lat_max": LAT[1],
                     "lon_min": LON[0], "lon_max": LON[1]},
            "features": FEATURES,
            "lithology_missing": sum(c["lithology_group"] is None for c in CELLS)}
