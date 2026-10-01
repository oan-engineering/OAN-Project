import logging
from datetime import datetime
from typing import Dict, Tuple, Optional, List
import uuid
from copy import deepcopy

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.utils.crypto import KeymanagerCryptoHelper

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker
from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..helpers import PatternMatcher
from ..models import (
    IncomingPartner,
    IncomingModelKeyPath,
    IncomingRawData,
    IncomingRawDataPayload,
    IncomingClassifiedData,
    DataModel,
    ProcessStatusEnum,
    IncomingModelSemanticPattern,
)
from ..engine import get_engines

_logger = logging.getLogger("g2p-partner-service")

class G2PIngestService(BaseService):
    async def ingest_data(
        self,
        data_model_mnemonic: Optional[str],
        ingest_data: Dict,
        *,
        register_id: Optional[str] = None,
        intake_form_id: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        _logger.info("Starting data ingestion with received request")
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)

        async with session_maker() as session:
            data_model: DataModel = await self._get_data_model(ingest_data, data_model_mnemonic, session)

            incoming_partner, signature, signature_payload, incoming_model_key_path = await self._match_model_signature_pattern(
                data_model.data_model_id, ingest_data, session
            )
            _logger.debug("Matched incoming model signature pattern")

            # await self._validate_signature(incoming_partner.keymanager_reference_id, signature, signature_payload)
            _logger.debug("Verified request signature")

            message_id = self._match_message_id_pattern(ingest_data, incoming_model_key_path)

            ingest_data_payloads: List[Dict] = []
            if incoming_model_key_path.is_list:
                ingest_data_payloads = self._get_ingest_data_payloads(ingest_data, incoming_model_key_path)
            else:
                ingest_data_payloads = [ingest_data]

            correlation_id = uuid.uuid4().hex
            for ingest_data_payload in ingest_data_payloads:
                ingest_id = str(uuid.uuid4())
                incoming_raw_data = IncomingRawData(
                    ingest_id=ingest_id,
                    partner_id=incoming_partner.partner_id,
                    data_model_id=data_model.data_model_id,
                    ingest_message_id=message_id,
                    ingest_correlation_id=correlation_id,
                    receipt_date_time=datetime.now(),
                )
                incoming_raw_data_payload = IncomingRawDataPayload(
                    ingest_id=ingest_id,
                    raw_data_json=ingest_data_payload,
                )

                _logger.debug(f"Storing raw data and payload to db with ingest_id: {ingest_id}")
                session.add(incoming_raw_data)
                session.add(incoming_raw_data_payload)

                # If classification information is already available, bypass classification stage
                # and directly enqueue for transformation by writing to IncomingClassifiedData.
                if register_id and intake_form_id:
                    incoming_raw_data.classification_status = ProcessStatusEnum.PROCESSED.value
                    incoming_raw_data.classification_date_time = datetime.now()

                    semantic_pattern_id = await self._get_semantic_pattern_id(
                        register_id,
                        intake_form_id,
                        data_model.data_model_id,
                        session,
                    )

                    session.add(
                        IncomingClassifiedData(
                            ingest_id=ingest_id,
                            data_model_id=data_model.data_model_id,
                            partner_id=incoming_partner.partner_id,
                            register_id=register_id,
                            intake_form_id=intake_form_id,
                            semantic_pattern_id=semantic_pattern_id,
                            classified_date_time=datetime.now(),
                            transformation_status=ProcessStatusEnum.PENDING.value,
                        )
                    )

            await session.commit()

            # Resolve the response template document to its store id so downstream
            # (sync) response helpers can render it without a DB session.
            response_template_store_id = None
            if data_model.response_template_document_id:
                from .g2p_template_service import G2PTemplateService
                g2p_template_service = G2PTemplateService.get_component()
                response_template_store_id = await g2p_template_service.resolve_template_store_id(
                    session, data_model.response_template_document_id
                )

            return correlation_id, response_template_store_id


    async def _get_data_model(
        self, ingest_data:Dict, data_model_mnemonic: Optional[str], session
    ) -> DataModel:
        if not data_model_mnemonic:
            data_models = (await session.execute(select(DataModel))).scalars().all()
            for data_model in data_models:
                data_model_mnemonic = self._match_data_model_pattern(
                    data_model, ingest_data
                )
        data_model: DataModel = await self._get_data_model_from_data_model_mnemonic(
            data_model_mnemonic, session
        )
        return data_model

    async def _get_data_model_from_data_model_mnemonic(
        self, data_model_mnemonic: str, session: Session
    ) -> DataModel:
        data_model: DataModel | None = (
            await session.execute(
                select(DataModel).where(
                    DataModel.data_model_mnemonic == data_model_mnemonic
                )
            )
        ).scalar_one_or_none()

        if not data_model:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.DATA_MODEL_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.DATA_MODEL_NOT_FOUND.value[0],
            )
        return data_model

    async def _get_partner_from_partner_mnemonic(
        self, partner_mnemonic: str
    ) -> IncomingPartner:
        """Get incoming partner from master-data-db by partner mnemonic"""
        master_data_engine = get_engines().get("db_engine_master_data")
        master_data_session_maker = async_sessionmaker(master_data_engine, expire_on_commit=False)
        async with master_data_session_maker() as master_data_session:
            partner: IncomingPartner | None = (
                await master_data_session.execute(
                    select(IncomingPartner).where(
                        IncomingPartner.partner_mnemonic == partner_mnemonic
                    )
                )
            ).scalar_one_or_none()
            if not partner:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.PARTNER_NOT_REGISTERED.value[1],
                    message=G2PRegistryErrorCodes.PARTNER_NOT_REGISTERED.value[0],
                )
            return partner

    def _match_message_id_pattern(self, ingest_data: Dict, incoming_model_key_path: IncomingModelKeyPath) -> str:
        pattern_matcher = PatternMatcher().get_component()

        message_id: str = pattern_matcher.get_message_id_pattern_match(incoming_model_key_path, ingest_data)
        return message_id
    
    def _match_data_model_pattern(
        self, data_model: DataModel, ingest_data: Dict
    ) -> str:
        pattern_matcher = PatternMatcher().get_component()

        data_model_mnmeonic: str = pattern_matcher.get_data_model_pattern_match(
            data_model, ingest_data
        )
        return data_model_mnmeonic

    async def _match_model_signature_pattern(
        self, data_model_id: str, ingest_data: Dict, session: Session
    ) -> Tuple[IncomingPartner, str, Dict, IncomingModelKeyPath]:
        pattern_matcher = PatternMatcher().get_component()
        
        incoming_model_key_path: IncomingModelKeyPath | None = (
            await session.execute(
                select(IncomingModelKeyPath).where(
                    IncomingModelKeyPath.data_model_id == data_model_id
                )
            )
        ).scalar_one_or_none()
        if incoming_model_key_path is None:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message=(
                    "No incoming_model_key_paths row for "
                    f"data_model_id={data_model_id}; configure key paths for this model"
                ),
            )

        partner_mnemonic, signature, signature_payload = pattern_matcher.get_signature_pattern_path(
            incoming_model_key_path, ingest_data
        )
        missing_parts: List[str] = []
        if not partner_mnemonic:
            missing_parts.append(
                f"sender/partner key (path {incoming_model_key_path.key_path_for_sender!r})"
            )
        if not signature:
            missing_parts.append(
                f"signature key (path {incoming_model_key_path.key_path_for_signature!r})"
            )
        if not signature_payload:
            missing_parts.append(
                "signature payload key (path "
                f"{incoming_model_key_path.key_path_for_signature_payload!r})"
            )
        if missing_parts:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message=(
                    "Ingest envelope missing required JSONPath values for partner routing: "
                    + "; ".join(missing_parts)
                ),
            )

        incoming_partner = await self._get_partner_from_partner_mnemonic(
            partner_mnemonic
        )
        return incoming_partner, signature, signature_payload, incoming_model_key_path

    async def _validate_signature(self, keymanager_reference_id: str, signature: str, signature_payload: Dict):
        keymanager_helper = KeymanagerCryptoHelper().get_component()
        signature_valid = await keymanager_helper.verify_jwt(
            self,
            orig_jwt=signature,
            payload=signature_payload,
            km_app_id=None,
            km_ref_id=keymanager_reference_id,
        )
        if not signature_valid:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[1],
                message=G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[0],
            )

    def _get_ingest_data_payloads(
        self,
        ingest_data: Dict,
        incoming_model_key_path: IncomingModelKeyPath,
    ) -> List[Dict]:
        """
        Split ingest_data into multiple payloads when a list is present at
        key_path_for_list_elements.

        Example:
            $.body.message.notify_event -> [ {...}, {...}, {...} ]

        Result:
            [
                ingest_data with notify_event = [{...}],
                ingest_data with notify_event = [{...}],
                ingest_data with notify_event = [{...}]
            ]
        """
        elements, jsonpath_expr = self._get_ingest_data_list_elements_path_expr(
            incoming_model_key_path, ingest_data
        )

        if not elements or not isinstance(elements, list):
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message=G2PRegistryErrorCodes.INVALID_REQUEST.value[0],
            )

        ingest_data_payloads: List[Dict] = []

        for element in elements:
            # Deep copy full payload and replace the list of elements with a single element
            payload_copy = deepcopy(ingest_data)
            jsonpath_expr.update(payload_copy, [element])
            ingest_data_payloads.append(payload_copy)

        return ingest_data_payloads

    async def _get_semantic_pattern_id(
        self, register_id: str, intake_form_id: str, data_model_id: str, session: Session
    ) -> str:
        pattern_row = (
            await session.execute(
                select(IncomingModelSemanticPattern).where(
                    IncomingModelSemanticPattern.register_id == register_id,
                    IncomingModelSemanticPattern.intake_form_id == intake_form_id,
                    IncomingModelSemanticPattern.data_model_id == data_model_id,
                )
            )
        ).scalar_one_or_none()

        if pattern_row is None:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message=(
                    "No incoming_model_semantic_patterns row for "
                    f"register_id={register_id}, intake_form_id={intake_form_id}, "
                    f"data_model_id={data_model_id}"
                ),
            )

        return pattern_row.semantic_pattern_id