"""
analysis.py

Contains the core analysis functions for Parts 2 through 4,
plus a main() that runs the full pipeline and saves outputs.
"""

import os
import sqlite3

import pandas as pd

DB_PATH = "cell-count.db"
OUTPUT_DIR = "outputs"


def get_summary_table(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Part 2, relative frequency of each cell population per sample.

    Returns a dataframe with columns
    sample, total_count, population, count, percentage
    """
    query = """
        SELECT sample_id AS sample, population, count
        FROM cell_counts
    """
    df = pd.read_sql_query(query, conn)

    totals = df.groupby("sample")["count"].sum().rename("total_count")
    df = df.merge(totals, on="sample")

    df["percentage"] = (df["count"] / df["total_count"]) * 100

    df = df[["sample", "total_count", "population", "count", "percentage"]]
    df = df.sort_values(["sample", "population"]).reset_index(drop=True)

    return df


def main():
    if not os.path.exists(DB_PATH):
        print(f"Could not find {DB_PATH}. Run load_data.py first.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    summary_df = get_summary_table(conn)
    summary_path = os.path.join(OUTPUT_DIR, "summary_table.csv")
    summary_df.to_csv(summary_path, index=False)
    print(f"Part 2, summary table saved to {summary_path}")
    print(summary_df.head(10))

    conn.close()


if __name__ == "__main__":
    main()