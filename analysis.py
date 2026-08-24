"""
analysis.py

Contains the core analysis functions for Parts 2 through 4,
plus a main() that runs the full pipeline and saves outputs.
"""

import logging
import os
import sqlite3

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu, false_discovery_control
from sklearn.decomposition import PCA

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = "cell-count.db"
OUTPUT_DIR = "outputs"


def get_summary_table(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Part 2, relative frequency of each cell population per sample.
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
    combinations of both.
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
    Paginated, searchable version of the Part 2 summary table.
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

    Also reports fdr, the Benjamini-Hochberg false discovery rate
    corrected p-value, computed jointly across every population tested
    here. Testing multiple populations inflates the chance that at least
    one looks significant purely by chance, fdr corrects for this.
    significant_fdr uses this corrected value rather than the raw
    p-value, and is the more defensible claim when reporting findings,
    since it accounts for the number of populations tested at once.
    """
    columns = [
        "population", "responder_median_pct", "non_responder_median_pct",
        "p_value", "significant", "effect_size", "auc", "fdr", "significant_fdr",
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

    df = pd.DataFrame(results)

    valid_mask = df["p_value"].notna()
    df["fdr"] = None
    if valid_mask.sum() > 0:
        fdr_values = false_discovery_control(df.loc[valid_mask, "p_value"].values, method="bh")
        df.loc[valid_mask, "fdr"] = fdr_values

    df["significant_fdr"] = df["fdr"].apply(lambda x: bool(x < 0.05) if pd.notna(x) else False)

    return df.sort_values("p_value", na_position="last").reset_index(drop=True)[columns]


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
    """
    query = """
        SELECT
            s.sample_id AS sample,
            sub.subject_id,
            sub.project_id,
            sub.response,
            sub.sex,
            sub.age
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


AGE_GROUP_BINS = [0, 59, 69, 200]
AGE_GROUP_LABELS = ["Under 60", "60-69", "70 and Over"]


def summarize_baseline_subset(baseline_df: pd.DataFrame) -> dict:
    """
    Part 4, breakdowns by project, response, sex, and age group.

    Age group bins, Under 60, 60-69, 70 and Over, were chosen after
    checking the actual age distribution in this dataset, ages range
    50 to 79, these three bins split the cohort roughly evenly rather
    than using generic decade buckets that wouldn't fit this population.
    """
    subjects_df = baseline_df.drop_duplicates("subject_id").copy()
    subjects_df["age_group"] = pd.cut(
        subjects_df["age"], bins=AGE_GROUP_BINS, labels=AGE_GROUP_LABELS
    )

    return {
        "samples_per_project": baseline_df.groupby("project_id")["sample"].nunique(),
        "subjects_by_response": subjects_df["response"].value_counts(),
        "subjects_by_sex": subjects_df["sex"].value_counts(),
        "subjects_by_age_group": subjects_df["age_group"].value_counts().reindex(AGE_GROUP_LABELS),
    }


def get_filter_options(conn: sqlite3.Connection) -> dict:
    """
    Returns the distinct values available for each filterable field.
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


POPULATIONS = ["b_cell", "cd4_t_cell", "cd8_t_cell", "monocyte", "nk_cell"]


def get_sample_pca(
    conn: sqlite3.Connection,
    condition: str = "melanoma",
    treatment: str = "miraclib",
    sample_type: str = "PBMC",
):
    """
    PCA projection of samples based on their five population percentages.

    Since the five percentages always sum to 100, there are only four
    real degrees of freedom here, not five. This is fine for the first
    two components, which is all we use for a 2D scatter, but worth
    knowing, the fifth component will carry essentially zero variance.

    Returns a tuple of three things.
    - a dataframe with sample, subject_id, response, sex, project_id,
      pc1, pc2, one row per sample, this is where each sample sits.
    - a list with the variance explained by pc1 and pc2 respectively.
    - a list of loadings, one entry per population, showing how much
      and in which direction each population contributes to pc1 and
      pc2. This is what the "Key Drivers" style biplot draws as arrows,
      complementary to the sample scatter, not a replacement for it.
    """
    result_cols = ["sample", "subject_id", "response", "sex", "project_id", "pc1", "pc2"]

    query = """
        SELECT
            s.sample_id AS sample,
            sub.subject_id,
            sub.response,
            sub.sex,
            sub.project_id,
            cc.population,
            cc.count
        FROM samples s
        JOIN subjects sub ON s.subject_id = sub.subject_id
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
        WHERE sub.condition = ?
          AND sub.treatment = ?
          AND s.sample_type = ?
    """
    long_df = pd.read_sql_query(query, conn, params=[condition, treatment, sample_type])

    if long_df.empty:
        return pd.DataFrame(columns=result_cols), [], []

    totals = long_df.groupby("sample")["count"].sum().rename("total_count")
    long_df = long_df.merge(totals, on="sample")
    long_df["percentage"] = (long_df["count"] / long_df["total_count"]) * 100

    wide_df = long_df.pivot_table(
        index=["sample", "subject_id", "response", "sex", "project_id"],
        columns="population",
        values="percentage",
    ).reset_index()
    wide_df.columns.name = None

    if len(wide_df) < 2:
        # PCA needs at least 2 samples to define any variance at all
        return pd.DataFrame(columns=result_cols), [], []

    X = wide_df[POPULATIONS].values

    pca = PCA(n_components=2)
    coords = pca.fit_transform(X)
    wide_df["pc1"] = coords[:, 0]
    wide_df["pc2"] = coords[:, 1]

    variance_explained = pca.explained_variance_ratio_.tolist()

    loadings = [
        {
            "population": pop,
            "pc1_loading": float(pca.components_[0][i]),
            "pc2_loading": float(pca.components_[1][i]),
        }
        for i, pop in enumerate(POPULATIONS)
    ]

    return wide_df[result_cols], variance_explained, loadings


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
    print("Part 3, filtered sample count:", comparison_df["sample"].nunique())
    print("Part 3, responder breakdown:")
    print(comparison_df.drop_duplicates("subject_id")["response"].value_counts())

    stats_df = run_statistical_comparison(comparison_df)
    stats_path = os.path.join(OUTPUT_DIR, "statistical_comparison.csv")
    stats_df.to_csv(stats_path, index=False)
    logger.info(f"Part 3, statistical comparison saved to {stats_path}")
    print(stats_df)

    make_boxplots(comparison_df, OUTPUT_DIR)

    baseline_df = get_baseline_subset(conn)
    baseline_path = os.path.join(OUTPUT_DIR, "baseline_subset.csv")
    baseline_df.to_csv(baseline_path, index=False)

    summary = summarize_baseline_subset(baseline_df)
    logger.info(f"Part 4, baseline subset saved to {baseline_path}")
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