"""HTTP endpoint AWE calls (server-to-server) to resolve WHO can approve a
given stage of the Crop Sown hierarchical approval chain (e.g. Kebele -> Woreda),
scoped to the specific location of the record being approved.
"""

import logging
import os

from fastapi import Request
from openg2p_fastapi_common.controller import BaseController
from starlette.responses import JSONResponse

from ..services.approver_resolver_service import resolve_approvers

_logger = logging.getLogger("g2p-cropsown-approver-resolver")


class G2PApproverResolverController(BaseController):
    """Server-to-server endpoint for AWE HTTP approver resolution.
    
    Undecorated with auth middleware so AWE can call it without a user browser session.
    Protected by APPROVER_RESOLVER_SECRET in query string.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.router.tags += ["/cropsown/approver-resolver"]
        self.router.add_api_route("/cropsown/approver-resolver", self.resolve, methods=["POST"])

    async def resolve(self, request: Request) -> JSONResponse:
        level = request.query_params.get("level") or ""
        expected = (os.environ.get("APPROVER_RESOLVER_SECRET") or "cropsown-approver-resolver-secret").strip()
        provided = (request.query_params.get("secret") or "").strip()
        if not expected or provided != expected:
            _logger.warning("approver-resolver: rejected call for level=%s (bad/missing secret)", level)
            return JSONResponse({"user_ids": []}, status_code=401)

        try:
            body = await request.json()
        except Exception:
            body = {}
        context = (body or {}).get("context") or {}

        # Prefer mnemonic name (e.g. "kebele_name"), fallback to code (e.g. "kebele")
        location_value = context.get(f"{level}_name") or context.get(level)
        if not location_value:
            _logger.info("approver-resolver: no '%s' value in context, resolving to unscoped %s approvers", level, level)

        user_ids = await resolve_approvers(level, str(location_value) if location_value else None)
        _logger.info(
            "approver-resolver: level=%s location=%r -> %s", level, location_value, user_ids
        )
        return JSONResponse({"user_ids": user_ids})
