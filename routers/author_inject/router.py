from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse
import pandas as pd

from db.session import SessionLocal
from repositories.author_inject_repository import AuthorInjectRepository
from schemas.author_inject import AuthorInjectRequest
from utils.csv_loader import read_uploaded_csv


# Async generator wrapper to ensure chunks are sent immediately
async def stream_with_flush(generator):
    """Wrapper to ensure streaming response chunks are flushed immediately"""
    async for chunk in generator:
        yield chunk

router = APIRouter(prefix="/author-inject", tags=["author-inject"])
_repository = AuthorInjectRepository()


def _normalize_csv_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize CSV column names to match our expected format"""
    normalized = {}
    for original in df.columns:
        key = original.strip().lower().replace(" ", "_").replace("-", "_")
        normalized[original] = key
    return df.rename(columns=normalized)


@router.post(
    "/csv/upload/stream",
    summary="Inject author data from CSV file with real-time JSON streaming",
)
async def inject_authors_from_csv_stream(
    organization_id: int = Form(..., description="Organization ID"),
    file: UploadFile = File(..., description="CSV file with author data"),
    limit: Optional[int] = Form(None, description="Limit number of rows to process"),
) -> StreamingResponse:
    """
    Inject author data from CSV file with real-time JSON streaming (NDJSON format).
    Each line is a separate JSON object that Postman can parse.
    """
    
    async def data_generator():
        session = SessionLocal()
        try:
            # Read CSV
            df = await read_uploaded_csv(file)
            df = _normalize_csv_columns(df)
            
            # Parse authors
            authors = []
            for idx, row in df.iterrows():
                try:
                    name = str(row.get("name")).strip() if pd.notna(row.get("name")) else None
                    username = str(row.get("username")).strip() if pd.notna(row.get("username")) else None
                    email = str(row.get("email")).strip() if pd.notna(row.get("email")) else None
                    type_val = str(row.get("type")).strip() if pd.notna(row.get("type")) else None
                    scmprovider = str(row.get("scmprovider")).strip() if pd.notna(row.get("scmprovider")) else None
                    
                    # Only scmprovider is strictly required
                    if not scmprovider:
                        continue
                    
                    labels_value = None
                    if pd.notna(row.get("labels")):
                        labels_str = str(row.get("labels")).strip()
                        if labels_str and labels_str not in ["", "{}"]:
                            try:
                                labels_value = json.loads(labels_str)
                            except:
                                labels_value = None
                    
                    author = AuthorInjectRequest(
                        name=name,
                        username=username,
                        email=email,
                        type=type_val,
                        scmprovider=scmprovider,
                        active=bool(row.get("active", False)) if pd.notna(row.get("active")) else False,
                        archived=bool(row.get("archived", False)) if pd.notna(row.get("archived")) else False,
                        generated=bool(row.get("generated", False)) if pd.notna(row.get("generated")) else False,
                        labels=labels_value,
                    )
                    authors.append(author)
                except:
                    continue
            
            if not authors:
                yield f"data: {json.dumps({'status': 'error', 'message': 'No valid authors found'})}\n\n"
                return
            
            authors_to_process = authors[:limit] if limit else authors
            
            # Send started message
            yield f"data: {json.dumps({'status': 'started', 'total_rows': len(authors_to_process), 'organization_id': organization_id, 'timestamp': str(pd.Timestamp.now())})}\n\n"
            await asyncio.sleep(0.05)
            
            rows_inserted = 0
            rows_skipped = 0
            inserted_list = []
            
            # Process each row
            for idx, author in enumerate(authors_to_process):
                try:
                    # Processing notification
                    yield f"data: {json.dumps({'status': 'processing', 'row': idx + 1, 'total': len(authors_to_process), 'author_name': author.name, 'progress': f'{idx + 1}/{len(authors_to_process)}', 'progress_percent': int((idx / len(authors_to_process)) * 100)})}\n\n"
                    await asyncio.sleep(0.01)
                    
                    # Insert
                    row_data = {
                        "name": author.name,
                        "username": author.username,
                        "email": author.email,
                        "type": author.type,
                        "scmprovider": author.scmprovider,
                        "active": author.active,
                        "archived": author.archived,
                        "generated": author.generated,
                        "labels": json.dumps(author.labels) if author.labels else json.dumps({}),
                        "organizationid": organization_id,
                    }
                    
                    # Use bulk_insert_with_encryption for single row with encryption support
                    inserted = _repository.bulk_insert_with_encryption(session, [row_data])
                    
                    # Commit EACH row immediately so it shows in real-time
                    session.commit()
                    
                    if inserted:
                        rows_inserted += 1
                        author_id = inserted[0].get("id")
                        inserted_list.append({
                            "id": author_id,
                            "name": author.name,
                            "username": author.username,
                            "email": author.email
                        })
                        
                        # Success notification - SENT IMMEDIATELY AFTER COMMIT
                        yield f"data: {json.dumps({'status': 'inserted', 'row': idx + 1, 'total': len(authors_to_process), 'author_id': author_id, 'author_name': author.name, 'inserted_count': rows_inserted, 'skipped_count': rows_skipped, 'progress_percent': int(((idx + 1) / len(authors_to_process)) * 100)})}\n\n"
                    else:
                        rows_skipped += 1
                        yield f"data: {json.dumps({'status': 'failed', 'row': idx + 1, 'total': len(authors_to_process), 'author_name': author.name, 'inserted_count': rows_inserted, 'skipped_count': rows_skipped, 'progress_percent': int(((idx + 1) / len(authors_to_process)) * 100)})}\n\n"
                    
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    rows_skipped += 1
                    session.rollback()
                    yield f"data: {json.dumps({'status': 'error_row', 'row': idx + 1, 'total': len(authors_to_process), 'error': str(e), 'author_name': author.name, 'inserted_count': rows_inserted, 'skipped_count': rows_skipped, 'progress_percent': int(((idx + 1) / len(authors_to_process)) * 100)})}\n\n"
            
            # Final summary
            yield f"data: {json.dumps({'status': 'completed', 'total_processed': len(authors_to_process), 'inserted': rows_inserted, 'skipped': rows_skipped, 'organization_id': organization_id, 'inserted_authors': inserted_list, 'progress_percent': 100})}\n\n"
            
        except Exception as e:
            try:
                session.rollback()
            except:
                pass
            yield f"data: {json.dumps({'status': 'fatal_error', 'error': str(e)})}\n\n"
        
        finally:
            try:
                session.close()
            except:
                pass
    
    return StreamingResponse(
        stream_with_flush(data_generator()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        },
    )
