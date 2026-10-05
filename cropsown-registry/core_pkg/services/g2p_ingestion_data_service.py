import logging

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import async_sessionmaker
from ..models import (
    DataModel,
    G2PIntakeFormDefinition,
    G2PRegisterDefinition,
    G2PRegisterSection,
    IncomingClassifiedData,
    IncomingEnrichedTransformedData,
    IncomingPartner,
    IncomingRawData,
    IncomingRawDataPayload,
    IncomingTemplate,
)
from ..schemas import (
    IngestionSummaryData,
    IngestionDataPayload,
    IngestionDataSearchResultData,
)
from ..engine import get_engines

_logger = logging.getLogger("g2p-ingestion-data-service")

class G2PIngestionDataService(BaseService):
    async def get_ingestion_summary_data(self) -> IngestionSummaryData:
        _logger.info("Fetching ingestion summary data through service")
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)

        async with session_maker() as session:
            no_of_messages: int = (
                await session.execute(
                    select(func.count()).select_from(IncomingRawData)
                )
            ).scalar() or 0

            no_of_partners: int = (
                await session.execute(
                    select(func.count(func.distinct(IncomingRawData.partner_id)))
                )
            ).scalar() or 0

            no_of_data_models: int = (
                await session.execute(
                    select(func.count(func.distinct(IncomingRawData.data_model_id)))
                )
            ).scalar() or 0
            
            ingestion_summary_data = IngestionSummaryData(
                no_of_messages = no_of_messages,
                no_of_partners = no_of_partners,
                no_of_data_models = no_of_data_models
            )
            return ingestion_summary_data
    
    async def search_in_ingestion_data(
            self, search_text: str, current_page: int = 1, page_size: int = 10, sort_by: str = None, filter_by: dict = None
        ) -> tuple[list[IngestionDataSearchResultData], int]:
        _logger.info("Searching in ingestion data through service")
        master_data_engine = get_engines().get("db_engine_master_data")
        master_data_session_maker = async_sessionmaker(master_data_engine, expire_on_commit=False)
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)

        async with session_maker() as session, master_data_session_maker() as master_data_session:
            search_results, total_items = await self._search_in_ingestion_data(search_text, current_page, page_size, filter_by, session, master_data_session, sort_by)
            return search_results, total_items
    
    async def get_raw_data_payload(self, ingest_id: str) -> IngestionDataPayload:
        _logger.info("Fetching raw payload through service")
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)

        async with session_maker() as session:
            incoming_raw_data_payload = (
                await session.execute(select(IncomingRawDataPayload).where(IncomingRawDataPayload.ingest_id == ingest_id))
            ).scalar_one_or_none()
            if not incoming_raw_data_payload:
                return IngestionDataPayload(raw_data_json=None)
            return IngestionDataPayload(
                raw_data_json=incoming_raw_data_payload.raw_data_json,
            )
    
    async def get_enriched_and_transformed_data_payload(self, ingest_id: str) -> IngestionDataPayload:
        _logger.info("Fetching enriched and transformed data payload through service")
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)

        async with session_maker() as session:
            incoming_enriched_and_transformed_data_payload: IncomingEnrichedTransformedData | None = (
                await session.execute(select(IncomingEnrichedTransformedData).where(IncomingEnrichedTransformedData.ingest_id == ingest_id))
            ).scalar_one_or_none()
            if not incoming_enriched_and_transformed_data_payload:
                return IngestionDataPayload(enriched_data_json=None, transformed_data_json=None)
            return IngestionDataPayload(
                enriched_data_json=incoming_enriched_and_transformed_data_payload.enriched_data_json or None,
                transformed_data_json=incoming_enriched_and_transformed_data_payload.transformed_data_json or None,
            )
    
    async def _search_in_ingestion_data(self, search_text: str, current_page: int, page_size: int, filter_by: dict, session, master_data_session, sort_by: str = None) -> tuple[list[IngestionDataSearchResultData], int]:
        """Helper method to search in ingestion data with pagination"""
        search_query = f"%{search_text}%"

        base_query = (
            select(IncomingRawDataPayload.ingest_id)
            .join(IncomingRawData, IncomingRawData.ingest_id == IncomingRawDataPayload.ingest_id)
            .where(IncomingRawDataPayload.raw_data_text.ilike(search_query))
        )

        if sort_by:
            if ":" in sort_by:
                sort_field, sort_dir = sort_by.split(":")
            else:
                sort_field, sort_dir = sort_by, "desc"

            if hasattr(IncomingRawData, sort_field):
                sort_column = getattr(IncomingRawData, sort_field)
            elif hasattr(IncomingRawDataPayload, sort_field):
                sort_column = getattr(IncomingRawDataPayload, sort_field)
            else:
                sort_column = IncomingRawData.receipt_date_time

            if sort_dir.lower() == "desc":
                base_query = base_query.order_by(sort_column.desc())
            else:
                base_query = base_query.order_by(sort_column.asc())
        else:
            base_query = base_query.order_by(IncomingRawData.receipt_date_time.desc())

        count_stmt = (
            select(func.count())
            .select_from(IncomingRawDataPayload)
            .where(IncomingRawDataPayload.raw_data_text.ilike(search_query))
        )

        total_items = (await session.execute(count_stmt)).scalar() or 0

        offset = (current_page - 1) * page_size
        query = base_query.offset(offset).limit(page_size)

        ingest_ids = (await session.execute(query)).scalars().all()

        if not ingest_ids:
            return [], total_items

        stmt = (
            select(
                IncomingRawData.ingest_id,
                IncomingRawData.partner_id,
                IncomingRawData.data_model_id,
                DataModel.data_model_mnemonic,
                IncomingRawData.ingest_message_id,
                IncomingRawData.ingest_correlation_id,
                IncomingRawData.receipt_date_time,
                IncomingRawData.classification_status,
                IncomingRawData.classification_date_time,
                IncomingRawData.classification_number_of_attempts,
                IncomingRawData.classification_latest_error_code,

                IncomingClassifiedData.intake_form_id,
                G2PIntakeFormDefinition.form_mnemonic.label("intake_form_mnemonic"),
                IncomingClassifiedData.intake_form_submission_id,
                IncomingClassifiedData.register_id,
                G2PRegisterDefinition.register_mnemonic,
                IncomingClassifiedData.semantic_pattern_id,

                IncomingClassifiedData.pipeline_action,
                IncomingClassifiedData.section_id,
                G2PRegisterSection.section_mnemonic.label("classified_section_mnemonic"),
                IncomingClassifiedData.internal_record_id,
                IncomingClassifiedData.change_request_id,

                IncomingTemplate.template_id,
                IncomingTemplate.template_document_id,

                IncomingClassifiedData.transformation_status,
                IncomingClassifiedData.transformation_date_time,
                IncomingClassifiedData.transformation_number_of_attempts,
                IncomingClassifiedData.transformation_latest_error_code,
                IncomingClassifiedData.ingestion_status,
                IncomingClassifiedData.ingestion_date_time,
                IncomingClassifiedData.ingestion_number_of_attempts,
                IncomingClassifiedData.ingestion_latest_error_code,
            )
            .select_from(IncomingRawData)

            # needed for data_model_mnemonic
            .outerjoin(
                DataModel,
                DataModel.data_model_id == IncomingRawData.data_model_id,
            )

            # needed for classified data
            .outerjoin(
                IncomingClassifiedData,
                IncomingClassifiedData.ingest_id == IncomingRawData.ingest_id,
            )

            # needed for register_mnemonic
            .outerjoin(
                G2PRegisterDefinition,
                G2PRegisterDefinition.register_id == IncomingClassifiedData.register_id,
            )

            # needed for intake_form_mnemonic
            .outerjoin(
                G2PIntakeFormDefinition,
                G2PIntakeFormDefinition.form_id == IncomingClassifiedData.intake_form_id,
            )

            .outerjoin(
                G2PRegisterSection,
                and_(
                    G2PRegisterSection.section_id == IncomingClassifiedData.section_id,
                    G2PRegisterSection.register_id == IncomingClassifiedData.register_id,
                ),
            )

            # needed for template
            .outerjoin(
                IncomingTemplate,
                and_(
                    IncomingTemplate.data_model_id == IncomingRawData.data_model_id,
                    IncomingTemplate.register_id == IncomingClassifiedData.register_id,
                )
            )

            .where(IncomingRawData.ingest_id.in_(ingest_ids))
        )

        result = await session.execute(stmt)
        rows = result.all()

        ingestion_data_search_result_data_list: list[IngestionDataSearchResultData] = []
        
        row_map = {row.ingest_id: row for row in rows}

        for ingest_id in ingest_ids:
            row = row_map.get(ingest_id)
            if not row:
                continue
            partner_mnemonic = None
            if row.partner_id:
                partner_mnemonic: str | None = (
                    await master_data_session.execute(select(IncomingPartner.partner_mnemonic).where(IncomingPartner.partner_id == row.partner_id))
                ).scalar_one_or_none()

            ingestion_data_search_result_data_list.append(
                IngestionDataSearchResultData(
                    ingest_id=row.ingest_id,
                    partner_id=row.partner_id,
                    partner_mnemonic=partner_mnemonic,
                    data_model_id=row.data_model_id,
                    data_model_mnemonic=row.data_model_mnemonic,
                    ingest_message_id=row.ingest_message_id,
                    ingest_correlation_id=row.ingest_correlation_id,
                    receipt_date_time=row.receipt_date_time,
                    classification_status=row.classification_status,
                    classification_date_time=row.classification_date_time,
                    classification_number_of_attempts=row.classification_number_of_attempts,
                    classification_latest_error_code=row.classification_latest_error_code,

                    intake_form_id=row.intake_form_id,
                    intake_form_mnemonic=row.intake_form_mnemonic,
                    intake_form_submission_id=row.intake_form_submission_id,
                    register_id=row.register_id,
                    register_mnemonic=row.register_mnemonic,
                    semantic_pattern_id=row.semantic_pattern_id,
                    pipeline_action=row.pipeline_action,
                    section_id=row.section_id,
                    section_mnemonic=row.classified_section_mnemonic,
                    internal_record_id=row.internal_record_id,
                    change_request_id=row.change_request_id,
                    template_id=row.template_id,
                    template_document_id=row.template_document_id,
                    transformation_status=row.transformation_status,
                    transformation_date_time=row.transformation_date_time,
                    transformation_number_of_attempts=row.transformation_number_of_attempts,
                    transformation_latest_error_code=row.transformation_latest_error_code,
                    ingestion_status=row.ingestion_status,
                    ingestion_date_time=row.ingestion_date_time,
                    ingestion_number_of_attempts=row.ingestion_number_of_attempts,
                    ingestion_latest_error_code=row.ingestion_latest_error_code,
                )
            )

        return ingestion_data_search_result_data_list, total_items

