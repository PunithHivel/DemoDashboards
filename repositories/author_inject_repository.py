from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

AUTHOR_INJECT_COLUMNS = [
    "name",
    "username",
    "email",
    "type",
    "scmprovider",
    "active",
    "archived",
    "generated",
    "labels",
    "organizationid",
]


class AuthorInjectRepository:
    """Handles author table inserts for injection endpoint using high-performance COPY.
    
    Note: This repository uses COPY which doesn't support custom SQL functions like aes_encrypt.
    If encryption is required, use the original row-by-row approach or handle encryption
    at the application level before inserting.
    """

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        """
        Bulk insert authors using PostgreSQL COPY command.
        
        This is 10-100x faster than row-by-row inserts.
        Returns summary of inserted rows (not individual IDs due to COPY limitations).
        
        WARNING: This bypasses aes_encrypt. If encryption is needed, the data should
        be pre-encrypted before calling this method, or use the legacy row-by-row approach.
        """
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="author",
            columns=AUTHOR_INJECT_COLUMNS,
            rows=rows,
        )
        
        # Return summary since COPY doesn't support RETURNING
        return [{"inserted_count": count}]

    def bulk_insert_with_encryption(self, session: Session, rows: List[Dict]) -> List[Dict]:
        """
        Legacy method that uses row-by-row inserts with aes_encrypt.
        
        Use this when encryption is required. It's slower but supports SQL functions.
        """
        from sqlalchemy import text
        
        AUTHOR_INJECT_INSERT_SQL = text(
            """
            INSERT INTO insightly.author (
                name,
                username,
                email,
                type,
                scmprovider,
                active,
                archived,
                generated,
                labels,
                organizationid
            ) VALUES (
                aes_encrypt(:name),
                aes_encrypt(:username),
                CASE
                    WHEN :email IS NULL THEN NULL
                    ELSE aes_encrypt(:email)
                END,
                :type,
                :scmprovider,
                :active,
                :archived,
                :generated,
                CAST(:labels AS jsonb),
                :organizationid
            )
            RETURNING id, aes_decrypt(name) as name, aes_decrypt(username) as username, 
                      CASE WHEN email IS NULL THEN NULL ELSE aes_decrypt(email) END as email, 
                      organizationid
            """
        )
        
        if not rows:
            return []

        inserted: List[Dict] = []
        for row in rows:
            result = session.execute(AUTHOR_INJECT_INSERT_SQL, row)
            inserted.append(dict(result.mappings().one()))

        return inserted
