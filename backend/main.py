import os
import sqlite3
import sys
import pandas as pd

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import (
    get_summary_table,
    get_responder_comparison_data,
    run_statistical_comparison,
    get_baseline_subset,
    summarize_baseline_subset,
    get_filter_options,
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cell-count.db")

app = FastAPI(title="Teiko Immune Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection():
    return sqlite3.connect(DB_PATH)


@app.get("/api/summary")
def summary():
    conn = get_connection()
    df = get_summary_table(conn)
    conn.close()
    return df.to_dict(orient="records")


@app.get("/api/comparison")
def comparison(
    condition: str = "melanoma",
    treatment: str = "miraclib",
    sample_type: str = "PBMC",
):
    conn = get_connection()
    comparison_df = get_responder_comparison_data(conn, condition, treatment, sample_type)
    stats_df = run_statistical_comparison(comparison_df)
    conn.close()

    data_points = comparison_df[["population", "response", "percentage"]].to_dict(orient="records") if not comparison_df.empty else []
    stats_df = stats_df.where(pd.notnull(stats_df), None)
    stats = stats_df.to_dict(orient="records")

    return {"data_points": data_points, "stats": stats}


@app.get("/api/baseline-subset")
def baseline_subset(
    condition: str = "melanoma",
    treatment: str = "miraclib",
    sample_type: str = "PBMC",
    time_from_treatment_start: int = 0,
):
    conn = get_connection()
    baseline_df = get_baseline_subset(conn, condition, treatment, sample_type, time_from_treatment_start)
    summary_dict = summarize_baseline_subset(baseline_df)
    conn.close()

    return {
        "total_samples": int(baseline_df["sample"].nunique()),
        "samples_per_project": summary_dict["samples_per_project"].to_dict(),
        "subjects_by_response": summary_dict["subjects_by_response"].to_dict(),
        "subjects_by_sex": summary_dict["subjects_by_sex"].to_dict(),
    }

@app.get("/api/filter-options")
def filter_options():
    conn = get_connection()
    options = get_filter_options(conn)
    conn.close()
    return options