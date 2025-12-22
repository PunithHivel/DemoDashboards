from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


WORKSPACE_INSERT_SQL = text(
    """
    INSERT INTO insightly.workspace (name, slug)
    VALUES (:name, :slug)
    RETURNING id
    """
)


class WorkspaceRepository:
    """Provides helpers for inserting test workspaces."""

    def create_dummy_workspace(
        self,
        session: Session,
        name: str = "testing",
        slug: str = "testing",
    ) -> int:
        result = session.execute(
            WORKSPACE_INSERT_SQL,
            {"name": name, "slug": slug},
        )
        new_id = result.scalar_one()
        return new_id
