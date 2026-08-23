import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu

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

def get_responder_comparison_data(
    conn: sqlite3.Connection,
    condition: str = "melanoma",
    treatment: str = "miraclib",
    sample_type: str = "PBMC",
) -> pd.DataFrame:
    """
    Part 3, filtered data for responder vs non-responder comparison.
    Defaults match the original assignment, melanoma, miraclib, PBMC.
    """
    query = """
        SELECT
            s.sample_id AS sample,
            sub.subject_id,
            sub.response,
            cc.population,
            cc.count
        FROM samples s
        JOIN subjects sub ON s.subject_id = sub.subject_id
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
        WHERE sub.condition = ?
          AND sub.treatment = ?
          AND s.sample_type = ?
    """
    df = pd.read_sql_query(query, conn, params=[condition, treatment, sample_type])

    totals = df.groupby("sample")["count"].sum().rename("total_count")
    df = df.merge(totals, on="sample")
    df["percentage"] = (df["count"] / df["total_count"]) * 100

    return df

def run_statistical_comparison(comparison_df: pd.DataFrame) -> pd.DataFrame:
    """
    Mann-Whitney U test per population, responders vs non-responders.
    Returns an empty, correctly shaped dataframe if there's no data
    or no valid comparison to run.
    """
    columns = ["population", "responder_median_pct", "non_responder_median_pct", "p_value", "significant"]

    if comparison_df.empty:
        return pd.DataFrame(columns=columns)

    results = []

    for population in sorted(comparison_df["population"].unique()):
        pop_df = comparison_df[comparison_df["population"] == population]

        responders = pop_df[pop_df["response"] == "yes"]["percentage"]
        non_responders = pop_df[pop_df["response"] == "no"]["percentage"]

        if len(responders) == 0 or len(non_responders) == 0:
            results.append({
                "population": population,
                "responder_median_pct": responders.median() if len(responders) else None,
                "non_responder_median_pct": non_responders.median() if len(non_responders) else None,
                "p_value": None,
                "significant": False,
            })
            continue

        stat, p_value = mannwhitneyu(responders, non_responders, alternative="two-sided")

        results.append({
            "population": population,
            "responder_median_pct": responders.median(),
            "non_responder_median_pct": non_responders.median(),
            "p_value": p_value,
            "significant": p_value < 0.05,
        })

    if not results:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(results).sort_values("p_value", na_position="last").reset_index(drop=True)


def make_boxplots(comparison_df: pd.DataFrame, output_dir: str) -> None:
    """
    Part 3, one boxplot per population, responders vs non-responders.
    """
    populations = sorted(comparison_df["population"].unique())

    for population in populations:
        pop_df = comparison_df[comparison_df["population"] == population]

        plt.figure(figsize=(5, 5))
        sns.boxplot(data=pop_df, x="response", y="percentage", order=["no", "yes"])
        sns.stripplot(data=pop_df, x="response", y="percentage", order=["no", "yes"],
                      color="black", alpha=0.3, size=3)
        plt.title(f"{population}, responders vs non-responders")
        plt.xlabel("Response to miraclib")
        plt.ylabel("Relative frequency (%)")
        plt.tight_layout()

        out_path = os.path.join(output_dir, f"boxplot_{population}.png")
        plt.savefig(out_path, dpi=150)
        plt.close()
        print(f"Saved {out_path}")

def get_baseline_subset(
    conn: sqlite3.Connection,
    condition: str = "melanoma",
    treatment: str = "miraclib",
    sample_type: str = "PBMC",
    time_from_treatment_start: int = 0,
) -> pd.DataFrame:
    """
    Part 4, filtered baseline samples.
    Defaults match the original assignment, melanoma, miraclib, PBMC, day 0.
    """
    query = """
        SELECT
            s.sample_id AS sample,
            sub.subject_id,
            sub.project_id,
            sub.response,
            sub.sex
        FROM samples s
        JOIN subjects sub ON s.subject_id = sub.subject_id
        WHERE sub.condition = ?
          AND sub.treatment = ?
          AND s.sample_type = ?
          AND s.time_from_treatment_start = ?
    """
    return pd.read_sql_query(
        query, conn, params=[condition, treatment, sample_type, time_from_treatment_start]
    )

def get_filter_options(conn: sqlite3.Connection) -> dict:
    """
    Returns the distinct values available for each filterable field,
    so the frontend can build dropdowns without hardcoding options.
    """
    conditions = pd.read_sql_query("SELECT DISTINCT condition FROM subjects", conn)["condition"].tolist()
    treatments = pd.read_sql_query("SELECT DISTINCT treatment FROM subjects", conn)["treatment"].tolist()
    sample_types = pd.read_sql_query("SELECT DISTINCT sample_type FROM samples", conn)["sample_type"].tolist()
    timepoints = pd.read_sql_query(
        "SELECT DISTINCT time_from_treatment_start FROM samples WHERE time_from_treatment_start IS NOT NULL",
        conn,
    )["time_from_treatment_start"].tolist()

    return {
        "conditions": sorted(conditions),
        "treatments": sorted(treatments),
        "sample_types": sorted(sample_types),
        "timepoints": sorted(timepoints),
    }

def summarize_baseline_subset(baseline_df: pd.DataFrame) -> dict:
    """
    Part 4, breakdowns by project, response, and sex.
    """
    subjects_df = baseline_df.drop_duplicates("subject_id")

    return {
        "samples_per_project": baseline_df.groupby("project_id")["sample"].nunique(),
        "subjects_by_response": subjects_df["response"].value_counts(),
        "subjects_by_sex": subjects_df["sex"].value_counts(),
    }

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

    comparison_df = get_responder_comparison_data(conn)
    print()
    print("Part 3, filtered sample count:", comparison_df["sample"].nunique())
    print("Part 3, responder breakdown:")
    print(comparison_df.drop_duplicates("subject_id")["response"].value_counts())

    stats_df = run_statistical_comparison(comparison_df)
    stats_path = os.path.join(OUTPUT_DIR, "statistical_comparison.csv")
    stats_df.to_csv(stats_path, index=False)
    print()
    print(f"Part 3, statistical comparison saved to {stats_path}")
    print(stats_df)

    make_boxplots(comparison_df, OUTPUT_DIR)

    baseline_df = get_baseline_subset(conn)
    baseline_path = os.path.join(OUTPUT_DIR, "baseline_subset.csv")
    baseline_df.to_csv(baseline_path, index=False)

    summary = summarize_baseline_subset(baseline_df)
    print()
    print(f"Part 4, baseline subset saved to {baseline_path}")
    print("Total baseline samples:", baseline_df["sample"].nunique())
    print()
    print("Samples per project")
    print(summary["samples_per_project"])
    print()
    print("Subjects by response")
    print(summary["subjects_by_response"])
    print()
    print("Subjects by sex")
    print(summary["subjects_by_sex"])

    conn.close()


if __name__ == "__main__":
    main()