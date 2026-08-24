"""
tests/test_analysis.py

Unit tests for the core analysis functions in analysis.py.

Uses a small, hand built in-memory database rather than the real
cell-count.db, so tests are fast, deterministic, and check exact
known scenarios rather than whatever happens to be true about the
real dataset at any given time.
"""

import sqlite3

import pandas as pd
import pytest

from load_data import SCHEMA
from analysis import (
    get_summary_table,
    get_responder_comparison_data,
    run_statistical_comparison,
    get_baseline_subset,
    summarize_baseline_subset,
    get_filter_options,
    _parse_sample_search,
)


@pytest.fixture
def conn():
    """
    An in-memory SQLite database with a small, known set of fixture data.

    3 subjects, melanoma, miraclib, PBMC (2 responders, 1 non-responder)
    1 subject, healthy, no treatment (response is null, by design)
    """
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA)

    connection.executemany(
        "INSERT INTO projects (project_id) VALUES (?)",
        [("prj1",), ("prj2",)],
    )

    connection.executemany(
        """INSERT INTO subjects
           (subject_id, project_id, condition, age, sex, treatment, response)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            ("sbj000", "prj1", "melanoma", 45, "F", "miraclib", "yes"),
            ("sbj001", "prj1", "melanoma", 50, "M", "miraclib", "yes"),
            ("sbj002", "prj2", "melanoma", 60, "F", "miraclib", "no"),
            ("sbj003", "prj2", "healthy", 30, "M", "none", None),
        ],
    )

    connection.executemany(
        """INSERT INTO samples
           (sample_id, subject_id, sample_type, time_from_treatment_start)
           VALUES (?, ?, ?, ?)""",
        [
            ("sampleA", "sbj000", "PBMC", 0),
            ("sampleB", "sbj001", "PBMC", 0),
            ("sampleC", "sbj002", "PBMC", 0),
            ("sampleD", "sbj003", "PBMC", 0),
        ],
    )

    fixed_counts = {
        "sampleA": [100, 200, 300, 250, 150],
        "sampleB": [120, 180, 280, 220, 200],
        "sampleC": [90, 210, 310, 240, 150],
        "sampleD": [80, 190, 290, 260, 180],
    }
    populations = ["b_cell", "cd4_t_cell", "cd8_t_cell", "monocyte", "nk_cell"]

    rows = []
    for sample_id, counts in fixed_counts.items():
        for population, count in zip(populations, counts):
            rows.append((sample_id, population, count))

    connection.executemany(
        "INSERT INTO cell_counts (sample_id, population, count) VALUES (?, ?, ?)",
        rows,
    )
    connection.commit()

    yield connection
    connection.close()


# ---------------------------------------------------------------------
# Part 2, get_summary_table
# ---------------------------------------------------------------------

def test_summary_table_has_expected_columns(conn):
    df = get_summary_table(conn)
    assert list(df.columns) == ["sample", "total_count", "population", "count", "percentage"]


def test_summary_table_percentages_sum_to_100_per_sample(conn):
    df = get_summary_table(conn)
    totals = df.groupby("sample")["percentage"].sum()
    assert (totals.round(5) == 100.0).all()


def test_summary_table_row_count_matches_samples_times_populations(conn):
    df = get_summary_table(conn)
    # 4 samples x 5 populations
    assert len(df) == 20


# ---------------------------------------------------------------------
# Part 3, get_responder_comparison_data and run_statistical_comparison
# ---------------------------------------------------------------------

def test_responder_comparison_filters_to_matching_subset(conn):
    df = get_responder_comparison_data(conn, condition="melanoma", treatment="miraclib", sample_type="PBMC")
    # only sampleA, sampleB, sampleC match melanoma + miraclib + PBMC
    assert set(df["sample"].unique()) == {"sampleA", "sampleB", "sampleC"}
    # sampleD (healthy, no treatment) must not appear
    assert "sampleD" not in df["sample"].unique()


def test_responder_comparison_excludes_unmatched_condition(conn):
    df = get_responder_comparison_data(conn, condition="carcinoma", treatment="miraclib", sample_type="PBMC")
    assert df.empty


def test_statistical_comparison_returns_one_row_per_population(conn):
    comparison_df = get_responder_comparison_data(conn, "melanoma", "miraclib", "PBMC")
    stats_df = run_statistical_comparison(comparison_df)
    assert len(stats_df) == 5
    assert set(stats_df["population"]) == {"b_cell", "cd4_t_cell", "cd8_t_cell", "monocyte", "nk_cell"}


def test_statistical_comparison_has_expected_columns(conn):
    comparison_df = get_responder_comparison_data(conn, "melanoma", "miraclib", "PBMC")
    stats_df = run_statistical_comparison(comparison_df)
    expected_cols = [
        "population", "responder_median_pct", "non_responder_median_pct",
        "p_value", "significant", "effect_size", "auc", "fdr", "significant_fdr",
    ]
    assert list(stats_df.columns) == expected_cols


def test_statistical_comparison_handles_completely_empty_input():
    empty_df = pd.DataFrame(columns=["sample", "subject_id", "response", "population", "count", "total_count", "percentage"])
    stats_df = run_statistical_comparison(empty_df)
    assert stats_df.empty
    expected_cols = [
        "population", "responder_median_pct", "non_responder_median_pct",
        "p_value", "significant", "effect_size", "auc", "fdr", "significant_fdr",
    ]
    assert list(stats_df.columns) == expected_cols


def test_statistical_comparison_handles_missing_group(conn):
    """
    If every sample in the filtered set is a responder (or non-responder),
    the function should not crash, and should return null p-values and
    null effect sizes instead.
    """
    comparison_df = get_responder_comparison_data(conn, "melanoma", "miraclib", "PBMC")
    responders_only = comparison_df[comparison_df["response"] == "yes"]

    stats_df = run_statistical_comparison(responders_only)
    assert len(stats_df) == 5
    assert stats_df["p_value"].isnull().all()
    assert stats_df["effect_size"].isnull().all()
    assert stats_df["auc"].isnull().all()
    assert (stats_df["significant"] == False).all()


def test_effect_size_and_auc_known_values(conn):
    """
    Hand-computed against the fixture data. Percentages work out to:
    b_cell:     responders [10, 12], non-responder [9]  -> both responders higher
    cd4_t_cell: responders [20, 18], non-responder [21] -> both responders lower

    For b_cell, both responder values exceed the single non-responder value,
    so this population perfectly separates the two groups in this direction,
    auc should be 1.0 and effect_size should be 1.0.

    For cd4_t_cell, both responder values are below the non-responder value,
    the perfect separation the other direction, auc should be 0.0 and
    effect_size should be -1.0.
    """
    comparison_df = get_responder_comparison_data(conn, "melanoma", "miraclib", "PBMC")
    stats_df = run_statistical_comparison(comparison_df)

    b_cell_row = stats_df[stats_df["population"] == "b_cell"].iloc[0]
    assert b_cell_row["auc"] == pytest.approx(1.0)
    assert b_cell_row["effect_size"] == pytest.approx(1.0)

    cd4_row = stats_df[stats_df["population"] == "cd4_t_cell"].iloc[0]
    assert cd4_row["auc"] == pytest.approx(0.0)
    assert cd4_row["effect_size"] == pytest.approx(-1.0)


def test_effect_size_matches_auc_relationship(conn):
    """
    effect_size and auc are two views of the same underlying statistic,
    effect_size should always equal (2 * auc) - 1.
    """
    comparison_df = get_responder_comparison_data(conn, "melanoma", "miraclib", "PBMC")
    stats_df = run_statistical_comparison(comparison_df)

    for _, row in stats_df.iterrows():
        assert row["effect_size"] == pytest.approx((2 * row["auc"]) - 1)


def test_auc_and_effect_size_within_valid_ranges(conn):
    comparison_df = get_responder_comparison_data(conn, "melanoma", "miraclib", "PBMC")
    stats_df = run_statistical_comparison(comparison_df)

    assert (stats_df["auc"] >= 0).all()
    assert (stats_df["auc"] <= 1).all()
    assert (stats_df["effect_size"] >= -1).all()
    assert (stats_df["effect_size"] <= 1).all()


def test_fdr_correction_is_never_smaller_than_raw_pvalue(conn):
    """
    Benjamini-Hochberg correction only ever inflates or preserves a
    p-value, it should never make a result look more significant than
    the raw test did.
    """
    comparison_df = get_responder_comparison_data(conn, "melanoma", "miraclib", "PBMC")
    stats_df = run_statistical_comparison(comparison_df)

    for _, row in stats_df.iterrows():
        assert row["fdr"] >= row["p_value"] - 1e-9


def test_fdr_correction_handles_single_population():
    """
    With only one population tested, FDR correction has nothing to
    correct against, the adjusted value should equal the raw p-value.
    """
    df = pd.DataFrame({
        "sample": ["s1", "s2", "s3", "s4"],
        "subject_id": ["sub1", "sub2", "sub3", "sub4"],
        "response": ["yes", "yes", "no", "no"],
        "population": ["b_cell"] * 4,
        "count": [10, 12, 9, 8],
        "total_count": [100, 100, 100, 100],
        "percentage": [10, 12, 9, 8],
    })
    stats_df = run_statistical_comparison(df)
    assert len(stats_df) == 1
    assert stats_df.iloc[0]["fdr"] == pytest.approx(stats_df.iloc[0]["p_value"])


# ---------------------------------------------------------------------
# Part 4, get_baseline_subset and summarize_baseline_subset
# ---------------------------------------------------------------------

def test_baseline_subset_matches_expected_subjects(conn):
    df = get_baseline_subset(conn, "melanoma", "miraclib", "PBMC", 0)
    assert len(df) == 3
    assert set(df["subject_id"]) == {"sbj000", "sbj001", "sbj002"}


def test_baseline_subset_empty_for_unmatched_timepoint(conn):
    df = get_baseline_subset(conn, "melanoma", "miraclib", "PBMC", 7)
    assert df.empty


def test_summarize_baseline_subset_breakdowns(conn):
    baseline_df = get_baseline_subset(conn, "melanoma", "miraclib", "PBMC", 0)
    summary = summarize_baseline_subset(baseline_df)

    assert summary["subjects_by_response"]["yes"] == 2
    assert summary["subjects_by_response"]["no"] == 1
    assert summary["samples_per_project"]["prj1"] == 2
    assert summary["samples_per_project"]["prj2"] == 1


# ---------------------------------------------------------------------
# get_filter_options
# ---------------------------------------------------------------------

def test_filter_options_returns_distinct_values(conn):
    options = get_filter_options(conn)
    assert set(options["conditions"]) == {"melanoma", "healthy"}
    assert set(options["treatments"]) == {"miraclib", "none"}
    assert set(options["sample_types"]) == {"PBMC"}
    assert set(options["timepoints"]) == {0}


# ---------------------------------------------------------------------
# _parse_sample_search
# ---------------------------------------------------------------------

def test_parse_sample_search_empty_matches_everything():
    where_clause, params = _parse_sample_search("")
    assert where_clause == "1=1"
    assert params == []


def test_parse_sample_search_single_term_is_substring_match():
    where_clause, params = _parse_sample_search("sample00001")
    assert "LIKE" in where_clause
    assert params == ["%sample00001%"]


def test_parse_sample_search_comma_separated_list():
    where_clause, params = _parse_sample_search("sample00001,sample00005")
    assert where_clause.count("LIKE") == 2
    assert params == ["%sample00001%", "%sample00005%"]


def test_parse_sample_search_range_uses_between():
    where_clause, params = _parse_sample_search("sample00001:sample00010")
    assert "BETWEEN" in where_clause
    assert params == ["sample00001", "sample00010"]


def test_parse_sample_search_reversed_range_is_auto_corrected():
    _, params = _parse_sample_search("sample00010:sample00001")
    assert params == ["sample00001", "sample00010"]


def test_parse_sample_search_combination_of_range_and_terms():
    where_clause, params = _parse_sample_search("sample00001:sample00003,sample00050")
    assert "BETWEEN" in where_clause
    assert "LIKE" in where_clause
    assert params == ["sample00001", "sample00003", "%sample00050%"]