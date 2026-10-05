import logging
import uuid
from datetime import datetime

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import G2PIntakeFormSubmission, G2PRegisterChangeRequest, G2PRegisterVerification
from ..schemas import AddVerificationPayload, VerificationData

_logger = logging.getLogger("g2p-register-verification-service")


class G2PRegisterVerificationService(BaseService):
    async def get_verifications(
        self,
        change_request_id: str | None,
        submission_id: str | None,
        current_page: int = 1,
        page_size: int = 10,
        sort_by: str | None = None,
        filter_by: dict | None = None,
    ) -> tuple[list[VerificationData], int]:
        """Get verifications for either a change request or an intake_form (exactly one target)."""
        self._validate_target_ids(change_request_id, submission_id)
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)

        async with session_maker() as session:
            if change_request_id:
                await self._validate_change_request_exists(change_request_id, session)
                target_condition = G2PRegisterVerification.change_request_id == change_request_id
            else:
                await self._validate_intake_form_exists(submission_id, session)
                target_condition = G2PRegisterVerification.submission_id == submission_id

            count_query = select(func.count()).select_from(G2PRegisterVerification).where(target_condition)
            total_items = (await session.execute(count_query)).scalar() or 0

            query = select(G2PRegisterVerification).where(target_condition)

            # Keep sort behavior simple and stable for now.
            if sort_by and hasattr(G2PRegisterVerification, sort_by.lstrip("-")):
                if sort_by.startswith("-"):
                    sort_col = getattr(G2PRegisterVerification, sort_by[1:])
                    query = query.order_by(sort_col.desc())
                else:
                    sort_col = getattr(G2PRegisterVerification, sort_by)
                    query = query.order_by(sort_col.asc())
            else:
                query = query.order_by(G2PRegisterVerification.verified_at.desc())

            offset = (current_page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            verifications = (await session.execute(query)).scalars().all()

            verifications_list = [self._to_verification_data(v) for v in verifications]
            return verifications_list, total_items

    async def add_verification(self, payload: AddVerificationPayload) -> VerificationData:
        """Add verification for either change_request_id or submission_id (exactly one target)."""
        submission_id = getattr(payload, "submission_id", None)
        self._validate_target_ids(payload.change_request_id, submission_id)
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        verified_by = payload.verified_by

        async with session_maker() as session:
            verification = None
            now = datetime.now()
            verification_id = str(uuid.uuid4())

            if payload.change_request_id:
                change_request = await self._validate_change_request_exists(payload.change_request_id, session)
                verification = G2PRegisterVerification(
                    verification_id=verification_id,
                    register_id=change_request.register_id,
                    internal_record_id=change_request.internal_record_id,
                    section_id=change_request.section_id,
                    change_request_id=change_request.change_request_id,
                    submission_id=None,
                    verified_by=verified_by,
                    verified_at=now,
                    verification_observations=payload.verification_observations,
                    is_approved=payload.is_approved,
                )
                change_request.no_of_verifications_done = (change_request.no_of_verifications_done or 0) + 1
                session.add(change_request)
            else:
                intake_form = await self._validate_intake_form_exists(submission_id, session)
                verification = G2PRegisterVerification(
                    verification_id=verification_id,
                    register_id=intake_form.register_id,
                    internal_record_id=None,
                    section_id=None,
                    change_request_id=None,
                    submission_id=intake_form.submission_id,
                    verified_by=verified_by,
                    verified_at=now,
                    verification_observations=payload.verification_observations,
                    is_approved=payload.is_approved,
                )
                intake_form.number_of_verifications_done = (intake_form.number_of_verifications_done or 0) + 1
                session.add(intake_form)

            session.add(verification)
            await session.commit()
            await session.refresh(verification)
            return self._to_verification_data(verification)

    def _validate_target_ids(self, change_request_id: str | None, submission_id: str | None):
        if bool(change_request_id) == bool(submission_id):
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[1],
                message="Exactly one of change_request_id or submission_id is required",
            )

    async def _validate_change_request_exists(self, change_request_id: str, session) -> G2PRegisterChangeRequest:
        change_request = (
            await session.execute(
                select(G2PRegisterChangeRequest).where(
                    G2PRegisterChangeRequest.change_request_id == change_request_id
                )
            )
        ).scalar_one_or_none()

        if not change_request:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[0],
            )
        return change_request

    async def _validate_intake_form_exists(self, submission_id: str, session) -> G2PIntakeFormSubmission:
        intake_form = await session.get(G2PIntakeFormSubmission, submission_id)
        if not intake_form:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INTAKE_FORM_NOT_FOUND.value[1],
                message=f"{G2PRegistryErrorCodes.INTAKE_FORM_NOT_FOUND.value[0]}: {submission_id}",
            )
        return intake_form

    def _to_verification_data(self, verification: G2PRegisterVerification) -> VerificationData:
        return VerificationData(
            verification_id=verification.verification_id,
            register_id=verification.register_id,
            internal_record_id=verification.internal_record_id,
            section_id=verification.section_id,
            change_request_id=verification.change_request_id,
            submission_id=verification.submission_id,
            verified_by=verification.verified_by,
            verified_at=verification.verified_at.isoformat() if verification.verified_at else None,
            verification_observations=verification.verification_observations,
            is_approved=verification.is_approved,
        )
