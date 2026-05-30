"""Convert the 5 Excel files into a single normalized CSV the data-service will replay.

Strategy
--------
* read every sheet, normalize column names from Cyrillic to ASCII keys
* parse the human-readable DPE column into a real timestamp
* drop rows with bad/missing timestamps
* keep ALL 26 sensor channels we found in the source files
* down-sample with a stride so the resulting file is ~2.5k rows total —
  enough to be visibly varied on the dashboard without bloating Postgres
* compute baseline statistics (mean / std / p05 / p95) per sensor and dump
  them into baselines.json so the live-ingest loop can mix in realistic noise
"""
import json
import os
from pathlib import Path

import pandas as pd

SRC_DIR = Path(r"C:\Users\sdzim\Downloads\Telegram Desktop")
OUT_DIR = Path(r"C:\Users\sdzim\ventilation-dss\db")
OUT_DIR.mkdir(parents=True, exist_ok=True)

COLMAP = {
    "Швидкість вітру":              "wind_speed",
    "Напрям вітру":                 "wind_direction",
    "Тиск КП":                      "pressure_kp",
    "Тиск ОО":                      "pressure_oo",
    "Витрата КП+":                  "flow_kp_in",
    "Витрата ОО-":                  "flow_oo_out",
    "Витрата ОО+":                  "flow_oo_in",
    "Перепад КП-ОС":                "dp_kp_os",
    "Перепад ОО-ОС 8-й":            "dp_oo_os_8",
    "Перепад ОО-ОС BU 9-й":         "dp_oo_os_9",
    "Перепад КП-ОО":                "dp_kp_oo",
    "Перепад КП-ОО BY 11-10":       "dp_kp_oo_by",
    "Перепад КП-ОО BZ_8":           "dp_kp_oo_bz",
    "Перепад КП-ОО CA":             "dp_kp_oo_ca",
    "Густина повітря":              "air_density",
    "ГУ Тиск західна стінка":       "gu_pressure_west_wall",
    "ГУ Тиск східна стінка":        "gu_pressure_east_wall",
    "ГУ Тиск циліндрична стінка":   "gu_pressure_cyl_wall",
    "ГУ Тиск західний зазор":       "gu_pressure_west_gap",
    "ГУ Тиск східний зазор":        "gu_pressure_east_gap",
    "ГУ Тиск ВСРО":                 "gu_pressure_vsro",
    "ГУ СКО тиск 008p BQ":          "gu_sigma_008",
    "ГУ СКО тиск 009p BR":          "gu_sigma_009",
    "ГУ СКО тиск КП-ОС BS":         "gu_sigma_kp_os",
}

FILES = [
    "output_sum 2020 (1).xlsx",
    "output_sum 2021.xlsx",
    "output_sum 2022.xlsx",
    "output_sum 2023.xlsx",
    "output_sum 2024.xlsx",
]


def parse_dpe(v):
    if pd.isna(v):
        return pd.NaT
    if isinstance(v, pd.Timestamp):
        return v
    s = str(v).strip()
    for fmt in ("%Y.%m.%d %H:%M:%S.%f", "%Y.%m.%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S",   "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            pass
    try:
        return pd.to_datetime(s)
    except Exception:
        return pd.NaT


frames = []
for fname in FILES:
    p = SRC_DIR / fname
    print("reading", fname)
    xl = pd.ExcelFile(p)
    sheet = xl.sheet_names[0]
    df = pd.read_excel(p, sheet_name=sheet)

    rename = {c: COLMAP[c] for c in df.columns if c in COLMAP}
    keep = list(rename.values())
    df = df.rename(columns=rename)

    if "DPE" not in df.columns:
        print("  no DPE col, skipping")
        continue
    df["ts"] = df["DPE"].apply(parse_dpe)
    df = df.dropna(subset=["ts"])

    df = df[["ts"] + [c for c in keep if c in df.columns]].copy()
    frames.append(df)

merged = pd.concat(frames, ignore_index=True)
print("merged shape", merged.shape)

for key in COLMAP.values():
    if key not in merged.columns:
        merged[key] = pd.NA

merged = merged.sort_values("ts").reset_index(drop=True)

for c in merged.columns:
    if c == "ts":
        continue
    merged[c] = pd.to_numeric(merged[c], errors="coerce")

data_cols = [c for c in merged.columns if c != "ts"]
merged = merged.dropna(subset=data_cols, how="all")

TARGET = 2500
stride = max(1, len(merged) // TARGET)
sampled = merged.iloc[::stride].reset_index(drop=True)
print("sampled to", len(sampled), "rows (stride", stride, ")")

sampled = sampled.ffill().bfill()

csv_path = OUT_DIR / "ventilation_history.csv"
sampled.to_csv(csv_path, index=False, encoding="utf-8")
print("wrote", csv_path)

stats = {}
for c in data_cols:
    s = sampled[c].dropna().astype(float)
    if len(s) == 0:
        continue
    stats[c] = {
        "mean":  float(s.mean()),
        "std":   float(s.std(ddof=0)),
        "min":   float(s.min()),
        "max":   float(s.max()),
        "p05":   float(s.quantile(0.05)),
        "p50":   float(s.median()),
        "p95":   float(s.quantile(0.95)),
        "count": int(len(s)),
    }

stats_path = OUT_DIR / "ventilation_baselines.json"
stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", stats_path)
print("\nper-channel summary:")
for k, v in stats.items():
    print(f"  {k:24s} mean={v['mean']:10.3f}  std={v['std']:9.3f}  "
          f"[{v['min']:9.2f} … {v['max']:9.2f}]  n={v['count']}")
