import logging
import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

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

def _parse_sample_search(search: str):
    """
    Parses a sample search string into a SQL WHERE clause fragment and params.
    Supports comma separated terms, colon separated inclusive ranges, and
    combinations of both, e.g.

    sample00001                              substring match
    sample00001,sample00005                  multiple matches
    sample00001:sample00010                  inclusive range
    sample00001:sample00010,sample00050      combination

    Ranges rely on sample IDs being zero padded to a fixed width, so string
    comparison sorts the same as numeric comparison.
    """
    search = search.strip()
    if not search:
        return "1=1", []

    clauses = []
    params = []

    for raw_token in search.split(","):
        token = raw_token.strip()
        if not token:
            continue

        if ":" in token:
            start, end = [t.strip() for t in token.split(":", 1)]
            if start and end:
                if start > end:
                    start, end = end, start
                clauses.append("sample_id BETWEEN ? AND ?")
                params.extend([start, end])
            elif start:
                clauses.append("sample_id LIKE ?")
                params.append(f"%{start}%")
            elif end:
                clauses.append("sample_id LIKE ?")
                params.append(f"%{end}%")
        else:
            clauses.append("sample_id LIKE ?")
            params.append(f"%{token}%")

    if not clauses:
        return "1=1", []

    return "(" + " OR ".join(clauses) + ")", params

def get_summary_page(
    conn: sqlite3.Connection,
    sample_search: str = "",
    population: str = "",
    page: int = 1,
    page_size: int = 50,
):
    """
    Paginated, searchable version of the Part 2 summary table, used by the dashboard.
    sample_search supports comma separated terms and colon separated ranges,
    see _parse_sample_search for details.
    """
    offset = (page - 1) * page_size
    where_clause, where_params = _parse_sample_search(sample_search)

    total_samples = pd.read_sql_query(
        f"SELECT COUNT(*) as n FROM samples WHERE {where_clause}",
        conn,
        params=where_params,
    )["n"].iloc[0]

    sample_ids_df = pd.read_sql_query(
        f"SELECT sample_id FROM samples WHERE {where_clause} ORDER BY sample_id LIMIT ? OFFSET ?",
        conn,
        params=where_params + [page_size, offset],
    )
    sample_ids = sample_ids_df["sample_id"].tolist()

    empty_columns = ["sample", "total_count", "population", "count", "percentage"]
    if not sample_ids:
        return pd.DataFrame(columns=empty_columns), int(total_samples)

    placeholders = ",".join("?" for _ in sample_ids)
    query = f"""
        SELECT sample_id AS sample, population, count
        FROM cell_counts
        WHERE sample_id IN ({placeholders})
    """
    df = pd.read_sql_query(query, conn, params=sample_ids)

    totals = df.groupby("sample")["count"].sum().rename("total_count")
    df = df.merge(totals, on="sample")
    df["percentage"] = (df["count"] / df["total_count"]) * 100

    if population:
        df = df[df["population"] == population]

    df = df[empty_columns].sort_values(["sample", "population"]).reset_index(drop=True)

    return df, int(total_samples)

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

    Alongside the p-value, this reports two effect size measures derived
    from the same U statistic:

    - effect_size (rank biserial correlation), ranges -1 to 1. Positive
      means responders trend higher than non-responders for that
      population, negative means the reverse. Magnitude reflects how
      separated the two groups are, independent of sample size, unlike
      the p-value which conflates the two.
    - auc, ranges 0 to 1. Treats the population's percentage as a simple
      one-feature classifier for response, 0.5 means no better than
      chance, 1.0 means perfect separation. auc = (effect_size + 1) / 2,
      it's the same underlying rank statistic expressed as a probability
      instead of a correlation.

    A population can be statistically significant (low p-value) while
    still having auc close to 0.5, this means the group difference is
    real but the two distributions overlap too much to reliably predict
    an individual's response from that population alone.
    """
    columns = [
        "population", "responder_median_pct", "non_responder_median_pct",
        "p_value", "significant", "effect_size", "auc",
    ]

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
                "effect_size": None,
                "auc": None,
            })
            continue

        stat, p_value = mannwhitneyu(responders, non_responders, alternative="two-sided")

        n1, n2 = len(responders), len(non_responders)
        auc = stat / (n1 * n2)
        effect_size = (2 * auc) - 1

        results.append({
            "population": population,
            "responder_median_pct": responders.median(),
            "non_responder_median_pct": non_responders.median(),
            "p_value": p_value,
            "significant": p_value < 0.05,
            "effect_size": effect_size,
            "auc": auc,
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
        logger.info(f"Saved {out_path}")

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
        logger.error(f"Could not find {DB_PATH}. Run load_data.py first.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    summary_df = get_summary_table(conn)
    summary_path = os.path.join(OUTPUT_DIR, "summary_table.csv")
    summary_df.to_csv(summary_path, index=False)
    logger.info(f"Part 2, summary table saved to {summary_path}")
    print(summary_df.head(10))

    comparison_df = get_responder_comparison_data(conn)
    print()
    logger.info(f"Part 3, filtered sample count: {comparison_df['sample'].nunique()}")
    logger.info("Part 3, responder breakdown:")
    print(comparison_df.drop_duplicates("subject_id")["response"].value_counts())

    stats_df = run_statistical_comparison(comparison_df)
    stats_path = os.path.join(OUTPUT_DIR, "statistical_comparison.csv")
    stats_df.to_csv(stats_path, index=False)
    print()
    logger.info(f"Part 3, statistical comparison saved to {stats_path}")
    print(stats_df)

    make_boxplots(comparison_df, OUTPUT_DIR)

    baseline_df = get_baseline_subset(conn)
    baseline_path = os.path.join(OUTPUT_DIR, "baseline_subset.csv")
    baseline_df.to_csv(baseline_path, index=False)

    summary = summarize_baseline_subset(baseline_df)
    print()
    logger.info(f"Part 4, baseline subset saved to {baseline_path}")
    logger.info(f"Total baseline samples: {baseline_df['sample'].nunique()}")
    print()
    logger.info("Samples per project")
    print(summary["samples_per_project"])
    print()
    logger.info("Subjects by response")
    print(summary["subjects_by_response"])
    print()
    logger.info("Subjects by sex")
    print(summary["subjects_by_sex"])

    conn.close()


if __name__ == "__main__":
    main()