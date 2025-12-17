from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Sequence
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session


TARGET_ORG_ID = 2159

TEMPLATE_QUERY = text(
    "SELECT * FROM insightly.repo ORDER BY id LIMIT 1"
)

REPO_INSERT_SQL = text(
    """
    INSERT INTO insightly.repo (
        name,
        slug,
        created_on,
        updated_on,
        workspaceid,
        organizationid,
        is_private,
        language,
        main_branch,
        owner,
        project,
        included,
        webhookpublished,
        uuid,
        webhookuuid,
        initialcommitsfetch,
        initialpullrequestfetch,
        archived,
        httpurl,
        namespace,
        weburl,
        unavailable,
        repocloneattemptcount,
        api_commit_date,
        excluded,
        userintegrationid,
        repoaccess,
        codereview_enabled,
        codereview_enabled_on,
        last_excluded_on,
        excluded_reason,
        exclusion_history
    ) VALUES (
        :name,
        :slug,
        :created_on,
        :updated_on,
        :workspaceid,
        :organizationid,
        :is_private,
        :language,
        :main_branch,
        :owner,
        :project,
        :included,
        :webhookpublished,
        :uuid,
        :webhookuuid,
        :initialcommitsfetch,
        :initialpullrequestfetch,
        :archived,
        :httpurl,
        :namespace,
        :weburl,
        :unavailable,
        :repocloneattemptcount,
        :api_commit_date,
        :excluded,
        :userintegrationid,
        :repoaccess,
        :codereview_enabled,
        :codereview_enabled_on,
        :last_excluded_on,
        :excluded_reason,
        :exclusion_history
    )
    RETURNING id, name, workspaceid, slug, httpurl
    """
)


class RepoRepository:
    """Repository utilities for repo seeding."""

    def _fetch_template(self, session: Session) -> Dict:
        result = session.execute(TEMPLATE_QUERY).mappings().first()
        if not result:
            raise ValueError("Unable to locate a template repo row in the database.")
        return dict(result)

    def create_dummy_repos(
        self, session: Session, workspace_id: int, count: int, organization_id: int = TARGET_ORG_ID
    ) -> List[Dict]:
        template = self._fetch_template(session)
        now = datetime.utcnow()

        created: List[Dict] = []
        for _ in range(count):
            unique_suffix = uuid4().hex[:8]
            name = f"testing-repo-{unique_suffix}"
            slug = name.replace("_", "-")
            httpurl = f"https://dummy.repo/{unique_suffix}"

            params = {
                "name": name,
                "slug": slug,
                "created_on": now,
                "updated_on": now,
                "workspaceid": workspace_id,
                "organizationid": organization_id,
                "is_private": template.get("is_private"),
                "language": template.get("language"),
                "main_branch": template.get("main_branch"),
                "owner": template.get("owner"),
                "project": template.get("project"),
                "included": template.get("included", True),
                "webhookpublished": template.get("webhookpublished", False),
                "uuid": uuid4().hex,
                "webhookuuid": template.get("webhookuuid"),
                "initialcommitsfetch": template.get("initialcommitsfetch"),
                "initialpullrequestfetch": template.get("initialpullrequestfetch"),
                "archived": template.get("archived"),
                "httpurl": httpurl,
                "namespace": template.get("namespace"),
                "weburl": httpurl,
                "unavailable": template.get("unavailable"),
                "repocloneattemptcount": template.get("repocloneattemptcount"),
                "api_commit_date": template.get("api_commit_date"),
                "excluded": template.get("excluded"),
                "userintegrationid": template.get("userintegrationid"),
                "repoaccess": template.get("repoaccess"),
                "codereview_enabled": template.get("codereview_enabled"),
                "codereview_enabled_on": template.get("codereview_enabled_on"),
                "last_excluded_on": template.get("last_excluded_on"),
                "excluded_reason": template.get("excluded_reason"),
                "exclusion_history": template.get("exclusion_history"),
            }

            result = session.execute(REPO_INSERT_SQL, params)
            created.append(dict(result.mappings().one()))

        return created
