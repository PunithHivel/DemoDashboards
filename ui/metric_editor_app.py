from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("METRICS_EDITOR_API_URL", "http://localhost:8000")
CATALOG_ENDPOINT = f"{API_URL}/metrics-editor/catalog"
CURRENT_ENDPOINT = f"{API_URL}/metrics-editor/current"
IMPACT_ENDPOINT = f"{API_URL}/metrics-editor/impact"
APPLY_ENDPOINT = f"{API_URL}/metrics-editor/apply"
HISTORY_ENDPOINT = f"{API_URL}/metrics-editor/history"
REPO_LIST_ENDPOINT = f"{API_URL}/repo/list"
ELIGIBLE_ENDPOINT = f"{API_URL}/metrics-editor/eligible"
ELIGIBLE_SUMMARY_ENDPOINT = f"{API_URL}/metrics-editor/eligible-summary"

st.set_page_config(page_title="Metrics Editor", layout="wide")
st.title("Metrics Editor")


def fetch_catalog() -> Dict[str, Any]:
    try:
        resp = requests.get(CATALOG_ENDPOINT, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        st.error(f"Failed to load catalog: {exc}")
        return {"metrics": []}


def fetch_repos(organization_id: int) -> List[Dict[str, Any]]:
    try:
        resp = requests.get(REPO_LIST_ENDPOINT, params={"organization_id": organization_id}, timeout=10)
        resp.raise_for_status()
        return resp.json().get("repos", [])
    except Exception:
        return []


def fetch_eligible(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = requests.post(ELIGIBLE_ENDPOINT, json=payload, timeout=30)
        if resp.ok:
            return resp.json()
        detail = None
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = None
        st.error(detail or "Eligible lookup failed. Please review filters and try again.")
    except Exception as exc:
        st.error(f"Failed to load eligible scopes: {exc}")
    return {"repos": [], "teams": [], "authors": []}


def fetch_eligible_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = requests.post(ELIGIBLE_SUMMARY_ENDPOINT, json=payload, timeout=30)
        if resp.ok:
            return resp.json()
        detail = None
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = None
        st.error(detail or "Eligible summary lookup failed.")
    except Exception as exc:
        st.error(f"Failed to load eligible summary: {exc}")
    return {"by_period": []}


def show_api_error(resp: requests.Response) -> None:
    detail = None
    try:
        detail = resp.json().get("detail")
    except Exception:
        detail = None
    st.error(detail or "Request failed. Please review inputs and try again.")


def format_metric_snapshot(snapshot: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for point in snapshot.get("by_period", []):
        rows.append({"Period": point["period"], "Value": point["value"]})
    return pd.DataFrame(rows)


def summarize_impact(impact: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for entry in impact.get("affected", []):
        before = entry["before"]["total_value"]
        after = entry["after"]["total_value"]
        rows.append(
            {
                "Metric": entry["label"],
                "Before": round(before, 2),
                "After": round(after, 2),
                "Delta": round(after - before, 2),
            }
        )
    return pd.DataFrame(rows)


catalog = fetch_catalog()
metrics = catalog.get("metrics", [])
metric_labels = {m["label"]: m for m in metrics}
metric_by_id = {m["id"]: m for m in metrics}

if "stage" not in st.session_state:
    st.session_state["stage"] = "filters"

if not metric_labels:
    st.warning("No metrics available. Please check the API connection.")
    st.stop()

with st.sidebar:
    st.header("Step 1: Filters")
    org_id = st.number_input("Organization ID", min_value=1, value=2159, step=1)
    start_date = st.date_input("Start date", value=date(2025, 10, 1))
    end_date = st.date_input("End date", value=date(2026, 1, 1))
    metric_label = st.selectbox("Metric", options=list(metric_labels.keys()))
    selected_metric = metric_labels[metric_label]
    action = st.selectbox("Action", options=selected_metric.get("actions") or ["read_only"])
    scope_type = st.selectbox("Scope type", options=["Organization", "Team", "Author"])
    repo_filter = st.selectbox(
        "Repo filter",
        options=[{"id": None, "label": "All repos"}] + fetch_repos(org_id),
        format_func=lambda item: item.get("label")
        or f"{item.get('id')} - {item.get('name') or item.get('slug') or ''}".strip(),
    )

    if st.button("Load eligible scopes"):
        eligible_payload = {
            "metric_id": selected_metric["id"],
            "action": action,
            "organization_id": org_id,
            "repo_id": repo_filter["id"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        st.session_state["eligible"] = fetch_eligible(eligible_payload)
        st.session_state["filters"] = eligible_payload
        st.session_state["scope_type"] = scope_type
        st.session_state["team_filter"] = None
        st.session_state["author_filter"] = None

    if "eligible" in st.session_state and st.session_state.get("stage") == "filters":
        eligible = st.session_state.get("eligible", {})
        team_options = [{"id": None, "label": "All teams"}] + eligible.get("teams", [])
        team_ids = [team["id"] for team in team_options]
        current_team = st.session_state.get("team_filter")
        team_index = team_ids.index(current_team) if current_team in team_ids else 0
        team_filter_selection = st.selectbox(
            "Team filter (optional)",
            options=team_options,
            index=team_index,
            key="team_filter_select",
            format_func=lambda item: item.get("label") or f"{item.get('id')} ({item.get('count', 0)})",
        )
        if team_filter_selection.get("id") != st.session_state.get("team_filter"):
            st.session_state["team_filter"] = team_filter_selection.get("id")
            filters = st.session_state["filters"]
            if team_filter_selection.get("id") is None:
                filters.pop("team_id", None)
            else:
                filters["team_id"] = team_filter_selection.get("id")
            refreshed = fetch_eligible(filters)
            st.session_state["eligible"] = refreshed
            eligible = refreshed

        if scope_type == "Author":
            author_options = [{"id": None, "label": "Select author"}] + eligible.get("authors", [])
            author_ids = [author["id"] for author in author_options]
            current_author = st.session_state.get("author_filter")
            author_index = author_ids.index(current_author) if current_author in author_ids else 0
            author_selection = st.selectbox(
                "Author",
                options=author_options,
                index=author_index,
                key="author_filter_select",
                format_func=lambda item: item.get("label") or f"{item.get('id')} ({item.get('count', 0)})",
            )
            selected_author_id = author_selection.get("id")
            if selected_author_id != st.session_state.get("author_filter"):
                st.session_state["author_filter"] = selected_author_id
                filters = st.session_state["filters"]
                if selected_author_id is None:
                    filters.pop("author_ids", None)
                else:
                    filters["author_ids"] = [selected_author_id]
                refreshed = fetch_eligible(filters)
                st.session_state["eligible"] = refreshed
                eligible = refreshed
        if scope_type == "Team":
            if team_filter_selection.get("id") is None:
                st.warning("Select a team to continue for Team scope.")

        if st.button("Continue to editor"):
            filters = st.session_state["filters"]
            filters["team_id"] = st.session_state.get("team_filter")
            if st.session_state.get("author_filter") is not None:
                filters["author_ids"] = [st.session_state["author_filter"]]
            st.session_state["filters"] = filters
            st.session_state["stage"] = "editor"

if st.session_state["stage"] == "filters":
    st.info("Select filters and click **Load eligible scopes** to continue.")
    st.stop()

eligible = st.session_state.get("eligible", {})
filters = st.session_state.get("filters", {})
scope_type = st.session_state.get("scope_type", "Organization")
team_id = st.session_state.get("team_filter")
author_ids = filters.get("author_ids")

st.subheader("Step 2: Eligible data")
if st.button("Change filters"):
    st.session_state["stage"] = "filters"
    st.stop()

if scope_type == "Team" and team_id is None:
    st.warning("Team scope selected but no team chosen in Step 1.")
if scope_type == "Author" and not author_ids:
    st.warning("Author scope selected but no author chosen in Step 1.")

st.caption(
    f"Metric: {selected_metric['label']} | Action: {action} | Scope: {scope_type} | "
    f"Date range: {filters['start_date']} → {filters['end_date']}"
)

with st.expander("Eligible coverage"):
    st.write(
        f"Repos: {len(eligible.get('repos', []))} | "
        f"Teams: {len(eligible.get('teams', []))} | "
        f"Authors: {len(eligible.get('authors', []))}"
    )
    if eligible.get("repos"):
        st.dataframe(pd.DataFrame(eligible["repos"]), width="stretch")
    if eligible.get("teams"):
        if team_id is not None:
            st.dataframe(pd.DataFrame([t for t in eligible["teams"] if t.get("id") == team_id]), width="stretch")
        else:
            st.dataframe(pd.DataFrame(eligible["teams"]), width="stretch")
    if eligible.get("authors"):
        if author_ids:
            st.dataframe(
                pd.DataFrame([a for a in eligible["authors"] if a.get("id") in author_ids]), width="stretch"
            )
        else:
            st.dataframe(pd.DataFrame(eligible["authors"]), width="stretch")

team_id: Optional[int] = filters.get("team_id")
author_ids: Optional[List[int]] = filters.get("author_ids")

affected_metric_ids = selected_metric.get("affects", [])
affected_labels = [metric_by_id[mid]["label"] for mid in affected_metric_ids if mid in metric_by_id]
if affected_metric_ids:
    affected_rows = []
    for metric_id in affected_metric_ids:
        metric_info = metric_by_id.get(metric_id, {})
        affected_rows.append(
            {
                "Metric": metric_info.get("label", metric_id),
                "Source": metric_info.get("source", "Unknown"),
            }
        )
    st.subheader("Affected metrics")
    st.dataframe(pd.DataFrame(affected_rows), use_container_width=True)
else:
    st.subheader("Affected metrics")
    st.caption("No downstream metrics are marked as affected for this change.")

st.subheader("Step 3: Change request")
options: Dict[str, Any] = {}
show_summary = False
if action in {"shift_open_prs", "shift_merged_prs", "shift_commit_dates"}:
    options["source_month"] = st.text_input("Source month (YYYY-MM)")
    options["target_month"] = st.text_input("Target month (YYYY-MM)")
    options["count"] = st.number_input("Count", min_value=1, value=10, step=1)
    show_summary = True
elif action in {"set_reviewed_count", "set_unreviewed_count"}:
    options["month"] = st.text_input("Month (YYYY-MM)")
    options["count"] = st.number_input("Count", min_value=1, value=10, step=1)
    options["review_minutes"] = st.number_input("Review minutes", min_value=1, value=180, step=10)
    show_summary = True
elif action == "set_flashy_reviews":
    options["month"] = st.text_input("Month (YYYY-MM)")
    options["count"] = st.number_input("Count", min_value=1, value=10, step=1)
    options["flashy"] = st.checkbox("Mark as flashy", value=True)
    options["flashy_minutes"] = st.number_input("Flashy minutes (<)", min_value=1, value=5, step=1)
    options["size_threshold"] = st.number_input("Large PR threshold (lines)", min_value=1, value=400, step=10)
    options["regular_minutes"] = st.number_input("Regular minutes", min_value=1, value=180, step=10)
    show_summary = True
elif action in {"toggle_release_prs", "toggle_hotfix_prs"}:
    options["month"] = st.text_input("Month (YYYY-MM)")
    options["count"] = st.number_input("Count", min_value=1, value=5, step=1)
    options["value"] = st.checkbox("Set to TRUE", value=True)
    show_summary = True
elif action == "set_large_prs":
    options["month"] = st.text_input("Month (YYYY-MM)")
    options["count"] = st.number_input("Count", min_value=1, value=10, step=1)
    options["large"] = st.checkbox("Make large", value=True)
    options["threshold_lines"] = st.number_input("Large threshold (lines)", min_value=1, value=400, step=10)
    options["target_lines"] = st.number_input("Target total lines", min_value=1, value=500, step=10)
    options["added_ratio"] = st.number_input("Added ratio (0-1)", min_value=0.0, max_value=1.0, value=0.6, step=0.05)
    show_summary = True
elif action in {"scale_review_time", "scale_cycle_time", "scale_deploy_time", "scale_coding_time", "scale_mttr_duration"}:
    options["month"] = st.text_input("Month (YYYY-MM)")
    options["scale"] = st.number_input("Scale", min_value=0.1, value=1.2, step=0.1)
    show_summary = True
elif action == "set_commit_mix":
    options["month"] = st.text_input("Month (YYYY-MM)")
    options["newwork_pct"] = st.number_input("New work %", min_value=0.0, max_value=100.0, value=70.0, step=1.0)
    options["rework_pct"] = st.number_input("Rework %", min_value=0.0, max_value=100.0, value=15.0, step=1.0)
    options["maintenance_pct"] = st.number_input("Maintenance %", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
    options["assistance_pct"] = st.number_input("Assistance %", min_value=0.0, max_value=100.0, value=5.0, step=1.0)
    show_summary = True

scope_payload = {
    "organization_id": filters["organization_id"],
    "repo_id": filters.get("repo_id"),
    "team_id": team_id,
    "author_ids": author_ids,
    "start_date": filters["start_date"],
    "end_date": filters["end_date"],
}

if show_summary:
    summary_payload = {
        "metric_id": selected_metric["id"],
        "action": action,
        "scope": scope_payload,
        "options": options,
    }
    summary = fetch_eligible_summary(summary_payload)
    if summary.get("by_period"):
        st.subheader("Eligible counts by month")
        st.dataframe(pd.DataFrame(summary["by_period"]), use_container_width=True)
    else:
        st.info("No eligible records found for the selected filters.")

col1, col2 = st.columns(2)
with col1:
    if st.button("Preview impact"):
        if scope_type == "Team" and team_id is None:
            st.error("Please select a team in Step 1 filters.")
        elif scope_type == "Author" and not author_ids:
            st.error("Please select an author in Step 1 filters.")
        else:
            request_payload = {
                "metric_id": selected_metric["id"],
                "action": action,
                "scope": scope_payload,
                "options": options,
            }
            if action != "read_only":
                resp = requests.post(IMPACT_ENDPOINT, json=request_payload, timeout=60)
                if resp.ok:
                    st.session_state["impact"] = resp.json()
                else:
                    show_api_error(resp)

with col2:
    if st.button("Apply change"):
        if scope_type == "Team" and team_id is None:
            st.error("Please select a team in Step 1 filters.")
        elif scope_type == "Author" and not author_ids:
            st.error("Please select an author in Step 1 filters.")
        else:
            request_payload = {
                "metric_id": selected_metric["id"],
                "action": action,
                "scope": scope_payload,
                "options": options,
            }
            if action != "read_only":
                resp = requests.post(APPLY_ENDPOINT, json=request_payload, timeout=60)
                if resp.ok:
                    st.session_state["apply"] = resp.json()
                else:
                    show_api_error(resp)

st.subheader("Current snapshot")
current_payload = {"metric_id": selected_metric["id"], "scope": scope_payload}
current_resp = requests.post(CURRENT_ENDPOINT, json=current_payload, timeout=30)
if current_resp.ok:
    snapshot = current_resp.json()
    snapshot_df = format_metric_snapshot(snapshot)
    st.dataframe(snapshot_df, use_container_width=True)
else:
    show_api_error(current_resp)

if "impact" in st.session_state:
    st.subheader("Impact summary")
    impact = st.session_state["impact"]
    st.dataframe(summarize_impact(impact), use_container_width=True)
    for entry in impact.get("affected", []):
        with st.expander(f"Period details: {entry['label']}"):
            before_df = format_metric_snapshot(entry["before"])
            after_df = format_metric_snapshot(entry["after"])
            merged = before_df.merge(after_df, on="Period", how="outer", suffixes=("_before", "_after"))
            merged["Delta"] = merged["Value_after"].fillna(0) - merged["Value_before"].fillna(0)
            st.dataframe(merged, use_container_width=True)
    with st.expander("SQL plan"):
        for stmt, params in zip(impact["plan"]["sql_statements"], impact["plan"]["sql_params"]):
            st.code(stmt, language="sql")
            st.caption(f"Params: {params}")

if "apply" in st.session_state:
    st.subheader("Apply result")
    st.json(st.session_state["apply"])

st.subheader("History")
if st.button("Refresh history"):
    history_resp = requests.get(HISTORY_ENDPOINT)
    if history_resp.ok:
        st.json(history_resp.json())
    else:
        st.error(history_resp.text)
