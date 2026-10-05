import logging

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..models import (
    DataModel,
    G2PRegisterDefinition,
    IncomingPartner,
    OutgoingRawData,
    OutgoingRawDataPayload,
    OutgoingTopic,
)
from ..schemas import (
    OutgestionSummaryData,
    OutgestionDataSearchResultData,
)
from ..engine import get_engines

_logger = logging.getLogger("g2p-outgestion-data-service")


class G2POutgestionDataService(BaseService):
    async def get_outgestion_summary_data(self) -> OutgestionSummaryData:
        _logger.info("Fetching outgestion summary data through service")
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)

        async with session_maker() as session:
            no_of_messages: int = (
                await session.execute(
                    select(func.count()).select_from(OutgoingRawData)
                )
            ).scalar() or 0

            no_of_topics: int = (
                await session.execute(
                    select(func.count(func.distinct(OutgoingRawData.topic_id)))
                )
            ).scalar() or 0

            no_of_data_models: int = (
                await session.execute(
                    select(func.count(func.distinct(OutgoingRawData.data_model_id)))
                )
            ).scalar() or 0

            return OutgestionSummaryData(
                no_of_messages=no_of_messages,
                no_of_topics=no_of_topics,
                no_of_data_models=no_of_data_models,
            )

    async def search_in_outgestion_data(
        self,
        search_text: str,
        current_page: int = 1,
        page_size: int = 10,
        sort_by: str = None,
        filter_by: dict = None,
    ) -> tuple[list[OutgestionDataSearchResultData], int]:
        _logger.info("Searching in outgestion data through service")
        master_data_engine = get_engines().get("db_engine_master_data")
        master_data_session_maker = async_sessionmaker(master_data_engine, expire_on_commit=False)
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)

        async with session_maker() as session, master_data_session_maker() as master_data_session:
            return await self._search_in_outgestion_data(
                search_text,
                current_page,
                page_size,
                filter_by,
                session,
                master_data_session,
                sort_by,
            )

    async def _search_in_outgestion_data(
        self,
        search_text: str,
        current_page: int,
        page_size: int,
        filter_by: dict,
        session,
        master_data_session,
        sort_by: str = None,
    ) -> tuple[list[OutgestionDataSearchResultData], int]:
        search_query = f"%{search_text}%"

        base_query = (
            select(OutgoingRawData.outgest_id)
            .join(
                OutgoingRawDataPayload,
                OutgoingRawData.payload_id == OutgoingRawDataPayload.payload_id,
            )
            .where(OutgoingRawDataPayload.raw_data_text.ilike(search_query))
        )

        if sort_by:
            if ":" in sort_by:
                sort_field, sort_dir = sort_by.split(":")
            else:
                sort_field, sort_dir = sort_by, "desc"

            if hasattr(OutgoingRawData, sort_field):
                sort_column = getattr(OutgoingRawData, sort_field)
            elif hasattr(OutgoingRawDataPayload, sort_field):
                sort_column = getattr(OutgoingRawDataPayload, sort_field)
            else:
                sort_column = OutgoingRawData.created_at

            if sort_dir.lower() == "desc":
                base_query = base_query.order_by(sort_column.desc())
            else:
                base_query = base_query.order_by(sort_column.asc())
        else:
            base_query = base_query.order_by(OutgoingRawData.created_at.desc())

        count_stmt = (
            select(func.count())
            .select_from(OutgoingRawDataPayload)
            .where(OutgoingRawDataPayload.raw_data_text.ilike(search_query))
        )

        total_items = (await session.execute(count_stmt)).scalar() or 0

        offset = (current_page - 1) * page_size
        query = base_query.offset(offset).limit(page_size)

        outgest_ids = (await session.execute(query)).scalars().all()

        if not outgest_ids:
            return [], total_items

        stmt = (
            select(
                OutgoingRawData.outgest_id,
                OutgoingRawData.payload_id,
                OutgoingRawData.change_request_id,
                OutgoingRawData.intake_form_submission_id,
                OutgoingRawData.internal_record_id,
                OutgoingRawData.register_id,
                G2PRegisterDefinition.register_mnemonic,
                OutgoingRawData.data_model_id,
                DataModel.data_model_mnemonic,
                OutgoingRawData.topic_id,
                OutgoingTopic.websub_topic,
                OutgoingRawData.created_at,
                OutgoingRawData.changed_by,
                OutgoingRawData.changed_at,
                OutgoingRawData.approved_by,
                OutgoingRawData.approved_at,
                OutgoingRawData.changed_by_partner_id,
                OutgoingRawData.transformation_status,
                OutgoingRawData.transformation_datetime,
                OutgoingRawData.transformation_number_of_attempts,
                OutgoingRawData.transformation_latest_error_code,
                OutgoingRawData.publish_status,
                OutgoingRawData.publish_datetime,
                OutgoingRawData.publish_number_of_attempts,
                OutgoingRawData.publish_latest_error_code,
            )
            .select_from(OutgoingRawData)
            .outerjoin(
                DataModel,
                DataModel.data_model_id == OutgoingRawData.data_model_id,
            )
            .outerjoin(
                G2PRegisterDefinition,
                G2PRegisterDefinition.register_id == OutgoingRawData.register_id,
            )
            .outerjoin(
                OutgoingTopic,
                OutgoingTopic.topic_id == OutgoingRawData.topic_id,
            )
            .where(OutgoingRawData.outgest_id.in_(outgest_ids))
        )

        result = await session.execute(stmt)
        rows = result.all()

        row_map = {row.outgest_id: row for row in rows}
        outgestion_data_search_result_data_list: list[OutgestionDataSearchResultData] = []

        for outgest_id in outgest_ids:
            row = row_map.get(outgest_id)
            if not row:
                continue

            partner_mnemonic = None
            if row.changed_by_partner_id:
                partner_mnemonic = (
                    await master_data_session.execute(
                        select(IncomingPartner.partner_mnemonic).where(
                            IncomingPartner.partner_id == row.changed_by_partner_id
                        )
                    )
                ).scalar_one_or_none()

            outgestion_data_search_result_data_list.append(
                OutgestionDataSearchResultData(
                    outgest_id=row.outgest_id,
                    payload_id=row.payload_id,
                    change_request_id=row.change_request_id,
                    intake_form_submission_id=row.intake_form_submission_id,
                    internal_record_id=row.internal_record_id,
                    register_id=row.register_id,
                    register_mnemonic=row.register_mnemonic,
                    data_model_id=row.data_model_id,
                    data_model_mnemonic=row.data_model_mnemonic,
                    topic_id=row.topic_id,
                    websub_topic=row.websub_topic,
                    created_at=row.created_at,
                    changed_by=row.changed_by,
                    changed_at=row.changed_at,
                    approved_by=row.approved_by,
                    approved_at=row.approved_at,
                    changed_by_partner_id=row.changed_by_partner_id,
                    partner_mnemonic=partner_mnemonic,
                    transformation_status=row.transformation_status,
                    transformation_datetime=row.transformation_datetime,
                    transformation_number_of_attempts=row.transformation_number_of_attempts,
                    transformation_latest_error_code=row.transformation_latest_error_code,
                    publish_status=row.publish_status,
                    publish_datetime=row.publish_datetime,
                    publish_number_of_attempts=row.publish_number_of_attempts,
                    publish_latest_error_code=row.publish_latest_error_code,
                )
            )

        return outgestion_data_search_result_data_list, total_items
