"""
AWE (Approval Workflow Engine) API client helper.

Provides async methods for all AWE runtime interactions needed by
registry consumers.  Every method accepts a ``token`` (Bearer string)
that is forwarded as-is; callers are responsible for obtaining and
refreshing the token via Keycloak client-credentials or on behalf of
the logged-in user.

Endpoint reference (all under ``awe_base_url``):

    POST   /v1/awe/requests                        create_request
    GET    /v1/awe/requests/{id}                   get_request
    GET    /v1/awe/requests                        search_requests
    POST   /v1/awe/requests/{id}/cancel            cancel_request
    GET    /v1/awe/requests/{id}/events             get_request_events
    GET    /v1/awe/tasks                            list_my_open_tasks / list_all_open_tasks
    GET    /v1/awe/tasks/stats                      my_task_stats
    POST   /v1/awe/tasks/{id}/claim                claim_task
    POST   /v1/awe/tasks/{id}/decision             submit_decision

Configuration (env prefix ``registry_core_``):

    awe_base_url                URL of the AWE service   (default: http://localhost:8000)
    awe_http_timeout_seconds    Per-request timeout      (default: 30.0)
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import httpx
from openg2p_fastapi_common.service import BaseService

from .awe_config import get_awe_settings, normalize_awe_base_url

logger = logging.getLogger(__name__)

_ACTIONABLE_TASK_STATUSES = frozenset({"open", "claimed"})


class AWEClientError(Exception):
    """Raised when the AWE API returns a non-2xx response.

    Attributes:
        status_code: HTTP status code returned by AWE.
        error_code:  AWE error code string, e.g. ``"AWE-001"``.
        message:     Human-readable message from the response body.
    """

    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message} (HTTP {status_code})")


class AweHelper(BaseService):
    """Async HTTP client for the OpenG2P Approval Workflow Engine (AWE) API.

    Follows the same singleton pattern as the other helpers in this
    package; obtain an instance with ``AweHelper.get_component()``.

    Example::

        helper = AweHelper.get_component()

        # Create a request
        result = await helper.create_request(
            token=bearer_token,
            policy_key="registry.change_request.v1",
            artifact_type="registry.change_request",
            artifact_id="cr-42",
            context={"district": "D1"},
        )
        request_id = result["request_id"]

        # Check open tasks assigned to the current user
        tasks_page = await helper.list_my_open_tasks(token=bearer_token)

        # Approve the first task
        decision = await helper.submit_decision(
            token=bearer_token,
            task_id=tasks_page["items"][0]["id"],
            action="approve",
            comment="Looks good",
        )
    """

    def __init__(self) -> None:
        super().__init__()
        config = get_awe_settings()
        self._base_url: str = normalize_awe_base_url(config.awe_base_url)
        self._timeout: float = config.awe_http_timeout_seconds

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self, token: str, extra_headers: Optional[Dict[str, str]] = None) -> httpx.AsyncClient:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=self._timeout,
        )

    @staticmethod
    def _raise_for_awe_error(response: httpx.Response) -> None:
        """Parse the AWE error envelope and raise ``AWEClientError`` on failure."""
        if response.is_success:
            return
        try:
            body = response.json()
            error_code = body.get("errorCode", "AWE-UNKNOWN")
            message = body.get("message") or body.get("detail") or response.text
        except Exception:
            error_code = "AWE-UNKNOWN"
            message = response.text
        request_url = str(response.request.url) if response.request else ""
        if request_url:
            message = f"{message} (url={request_url})"
        raise AWEClientError(response.status_code, error_code, message)

    # ------------------------------------------------------------------
    # 1. Create Request
    # ------------------------------------------------------------------

    async def create_request(
        self,
        token: str,
        *,
        policy_key: str,
        artifact_type: str,
        artifact_id: str,
        context: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
        callback_secret_id: Optional[str] = None,
        requester: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a new approval request to AWE.

        Args:
            token:              Bearer token for the calling service.
            policy_key:         Active policy to route the request through,
                                e.g. ``"registry.change_request.v1"``.
            artifact_type:      Domain type of the object under approval,
                                e.g. ``"registry.change_request"``.
            artifact_id:        Stable id of the artifact in the calling system,
                                e.g. ``"cr-42"``.
            context:            Arbitrary JSON dict forwarded to policy rules
                                and stage expressions.
            callback_url:       Optional webhook URL for AWE to POST status events.
            callback_secret_id: Id of the secret stored in AWE used to sign
                                webhook deliveries.
            requester:          Optional human initiator id; defaults to the
                                token's ``sub`` inside AWE.
            idempotency_key:    Optional ``Idempotency-Key`` header value.  AWE
                                returns the cached response on a duplicate key.

        Returns:
            ``CreateRequestOut`` dict with keys ``request_id``, ``status``,
            ``current_stage_order``, and ``tasks``.

        Raises:
            AWEClientError: If AWE returns a non-2xx response.
        """
        payload: Dict[str, Any] = {
            "policy_key": policy_key,
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "context": context or {},
        }
        if callback_url is not None:
            payload["callback_url"] = callback_url
        if callback_secret_id is not None:
            payload["callback_secret_id"] = callback_secret_id
        if requester is not None:
            payload["requester"] = requester

        extra: Dict[str, str] = {}
        if idempotency_key:
            extra["Idempotency-Key"] = idempotency_key

        async with self._client(token, extra) as client:
            response = await client.post("/v1/awe/requests", json=payload)

        self._raise_for_awe_error(response)
        result = response.json()
        logger.debug("AWE create_request → %s", result)
        return result

    # ------------------------------------------------------------------
    # 2. List my open tasks
    # ------------------------------------------------------------------

    async def my_task_stats(
        self,
        token: str,
        *,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return task counts for the caller grouped by artifact type."""
        params: Dict[str, Any] = {}
        if status is not None:
            params["status"] = status

        async with self._client(token) as client:
            response = await client.get("/v1/awe/tasks/stats", params=params)

        self._raise_for_awe_error(response)
        return response.json()

    async def list_my_tasks(
        self,
        token: str,
        *,
        request_id: Optional[str] = None,
        status: Optional[str] = None,
        artifact_type: Optional[str] = None,
        policy_key: Optional[str] = None,
        search_text: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Dict[str, Any]:
        """Return tasks assigned to the caller (``assignee=me``).

        Args:
            token:         Bearer token; its ``sub`` claim is used as the assignee.
            request_id:    Optional filter — list tasks for a single request.
            status:        Optional filter (``open``, ``claimed``, ``completed``, …).
                           Omit to return tasks in every status.
            artifact_type: Optional filter by artifact type.
            policy_key:    Optional filter by policy.
            page:          1-based page number.
            page_size:     Items per page (1–100).

        Returns:
            ``PagedTasksOut`` dict with keys ``items``, ``total``, ``page``,
            ``page_size``, and ``pages``.

        Raises:
            AWEClientError: If AWE returns a non-2xx response.
        """
        return await self._list_tasks(
            token,
            assignee="me",
            request_id=request_id,
            status=status,
            artifact_type=artifact_type,
            policy_key=policy_key,
            search_text=search_text,
            page=page,
            page_size=page_size,
        )

    async def list_my_open_tasks(
        self,
        token: str,
        *,
        request_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        policy_key: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Dict[str, Any]:
        """Return only open tasks for the caller. Convenience wrapper around ``list_my_tasks``."""
        return await self.list_my_tasks(
            token,
            request_id=request_id,
            status="open",
            artifact_type=artifact_type,
            policy_key=policy_key,
            page=page,
            page_size=page_size,
        )

    async def list_tasks_for_request(
        self,
        token: str,
        *,
        request_id: str,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """Return tasks for the registry approval sidebar on a detail page.

        Includes the caller's task(s) for the request plus other approvers'
        completed approved tasks. When the caller has an open or claimed task
        it is listed first; the remaining items are other approved tasks
        ordered by stage.
        """
        all_page = await self._list_tasks(
            token,
            assignee="*",
            request_id=request_id,
            page=1,
            page_size=page_size,
        )
        my_page = await self._list_tasks(
            token,
            assignee="me",
            request_id=request_id,
            page=1,
            page_size=page_size,
        )

        all_items: List[Dict[str, Any]] = list(all_page.get("items") or [])
        my_items: List[Dict[str, Any]] = list(my_page.get("items") or [])
        my_ids = {task["id"] for task in my_items}

        my_actionable = [
            task for task in my_items if task.get("status") in _ACTIONABLE_TASK_STATUSES
        ]
        my_other = [
            task for task in my_items if task.get("status") not in _ACTIONABLE_TASK_STATUSES
        ]
        others_approved = [
            task
            for task in all_items
            if task["id"] not in my_ids
            and task.get("status") == "completed"
            and task.get("decision_action") == "approve"
        ]

        def _stage_sort_key(task: Dict[str, Any]) -> tuple[int, str]:
            return (task.get("stage_order") or 0, task.get("created_at") or "")

        others_approved.sort(key=_stage_sort_key)

        if my_actionable:
            my_actionable.sort(key=_stage_sort_key)
            items = [my_actionable[0], *others_approved]
        else:
            my_other.sort(key=_stage_sort_key)
            items = [*my_other, *others_approved]

        total = len(items)
        return {
            "items": items,
            "total": total,
            "page": 1,
            "page_size": page_size,
            "pages": 1 if total else 1,
        }

    # ------------------------------------------------------------------
    # 3. List all open tasks
    # ------------------------------------------------------------------

    async def list_all_open_tasks(
        self,
        token: str,
        *,
        request_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        policy_key: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Dict[str, Any]:
        """Return all open tasks across every assignee.

        Passing ``assignee=*`` to AWE requires the token to carry the
        ``AWE_ADMIN`` role when the results need to span multiple users;
        in practice use a service-account / admin token here.

        Args:
            token:         Admin Bearer token.
            request_id:    Optional filter — list tasks for a single request.
            artifact_type: Optional filter by artifact type.
            policy_key:    Optional filter by policy.
            page:          1-based page number.
            page_size:     Items per page (1–100).

        Returns:
            ``PagedTasksOut`` dict.

        Raises:
            AWEClientError: If AWE returns a non-2xx response.
        """
        return await self._list_tasks(
            token,
            assignee="*",
            request_id=request_id,
            status="open",
            artifact_type=artifact_type,
            policy_key=policy_key,
            page=page,
            page_size=page_size,
        )

    # ------------------------------------------------------------------
    # 4. Submit decision
    # ------------------------------------------------------------------

    async def submit_decision(
        self,
        token: str,
        task_id: str,
        *,
        action: str,
        comment: Optional[str] = None,
        attachments_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an approve / reject / abstain decision on a task.

        The token's ``sub`` is treated as the actor; the task must be
        assigned to that subject (or the token must carry ``AWE_ADMIN``).

        Args:
            token:           Bearer token of the deciding user.
            task_id:         Id of the task to decide on.
            action:          One of ``"approve"``, ``"reject"``, ``"abstain"``.
            comment:         Optional free-text rationale.
            attachments_ref: Optional reference string pointing to uploaded
                             attachments (format is caller-defined).

        Returns:
            ``DecisionOut`` dict with keys ``id``, ``request_id``, ``task_id``,
            ``stage_order``, ``actor``, ``action``, ``comment``,
            ``attachments_ref``, ``created_at``.

        Raises:
            ValueError:     If ``action`` is not a valid decision value.
            AWEClientError: If AWE returns a non-2xx response.
        """
        if action not in {"approve", "reject", "abstain"}:
            raise ValueError(
                f"action must be one of 'approve', 'reject', 'abstain'; got {action!r}"
            )
        payload: Dict[str, Any] = {"action": action}
        if comment is not None:
            payload["comment"] = comment
        if attachments_ref is not None:
            payload["attachments_ref"] = attachments_ref

        async with self._client(token) as client:
            response = await client.post(f"/v1/awe/tasks/{task_id}/decision", json=payload)

        self._raise_for_awe_error(response)
        result = response.json()
        logger.debug("AWE submit_decision task=%s action=%s → decision=%s", task_id, action, result.get("id"))
        return result

    # ------------------------------------------------------------------
    # 5. Cancel request
    # ------------------------------------------------------------------

    async def cancel_request(
        self,
        token: str,
        request_id: str,
        *,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancel an in-flight approval request.

        Requires a token with the ``AWE_ADMIN`` role.

        Args:
            token:      Admin Bearer token.
            request_id: Id of the request to cancel.
            reason:     Optional human-readable cancellation reason (audited).
            actor:      Optional override for the cancelling actor id; defaults
                        to the token's ``sub`` inside AWE.

        Returns:
            Updated ``RequestOut`` dict with ``status`` set to ``"cancelled"``.

        Raises:
            AWEClientError: If AWE returns a non-2xx response (e.g. 409 if
                            the request is already terminal).
        """
        payload: Dict[str, Any] = {}
        if reason is not None:
            payload["reason"] = reason
        if actor is not None:
            payload["actor"] = actor

        async with self._client(token) as client:
            response = await client.post(
                f"/v1/awe/requests/{request_id}/cancel", json=payload
            )

        self._raise_for_awe_error(response)
        result = response.json()
        logger.debug("AWE cancel_request request=%s → status=%s", request_id, result.get("status"))
        return result

    # ------------------------------------------------------------------
    # 6. Get request events
    # ------------------------------------------------------------------

    async def get_request_events(
        self,
        token: str,
        request_id: str,
    ) -> List[Dict[str, Any]]:
        """Fetch the full, ordered event timeline for an approval request.

        Events are returned oldest-first and cover every lifecycle
        transition (``request_created``, ``task_assigned``,
        ``decision_recorded``, ``stage_advanced``, ``request_approved``,
        ``request_rejected``, ``request_cancelled``, ``task_expired``, …).

        Args:
            token:      Bearer token.
            request_id: Id of the approval request.

        Returns:
            List of ``EventOut`` dicts, each with ``id``, ``request_id``,
            ``event_type``, ``payload``, and ``created_at``.

        Raises:
            AWEClientError: If AWE returns a non-2xx response.
        """
        async with self._client(token) as client:
            response = await client.get(f"/v1/awe/requests/{request_id}/events")

        self._raise_for_awe_error(response)
        result = response.json()
        logger.debug("AWE get_request_events request=%s → %s event(s)", request_id, len(result))
        return result

    # ------------------------------------------------------------------
    # Additional methods
    # ------------------------------------------------------------------

    async def get_request(
        self,
        token: str,
        request_id: str,
    ) -> Dict[str, Any]:
        """Fetch a single approval request by id.

        Args:
            token:      Bearer token.
            request_id: Id of the approval request.

        Returns:
            ``RequestOut`` dict.

        Raises:
            AWEClientError: If AWE returns a non-2xx response.
        """
        async with self._client(token) as client:
            response = await client.get(f"/v1/awe/requests/{request_id}")

        self._raise_for_awe_error(response)
        result = response.json()
        logger.debug("AWE get_request request=%s → status=%s", request_id, result.get("status"))
        return result

    async def search_requests(
        self,
        token: str,
        *,
        artifact_type: Optional[str] = None,
        artifact_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search approval requests with optional filters.

        Args:
            token:         Bearer token.
            artifact_type: Filter by artifact type.
            artifact_id:   Filter by artifact id.
            status:        Filter by request status (``pending``, ``approved``,
                           ``rejected``, ``cancelled``, …).
            limit:         Maximum number of results to return (1–500).

        Returns:
            List of ``RequestOut`` dicts ordered by ``created_at`` descending.

        Raises:
            AWEClientError: If AWE returns a non-2xx response.
        """
        params: Dict[str, Any] = {"limit": limit}
        if artifact_type is not None:
            params["artifact_type"] = artifact_type
        if artifact_id is not None:
            params["artifact_id"] = artifact_id
        if status is not None:
            params["status"] = status

        async with self._client(token) as client:
            response = await client.get("/v1/awe/requests", params=params)

        self._raise_for_awe_error(response)
        result = response.json()
        logger.debug("AWE search_requests → %s result(s)", len(result))
        return result

    async def claim_task(
        self,
        token: str,
        task_id: str,
    ) -> Dict[str, Any]:
        """Claim a task to signal intent to act (optional before ``submit_decision``).

        Args:
            token:   Bearer token of the assignee (or an AWE_ADMIN token).
            task_id: Id of the open task to claim.

        Returns:
            Updated ``TaskOut`` dict with ``status`` set to ``"claimed"``.

        Raises:
            AWEClientError: If AWE returns a non-2xx response (e.g. 409 if
                            the task is not in ``open`` state).
        """
        async with self._client(token) as client:
            response = await client.post(f"/v1/awe/tasks/{task_id}/claim")

        self._raise_for_awe_error(response)
        result = response.json()
        logger.debug("AWE claim_task task=%s → status=%s", task_id, result.get("status"))
        return result

    # ------------------------------------------------------------------
    # Shared task listing implementation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_paged_tasks(
        result: Any,
        *,
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        """Coerce AWE task list responses into ``PagedTasksOut`` shape.

        Some deployments return a bare JSON array instead of the paginated
        envelope; accept both so callers always receive a dict.
        """
        if isinstance(result, dict):
            return result
        if isinstance(result, list):
            total = len(result)
            return {
                "items": result,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": math.ceil(total / page_size) if total and page_size else 1,
            }
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "pages": 1}

    async def _list_tasks(
        self,
        token: str,
        *,
        assignee: str = "me",
        request_id: Optional[str] = None,
        status: Optional[str] = None,
        artifact_type: Optional[str] = None,
        policy_key: Optional[str] = None,
        search_text: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "assignee": assignee,
            "page": page,
            "page_size": page_size,
        }
        if request_id is not None:
            params["request_id"] = request_id
        if status is not None:
            params["status"] = status
        if artifact_type is not None:
            params["artifact_type"] = artifact_type
        if policy_key is not None:
            params["policy_key"] = policy_key
        if search_text is not None:
            params["search_text"] = search_text

        async with self._client(token) as client:
            response = await client.get("/v1/awe/tasks", params=params)

        self._raise_for_awe_error(response)
        result = self._normalize_paged_tasks(
            response.json(),
            page=page,
            page_size=page_size,
        )
        logger.debug(
            "AWE list_tasks assignee=%s status=%s → %s/%s item(s)",
            assignee,
            status,
            len(result.get("items", [])),
            result.get("total"),
        )
        return result
