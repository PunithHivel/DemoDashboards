from __future__ import annotations

import io
import json
from typing import Dict, List, Tuple

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.author_repository import AuthorRepository

router = APIRouter(prefix="/author-import", tags=["author-import"])
ORG_ID = 2159
CSV_TO_DB_FIELDS = {
    "unique_ic": "accountid",
    "name": "name",
    "email": "email",
    "labels": "labels",
    "username": "username",
    "login_via": "type",
    "user_role": "access_status",
    "teams": "sharedteams",
    "scm_provider": "scmprovider",
    "id": "id",
}
REQUIRED_NON_NULL = {"id", "scm_provider", "name", "username", "login_via"}
_repository = AuthorRepository()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Accepts user CSVs that may contain different casing or spacing for headers.
    Normalizes everything to lowercase snake_case and applies known aliases.
    """
    alias_map = {
        "unique_id": "unique_ic",
        "scmprovider": "scm_provider",
    }

    normalized = {}
    for original in df.columns:
        key = original.strip().lower().replace(" ", "_")
        target = alias_map.get(key, key)
        normalized[original] = target

    return df.rename(columns=normalized)


def _normalize_labels(raw_value) -> str:
    """
    Returns a JSON string only when the CSV already supplies structured labels.
    If the CSV contains a plain string (e.g., comma separated values), we skip
    storing it because labels are expected to reference lookup IDs.
    """
    if pd.isna(raw_value):
        return json.dumps({})

    raw_str = str(raw_value).strip()
    if not raw_str:
        return json.dumps({})

    try:
        parsed = json.loads(raw_str)
    except json.JSONDecodeError:
        return json.dumps({})

    if isinstance(parsed, (dict, list)):
        return json.dumps(parsed)

    return json.dumps({})


def _normalize_shared_teams(raw_value) -> str | None:
    """
    Shared teams in the author table store team identifiers, not display names.
    We therefore only accept JSON lists (e.g., [1, 2]) from the CSV; otherwise
    we return None to avoid saving misleading text.
    """
    if pd.isna(raw_value):
        return None

    raw_str = str(raw_value).strip()
    if not raw_str:
        return None

    try:
        parsed = json.loads(raw_str)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, list):
        return json.dumps(parsed)

    return None


def _prepare_author_payloads(
    df: pd.DataFrame,
) -> Tuple[List[Dict], int, int]:
    df = _normalize_columns(df)
    missing_columns = [col for col in CSV_TO_DB_FIELDS if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV missing required columns: {', '.join(missing_columns)}",
        )

    initial_count = len(df)
    filtered_df = df[list(CSV_TO_DB_FIELDS.keys())].copy()
    filtered_df = filtered_df.drop_duplicates(subset=["id"])
    filtered_df = filtered_df.dropna(subset=list(REQUIRED_NON_NULL))
    filtered_count = len(filtered_df)

    payloads: List[Dict] = []
    conversion_errors = 0
    for row in filtered_df.itertuples(index=False):
        try:
            user_role_value = None if pd.isna(row.user_role) else str(row.user_role).strip()
            account_id = None
            if not pd.isna(row.unique_ic):
                account_candidate = str(row.unique_ic).strip()
                if account_candidate:
                    try:
                        if int(float(account_candidate)) == int(row.id):
                            account_candidate = ""
                    except (ValueError, TypeError):
                        pass

                account_id = account_candidate or None

            author_payload = {
                "id": int(row.id),
                "organizationid": ORG_ID,
                "accountid": account_id,
                "name": str(row.name).strip(),
                "email": None if pd.isna(row.email) else str(row.email).strip(),
                "labels": _normalize_labels(row.labels),
                "username": str(row.username).strip(),
                "login_via": str(row.login_via).strip(),
                "access_status": user_role_value,
                "sharedteams": _normalize_shared_teams(row.teams),
                "scmprovider": str(row.scm_provider).strip(),
                "active": True,
            }
        except (TypeError, ValueError):
            conversion_errors += 1
            continue

        payloads.append(author_payload)

    dropped_rows = initial_count - filtered_count
    return payloads, dropped_rows, conversion_errors


@router.post(
    "/csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import authors for a fixed organization from a CSV file",
)
async def import_authors_from_csv(
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
    except Exception as exc:  # pragma: no cover - pandas error surface
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to parse CSV: {exc}",
        ) from exc

    author_payloads, dropped_prior, conversion_errors = _prepare_author_payloads(df)
    if not author_payloads:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid rows found in CSV.",
        )

    inserted = _repository.bulk_upsert(session, author_payloads)

    return {
        "rows_received": len(df),
        "rows_inserted": inserted,
        "rows_skipped": dropped_prior + conversion_errors,
        "organization_id": ORG_ID,
    }
