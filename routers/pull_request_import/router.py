from __future__ import annotations

import io
from typing import Dict, List, Tuple

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.pull_request_repository import PullRequestRepository

router = APIRouter(prefix="/pull-request-import", tags=["pull-request-import"])

EXPECTED_COLUMNS = [
    "id",
    "actualpullrequestid",
    "title",
    "authorid",
    "createdon",
    "description",
    "destinationbranch",
    "sourcebranch",
    "firstcommitid",
    "sourcecommitid",
    "destinationcommitid",
    "state",
    "repoid",
    "linesadded",
    "linesremoved",
    "htmllink",
    "commentcount",
    "commitscount",
    "modifiedfilescount",
    "updatedon",
    "mergecommit",
    "mergedby",
    "approvedby",
    "mergedon",
    "declinedon",
    "approvedon",
    "firstcommittedon",
    "committoopenduration",
    "opentoreviewduration",
    "reviewedtoapprovedduration",
    "reviewedtomergedduration",
    "approvedtomergedduration",
    "reviewedtodeclineduration",
    "opentodeclineduration",
    "opentomergedduration",
    "cycletimeduration",
    "deploytimeduration",
    "cycletimeoverflow",
    "declinedby",
    "remark",
    "originalauthorid",
    "originalapprovedby",
    "originalfirstreviewedby",
    "originaldeclinedby",
    "processed",
    "hotfixpr",
    "reviewbranchpr",
    "releasebranchpr",
    "excludepr",
    "flashyreviewedpr",
    "organizationid",
    "workspaceid",
    "userintegrationid",
    "reviewcyclecount",
    "opentofirstcommentduration",
    "firstcommenttoapproved",
]

REQUIRED_COLUMNS = {
    "id",
    "actualpullrequestid",
    "authorid",
    "createdon",
    "repoid",
    "organizationid",
    "workspaceid",
}

TIMESTAMP_COLUMNS = {
    "createdon",
    "updatedon",
    "mergedon",
    "declinedon",
    "approvedon",
    "firstcommittedon",
}

FLOAT_COLUMNS = {
    "committoopenduration",
    "opentoreviewduration",
    "reviewedtoapprovedduration",
    "reviewedtomergedduration",
    "approvedtomergedduration",
    "reviewedtodeclineduration",
    "opentodeclineduration",
    "opentomergedduration",
    "cycletimeduration",
    "deploytimeduration",
    "opentofirstcommentduration",
    "firstcommenttoapproved",
}

INT_COLUMNS = {
    "id",
    "actualpullrequestid",
    "authorid",
    "repoid",
    "linesadded",
    "linesremoved",
    "commentcount",
    "commitscount",
    "modifiedfilescount",
    "mergedby",
    "approvedby",
    "declinedby",
    "originalauthorid",
    "originalapprovedby",
    "originalfirstreviewedby",
    "originaldeclinedby",
    "organizationid",
    "workspaceid",
    "userintegrationid",
    "reviewcyclecount",
}

BOOL_COLUMNS = {
    "cycletimeoverflow",
    "processed",
    "hotfixpr",
    "reviewbranchpr",
    "releasebranchpr",
    "excludepr",
    "flashyreviewedpr",
}

_repository = PullRequestRepository()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    alias_map = {
        "firstcommenttoapprovedduration": "firstcommenttoapproved",
        "html_link": "htmllink",
    }

    normalized = {}
    for original in df.columns:
        key = original.strip().lower().replace(" ", "").replace("-", "")
        replacement = alias_map.get(key, key)
        normalized[original] = replacement

    return df.rename(columns=normalized)


def _to_datetime(value):
    if pd.isna(value):
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        return pd.to_datetime(text_value).to_pydatetime()
    except Exception:
        return None


def _to_int(value):
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value):
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value):
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    text_value = str(value).strip().lower()
    if not text_value:
        return None
    return text_value in {"1", "true", "yes", "y"}


def _clean_string(value):
    if pd.isna(value):
        return None
    text_value = str(value).strip()
    return text_value or None


def _prepare_payloads(df: pd.DataFrame) -> Tuple[List[Dict], int]:
    df = _normalize_columns(df)

    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV missing expected columns: {', '.join(missing)}",
        )

    if any(col not in df.columns for col in REQUIRED_COLUMNS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV missing required pull request identifiers.",
        )

    filtered = df.drop_duplicates(subset=["id"]).dropna(subset=list(REQUIRED_COLUMNS))

    payloads: List[Dict] = []
    conversion_errors = 0

    for row in filtered.itertuples(index=False):
        try:
            payload = {}
            for column in EXPECTED_COLUMNS:
                value = getattr(row, column)
                if column in TIMESTAMP_COLUMNS:
                    payload[column] = _to_datetime(value)
                elif column in INT_COLUMNS:
                    payload[column] = _to_int(value)
                elif column in FLOAT_COLUMNS:
                    payload[column] = _to_float(value)
                elif column in BOOL_COLUMNS:
                    payload[column] = _to_bool(value)
                else:
                    payload[column] = _clean_string(value)

            payloads.append(payload)
        except Exception:
            conversion_errors += 1
            continue

    return payloads, conversion_errors


@router.post(
    "/csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import pull requests from a CSV file",
)
async def import_pull_requests(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV uploads are supported.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded.",
        )

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to parse CSV: {exc}",
        ) from exc

    payloads, conversion_errors = _prepare_payloads(df)
    if not payloads:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid pull request rows found in CSV.",
        )

    inserted = _repository.bulk_upsert(session, payloads)

    return {
        "rows_received": len(df),
        "rows_inserted": inserted,
        "rows_skipped": conversion_errors + (len(df) - len(payloads)),
    }
