import logging
import os
import sqlite3
import sys
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import (
    get_summary_page,
    get_responder_comparison_data,
    run_statistical_comparison,
    get_baseline_subset,
    summarize_baseline_subset,
    get_filter_options,
)
from backend.schemas import (
    Condition,
    Treatment,
    SampleType,
    SummaryResponse,
    ComparisonResponse,
    BaselineSubsetResponse,
    FilterOptionsResponse,
    HealthResponse,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cell-count.db")

app = FastAPI(title="Teiko Immune Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    logger.info(f"Starting API, using database at {DB_PATH}")
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}, run 'python load_data.py' first")


def get_connection():
    return sqlite3.connect(DB_PATH)


@app.get("/api/health", response_model=HealthResponse)
def health():
    db_status = "connected" if os.path.exists(DB_PATH) else "missing"
    return HealthResponse(status="ok", database=db_status)


@app.get("/api/summary", response_model=SummaryResponse)
def summary(
    sample_search: str = "",
    population: str = "",
    page: int = 1,
    page_size: int = 50,
):
    conn = get_connection()
    df, total_samples = get_summary_page(conn, sample_search, population, page, page_size)
    conn.close()

    return SummaryResponse(
        rows=df.to_dict(orient="records"),
        total_samples=total_samples,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total_samples // page_size)),
    )


@lru_cache(maxsize=128)
def _cached_comparison(condition: str, treatment: str, sample_type: str):
    conn = get_connection()
    comparison_df = get_responder_comparison_data(conn, condition, treatment, sample_type)
    stats_df = run_statistical_comparison(comparison_df)
    conn.close()

    data_points = (
        comparison_df[["population", "response", "percentage"]].to_dict(orient="records")
        if not comparison_df.empty
        else []
    )
    stats_df = stats_df.where(pd.notnull(stats_df), None)
    stats = stats_df.to_dict(orient="records")

    return {"data_points": data_points, "stats": stats}


@app.get("/api/comparison", response_model=ComparisonResponse)
def comparison(
    condition: Condition = Condition.melanoma,
    treatment: Treatment = Treatment.miraclib,
    sample_type: SampleType = SampleType.PBMC,
):
    return _cached_comparison(condition.value, treatment.value, sample_type.value)


@lru_cache(maxsize=128)
def _cached_baseline_subset(condition: str, treatment: str, sample_type: str, time_from_treatment_start: int):
    conn = get_connection()
    baseline_df = get_baseline_subset(conn, condition, treatment, sample_type, time_from_treatment_start)
    summary_dict = summarize_baseline_subset(baseline_df)
    conn.close()

    return {
        "total_samples": int(baseline_df["sample"].nunique()),
        "samples_per_project": summary_dict["samples_per_project"].to_dict(),
        "subjects_by_response": summary_dict["subjects_by_response"].to_dict(),
        "subjects_by_sex": summary_dict["subjects_by_sex"].to_dict(),
        "subjects_by_age_group": summary_dict["subjects_by_age_group"].to_dict(),
    }


@app.get("/api/baseline-subset", response_model=BaselineSubsetResponse)
def baseline_subset(
    condition: Condition = Condition.melanoma,
    treatment: Treatment = Treatment.miraclib,
    sample_type: SampleType = SampleType.PBMC,
    time_from_treatment_start: int = 0,
):
    return _cached_baseline_subset(
        condition.value, treatment.value, sample_type.value, time_from_treatment_start
    )


@app.get("/api/filter-options", response_model=FilterOptionsResponse)
def filter_options():
    conn = get_connection()
    options = get_filter_options(conn)
    conn.close()
    return options