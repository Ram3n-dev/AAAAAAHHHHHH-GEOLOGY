"""
GeoLens backend (костыльный пока что)
"""

import csv
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Yenisei Ridge prototype area (docs, R-004).
LAT = (58.5, 60.6)
LON = (92.3, 95.0)
FEATURES = ["elevation", "magnetic", "gravity",
            "lithology_group", "dist_fault_km", "dist_contact_km"]

# backend/main.py -> repo/data/processed/features_table_geo.csv
def _find_table() -> Path:
    name = Path("data") / "processed" / "features_table_geo.csv"
    for base in Path(__file__).resolve().parents:
        candidate = base / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Table not found: {name} (searched upwards from {__file__})")

TABLE = _find_table()

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

app = FastAPI(title="GeoLens API", version="0.1.0")
app.add_middleware(  # dev only: lets the Vite app on :3000 call the API directly
    CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "table": TABLE.name,
            "cells": len(CELLS), "deposits": len(DEPOSITS), "features": FEATURES}


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
    c = min(CELLS, key=lambda c: (c["latitude"] - latitude) ** 2
            + (c["longitude"] - longitude) ** 2)
    return {"latitude": c["latitude"], "longitude": c["longitude"],
            "x": c["x"], "y": c["y"], "fold_id": c["fold_id"],
            "is_deposit": c["is_deposit"], "deposit_name": c["deposit_name"],
            "features": {name: c[name] for name in FEATURES}}


@app.get("/api/stats")
def stats():
    return {"cells": len(CELLS), "deposits": len(DEPOSITS),
            "area": {"lat_min": LAT[0], "lat_max": LAT[1],
                     "lon_min": LON[0], "lon_max": LON[1]},
            "features": FEATURES,
            "lithology_missing": sum(c["lithology_group"] is None for c in CELLS)}
