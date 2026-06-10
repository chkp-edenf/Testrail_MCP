"""TestRail Shared Steps API client.

Shared Steps (a.k.a. Shared Test Steps) are reusable step sets that can be
referenced by multiple test cases. Available in TestRail 7.0+; the
``get_shared_step_history`` endpoint requires TestRail 7.3+.
"""


from ..client.base_client import BaseAPIClient


class SharedStepsClient:
    """Client for shared step operations"""

    def __init__(self, client: BaseAPIClient):
        self._client = client

    async def get_shared_steps(
        self,
        project_id: int,
        created_after: int | None = None,
        created_before: int | None = None,
        created_by: str | None = None,
        updated_after: int | None = None,
        updated_before: int | None = None,
        refs: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict:
        """
        Get shared steps for a project with optional filtering.

        Args:
            project_id: The ID of the project
            created_after: Only return shared steps created after this Unix timestamp (API-supported)
            created_before: Only return shared steps created before this Unix timestamp (API-supported)
            created_by: Comma-separated list of creator user IDs to filter by (API-supported)
            updated_after: Only return shared steps updated after this Unix timestamp (API-supported)
            updated_before: Only return shared steps updated before this Unix timestamp (API-supported)
            refs: Filter by a single reference ID (e.g. TR-a, 4291) (API-supported)
            limit: Maximum number of results to return (default 250, API-supported)
            offset: Pagination offset (API-supported)

        Returns:
            Dict with shared_steps list (and pagination metadata when present)
        """
        params: dict = {}

        if created_after is not None:
            params["created_after"] = created_after
        if created_before is not None:
            params["created_before"] = created_before
        if created_by is not None:
            params["created_by"] = created_by
        if updated_after is not None:
            params["updated_after"] = updated_after
        if updated_before is not None:
            params["updated_before"] = updated_before
        if refs is not None:
            params["refs"] = refs
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        result = await self._client.get(
            f"get_shared_steps/{project_id}",
            params=params if params else None,
        )

        # Handle pagination wrapper
        if isinstance(result, dict) and "shared_steps" in result:
            return result
        return {"shared_steps": result if isinstance(result, list) else []}

    async def get_shared_step(self, shared_step_id: int) -> dict:
        """Get a single set of shared steps by ID"""
        return await self._client.get(f"get_shared_step/{shared_step_id}")

    async def get_shared_step_history(self, shared_step_id: int) -> dict:
        """Get the change history of a set of shared steps (TestRail 7.3+)"""
        return await self._client.get(f"get_shared_step_history/{shared_step_id}")

    async def add_shared_step(self, project_id: int, data: dict) -> dict:
        """Create a new set of shared steps"""
        return await self._client.post(f"add_shared_step/{project_id}", data)

    async def update_shared_step(self, shared_step_id: int, data: dict) -> dict:
        """Update an existing set of shared steps.

        Note: submitting ``custom_steps_separated`` REPLACES all existing steps.
        """
        return await self._client.post(f"update_shared_step/{shared_step_id}", data)

    async def delete_shared_step(
        self, shared_step_id: int, keep_in_cases: bool | int = True
    ) -> dict:
        """Delete a set of shared steps.

        Args:
            shared_step_id: The ID of the set of shared steps
            keep_in_cases: When truthy (default), the steps are kept in the test
                cases that referenced them. Pass False/0 to also remove the steps
                from all referencing test cases. Cannot be undone.
        """
        keep = int(bool(keep_in_cases))
        return await self._client.post(
            f"delete_shared_step/{shared_step_id}", {"keep_in_cases": keep}
        )
