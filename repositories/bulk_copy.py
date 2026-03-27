"""
Bulk copy utilities for high-performance database inserts using PostgreSQL COPY command.

These functions provide 10-100x faster inserts compared to row-by-row operations
by using PostgreSQL's native COPY command.
"""

from typing import List, Dict, Any
from io import StringIO
import csv
from sqlalchemy.orm import Session
from sqlalchemy import text


def bulk_copy_insert_jira(
    session: Session,
    table_name: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
) -> int:
    """
    Bulk insert rows into insightly_jira schema using PostgreSQL COPY command.
    
    This is significantly faster than individual INSERT statements.
    
    Args:
        session: SQLAlchemy session
        table_name: Target table name (e.g., "issue_event_log", "issue")
        columns: List of column names to insert
        rows: List of dictionaries containing row data
        
    Returns:
        Number of rows inserted
        
    Note:
        - Does not support RETURNING clause (COPY limitation)
        - Does not support SQL functions like aes_encrypt
        - All data must be pre-processed before calling this function
    """
    if not rows:
        return 0
    
    # Create CSV data in memory
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=columns,
        extrasaction='ignore',  # Ignore extra columns not in fieldnames
        delimiter='\t',  # Use tab delimiter for better compatibility
        quoting=csv.QUOTE_MINIMAL
    )
    
    # Write rows (no header)
    for row in rows:
        # Convert None to \N (PostgreSQL NULL representation in COPY)
        processed_row = {
            col: '\\N' if row.get(col) is None else str(row.get(col, ''))
            for col in columns
        }
        writer.writerow(processed_row)
    
    # Get the CSV content
    output.seek(0)
    csv_data = output.getvalue()
    
    # Use raw connection for COPY command
    connection = session.connection().connection
    cursor = connection.cursor()
    
    try:
        # Build COPY command for insightly_jira schema
        copy_sql = f"COPY insightly_jira.{table_name} ({', '.join(columns)}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')"
        
        # Execute COPY
        cursor.copy_expert(copy_sql, StringIO(csv_data))
        
        # Get row count
        row_count = cursor.rowcount
        
        # Commit is handled by SQLAlchemy session
        return row_count
        
    except Exception as e:
        raise Exception(f"Error in bulk_copy_insert_jira for {table_name}: {str(e)}")
    finally:
        cursor.close()


def bulk_copy_insert(
    session: Session,
    table_name: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
) -> int:
    """
    Bulk insert rows using PostgreSQL COPY command.
    
    This is significantly faster than individual INSERT statements.
    
    Args:
        session: SQLAlchemy session
        table_name: Target table name (e.g., "author", "pull_request")
        columns: List of column names to insert
        rows: List of dictionaries containing row data
        
    Returns:
        Number of rows inserted
        
    Note:
        - Does not support RETURNING clause (COPY limitation)
        - Does not support SQL functions like aes_encrypt
        - All data must be pre-processed before calling this function
    """
    if not rows:
        return 0
    
    # Create CSV data in memory
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=columns,
        extrasaction='ignore',  # Ignore extra columns not in fieldnames
        delimiter='\t',  # Use tab delimiter for better compatibility
        quoting=csv.QUOTE_MINIMAL
    )
    
    # Write rows (no header)
    for row in rows:
        # Convert None to \N (PostgreSQL NULL representation in COPY)
        processed_row = {
            col: '\\N' if row.get(col) is None else str(row.get(col, ''))
            for col in columns
        }
        writer.writerow(processed_row)
    
    # Get the CSV content
    output.seek(0)
    csv_data = output.getvalue()
    
    # Use raw connection for COPY command
    connection = session.connection().connection
    cursor = connection.cursor()
    
    try:
        # Build COPY command
        copy_sql = f"COPY insightly.{table_name} ({', '.join(columns)}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')"
        
        # Execute COPY
        cursor.copy_expert(copy_sql, StringIO(csv_data))
        
        # Get row count
        row_count = cursor.rowcount
        
        # Commit is handled by SQLAlchemy session
        return row_count
        
    except Exception as e:
        raise Exception(f"Error in bulk_copy_insert for {table_name}: {str(e)}")
    finally:
        cursor.close()


def bulk_copy_upsert(
    session: Session,
    table_name: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
    conflict_columns: List[str],
) -> int:
    """
    Bulk upsert (INSERT ... ON CONFLICT DO UPDATE) using temp table + COPY.
    
    This approach:
    1. Creates a temporary table
    2. Uses COPY to load data into temp table (fast)
    3. Uses INSERT ... ON CONFLICT to merge into target table
    
    Args:
        session: SQLAlchemy session
        table_name: Target table name
        columns: List of column names
        rows: List of dictionaries containing row data
        conflict_columns: Columns to check for conflicts (usually primary key or unique constraint)
        
    Returns:
        Number of rows inserted/updated
        
    Note:
        This is much faster than individual UPSERT statements for large datasets.
    """
    if not rows:
        return 0
    
    # Create temporary table name
    temp_table = f"temp_{table_name}_{id(rows)}"
    
    try:
        # Step 1: Create temporary table with same structure
        create_temp_sql = text(f"""
            CREATE TEMP TABLE {temp_table} (LIKE insightly.{table_name} INCLUDING DEFAULTS)
            ON COMMIT DROP
        """)
        session.execute(create_temp_sql)
        
        # Step 2: Use COPY to load data into temp table
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=columns,
            extrasaction='ignore',
            delimiter='\t',
            quoting=csv.QUOTE_MINIMAL
        )
        
        for row in rows:
            processed_row = {
                col: '\\N' if row.get(col) is None else str(row.get(col, ''))
                for col in columns
            }
            writer.writerow(processed_row)
        
        output.seek(0)
        csv_data = output.getvalue()
        
        # Use raw connection for COPY
        connection = session.connection().connection
        cursor = connection.cursor()
        
        try:
            copy_sql = f"COPY {temp_table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')"
            cursor.copy_expert(copy_sql, StringIO(csv_data))
        finally:
            cursor.close()
        
        # Step 3: Merge from temp table to target table using INSERT ... ON CONFLICT
        conflict_cols_str = ', '.join(conflict_columns)
        update_cols = [col for col in columns if col not in conflict_columns]
        update_set = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_cols])
        
        merge_sql = text(f"""
            INSERT INTO insightly.{table_name} ({', '.join(columns)})
            SELECT {', '.join(columns)}
            FROM {temp_table}
            ON CONFLICT ({conflict_cols_str})
            DO UPDATE SET {update_set}
        """)
        
        result = session.execute(merge_sql)
        row_count = result.rowcount
        
        return row_count
        
    except Exception as e:
        raise Exception(f"Error in bulk_copy_upsert for {table_name}: {str(e)}")


def bulk_copy_insert_returning_ids(
    session: Session,
    table_name: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
) -> List[int]:
    """
    Bulk insert with returning IDs.
    
    Note: This uses a different approach than pure COPY since COPY doesn't support RETURNING.
    Uses INSERT ... SELECT for better performance than row-by-row while still getting IDs.
    
    Args:
        session: SQLAlchemy session
        table_name: Target table name
        columns: List of column names
        rows: List of dictionaries containing row data
        
    Returns:
        List of inserted IDs
        
    Note:
        Slower than bulk_copy_insert but faster than row-by-row and returns IDs.
    """
    if not rows:
        return []
    
    # Create temporary table
    temp_table = f"temp_{table_name}_{id(rows)}"
    
    try:
        # Create temp table
        create_temp_sql = text(f"""
            CREATE TEMP TABLE {temp_table} (LIKE insightly.{table_name} INCLUDING DEFAULTS)
            ON COMMIT DROP
        """)
        session.execute(create_temp_sql)
        
        # Use COPY to load into temp table
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=columns,
            extrasaction='ignore',
            delimiter='\t',
            quoting=csv.QUOTE_MINIMAL
        )
        
        for row in rows:
            processed_row = {
                col: '\\N' if row.get(col) is None else str(row.get(col, ''))
                for col in columns
            }
            writer.writerow(processed_row)
        
        output.seek(0)
        csv_data = output.getvalue()
        
        connection = session.connection().connection
        cursor = connection.cursor()
        
        try:
            copy_sql = f"COPY {temp_table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')"
            cursor.copy_expert(copy_sql, StringIO(csv_data))
        finally:
            cursor.close()
        
        # Insert from temp table with RETURNING
        insert_sql = text(f"""
            INSERT INTO insightly.{table_name} ({', '.join(columns)})
            SELECT {', '.join(columns)}
            FROM {temp_table}
            RETURNING id
        """)
        
        result = session.execute(insert_sql)
        ids = [row[0] for row in result]
        
        return ids
        
    except Exception as e:
        raise Exception(f"Error in bulk_copy_insert_returning_ids for {table_name}: {str(e)}")
