from __future__ import annotations

import io

import pandas as pd
from fastapi import HTTPException, UploadFile, status


async def read_uploaded_csv(file: UploadFile) -> pd.DataFrame:
    """
    Validates an uploaded file and returns its contents as a DataFrame.
    """
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
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
        return pd.read_csv(io.BytesIO(contents))
    except Exception as exc:  # pragma: no cover - pandas error surface
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to parse CSV: {exc}",
        ) from exc
