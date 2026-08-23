import logging
import os
import sqlite3
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CSV_PATH = "cell-count.csv"
DB_PATH = "cell-count.db"

CELL_POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

SCHEMA = """
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY
);

CREATE TABLE subjects (
    subject_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    condition TEXT NOT NULL,
    age INTEGER NOT NULL,
    sex TEXT NOT NULL,
    treatment TEXT NOT NULL,
    response TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (project_id)
);

CREATE TABLE samples (
    sample_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    sample_type TEXT NOT NULL,
    time_from_treatment_start INTEGER,
    FOREIGN KEY (subject_id) REFERENCES subjects (subject_id)
);

CREATE TABLE cell_counts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id TEXT NOT NULL,
    population TEXT NOT NULL,
    count INTEGER NOT NULL,
    FOREIGN KEY (sample_id) REFERENCES samples (sample_id)
);

CREATE INDEX idx_subjects_project_id ON subjects (project_id);
CREATE INDEX idx_samples_subject_id ON samples (subject_id);
CREATE INDEX idx_cell_counts_sample_id ON cell_counts (sample_id);
CREATE INDEX idx_cell_counts_population ON cell_counts (population);
"""


def validate(df: pd.DataFrame) -> None:
    """Basic sanity checks on the raw data before loading."""
    errors = []

    if df["sample"].duplicated().any():
        errors.append("Duplicate sample IDs found in CSV.")

    valid_sex = {"M", "F"}
    bad_sex = set(df["sex"].unique()) - valid_sex
    if bad_sex:
        errors.append(f"Unexpected sex values: {bad_sex}")

    valid_response = {"yes", "no"}
    non_null_response = df["response"].dropna()
    bad_response = set(non_null_response.unique()) - valid_response
    if bad_response:
        errors.append(f"Unexpected response values: {bad_response}")

    for col in CELL_POPULATIONS:
        if (df[col] < 0).any():
            errors.append(f"Negative counts found in column {col}")

    # response should only be missing when treatment is 'none'
    missing_response = df[df["response"].isnull()]
    if not (missing_response["treatment"] == "none").all():
        errors.append(
            "Found missing response values for subjects with an active treatment."
        )

    if errors:
        logger.error("Validation failed:")
        for e in errors:
            logger.error(f" - {e}")
        sys.exit(1)

    logger.info("Validation passed.")


def build_database(df: pd.DataFrame, db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    projects_df = df[["project"]].drop_duplicates().rename(
        columns={"project": "project_id"}
    )
    projects_df.to_sql("projects", conn, if_exists="append", index=False)

    subjects_df = (
        df[["subject", "project", "condition", "age", "sex", "treatment", "response"]]
        .drop_duplicates(subset=["subject"])
        .rename(columns={"subject": "subject_id", "project": "project_id"})
    )
    subjects_df.to_sql("subjects", conn, if_exists="append", index=False)

    samples_df = df[
        ["sample", "subject", "sample_type", "time_from_treatment_start"]
    ].rename(columns={"sample": "sample_id", "subject": "subject_id"})
    samples_df.to_sql("samples", conn, if_exists="append", index=False)

    cell_counts_df = df.melt(
        id_vars=["sample"],
        value_vars=CELL_POPULATIONS,
        var_name="population",
        value_name="count",
    ).rename(columns={"sample": "sample_id"})
    cell_counts_df.to_sql("cell_counts", conn, if_exists="append", index=False)

    conn.commit()

    for table in ["projects", "subjects", "samples", "cell_counts"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        logger.info(f"{table}: {n} rows loaded")

    conn.close()


def main():
    if not os.path.exists(CSV_PATH):
        logger.error(f"Could not find {CSV_PATH} in the current directory.")
        sys.exit(1)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    df = pd.read_csv(CSV_PATH)
    validate(df)
    build_database(df, DB_PATH)
    logger.info(f"Database created at {DB_PATH}")


if __name__ == "__main__":
    main()