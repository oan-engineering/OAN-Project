import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Text, JSON, func, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from openg2p_fastapi_common.models import BaseORMModel


class G2PRegisterVerification(BaseORMModel):
    __tablename__ = "g2p_register_verifications"

    verification_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    internal_record_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    section_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    change_request_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    submission_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    verified_by: Mapped[str] = mapped_column(String, nullable=False)
    verified_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    verification_observations: Mapped[Text] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    @classmethod
    async def get_verification_count_for_change_request(cls, session: AsyncSession, change_request_id: str) -> int:
        return (await session.execute(
            select(func.count()).select_from(G2PRegisterVerification).where(
                G2PRegisterVerification.change_request_id == change_request_id,
                G2PRegisterVerification.is_approved
            )
        )).scalar_one()

    @classmethod
    async def get_verification_count_for_intake_form_submission(cls, session: AsyncSession, submission_id: str) -> int:
        return (await session.execute(
            select(func.count()).select_from(G2PRegisterVerification).where(
                G2PRegisterVerification.submission_id == submission_id,
                G2PRegisterVerification.is_approved
            )
        )).scalar_one()


