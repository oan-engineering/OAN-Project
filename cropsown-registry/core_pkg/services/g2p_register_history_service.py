import importlib
import logging
import uuid
from datetime import datetime

from openg2p_fastapi_common.service import BaseService
from sqlalchemy import Boolean, Date as SQLDate, Float, Integer, Numeric, inspect, select

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import G2PRegisterChangeRequest, G2PRegisterChangeRequestPayload, G2PRegisterDefinition, RegisterPurposeEnum
from ..schemas.change_request import ChangeActionEnum, ChangePayload

_logger = logging.getLogger("g2p-register-history-service")


class G2PRegisterHistoryService(BaseService):
    async def insert_into_register_history(self, change_request: G2PRegisterChangeRequest, session) -> None:
        register_definition: G2PRegisterDefinition = (
            await session.execute(
                select(G2PRegisterDefinition).where(
                    G2PRegisterDefinition.register_id == change_request.section_register_id
                )
            )
        ).scalar()
        if not register_definition:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[0],
            )
        if register_definition.register_purpose == RegisterPurposeEnum.PROGRAM_REGISTER.value:
            return

        import os
        ext_mod = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_extensions")
        module = importlib.import_module(f"{ext_mod}.register_domain.models")
        history_class = getattr(module, f"G2PRegisterHistory{register_definition.register_mnemonic}")

        schema_module = importlib.import_module(f"{ext_mod}.register_domain.schemas")
        history_schema_class = getattr(schema_module, f"G2PRegisterHistorySchema{register_definition.register_mnemonic}")

        payload_result = await session.execute(
            select(G2PRegisterChangeRequestPayload).where(
                G2PRegisterChangeRequestPayload.change_request_id == change_request.change_request_id
            )
        )
        payload = payload_result.scalar()
        if payload and payload.change_payload:
            for change_payload in payload.change_payload:
                if change_payload.get("edit_action") == ChangeActionEnum.NO_CHANGE.value:
                    continue
                self._create_history_record(
                    change_payload=change_payload,
                    change_request=change_request,
                    history_schema_class=history_schema_class,
                    history_class=history_class,
                    session=session,
                )

    def _create_history_record(
        self,
        change_payload: ChangePayload,
        change_request: G2PRegisterChangeRequest,
        history_schema_class,
        history_class,
        session,
    ) -> None:
        history_schema_instance = history_schema_class(**(change_payload or {}))
        history_dict = {k: v for k, v in history_schema_instance.dict().items() if v is not None}
        history_dict["history_record_id"] = str(uuid.uuid4())
        history_dict["internal_record_id"] = change_payload.get("internal_record_id")
        history_dict["tab_id"] = change_request.tab_id
        history_dict["section_id"] = change_request.section_id
        if "change_request_source" in history_class.__table__.columns:
            history_dict["change_request_source"] = change_request.change_request_source
        if "is_primary_section" in history_class.__table__.columns:
            history_dict["is_primary_section"] = getattr(change_request, "is_primary_section", False)
        history_dict["change_request_id"] = change_request.change_request_id
        history_dict["created_at"] = change_request.created_at
        history_dict["created_by"] = change_request.created_by
        history_dict["approved_at"] = change_request.approved_at
        history_dict["approved_by"] = change_request.approved_by

        history_dict = self._convert_date_strings_to_objects(history_dict, history_class)
        session.add(history_class(**history_dict))

    def _convert_date_strings_to_objects(self, data_dict: dict, model_class) -> dict:
        mapper = inspect(model_class)
        converted_dict = data_dict.copy()

        for key, value in converted_dict.items():
            if value is None or key not in mapper.columns:
                continue
            if isinstance(value, (list, tuple)):
                # JSON/JSONB/ARRAY columns natively hold lists — don't flatten
                # them to a comma-string (that is what corrupts cluster_status).
                if type(mapper.columns[key].type).__name__.upper() in {"JSON", "JSONB", "ARRAY"}:
                    continue
                converted_dict[key] = ",".join(str(v) for v in value if v is not None)
                continue
            column = mapper.columns[key]
            if isinstance(column.type, SQLDate):
                if isinstance(value, str):
                    if not value.strip():
                        converted_dict[key] = None
                        continue
                    try:
                        converted_dict[key] = datetime.strptime(value, "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        _logger.debug("Leaving non-date string value unchanged for history field %s", key)
                elif isinstance(value, datetime):
                    converted_dict[key] = value.date()
            elif isinstance(column.type, Boolean):
                if isinstance(value, str):
                    if value.lower() in ("true", "t", "yes", "1"):
                        converted_dict[key] = True
                    elif value.lower() in ("false", "f", "no", "0", ""):
                        converted_dict[key] = False
            elif isinstance(column.type, (Numeric, Float)):
                if isinstance(value, str):
                    if not value.strip():
                        converted_dict[key] = None
                    else:
                        try:
                            converted_dict[key] = float(value.replace("%", "").strip())
                        except (TypeError, ValueError):
                            converted_dict[key] = None
            elif isinstance(column.type, Integer):
                if isinstance(value, str):
                    if not value.strip():
                        converted_dict[key] = None
                    else:
                        try:
                            converted_dict[key] = int(value.strip())
                        except (TypeError, ValueError):
                            converted_dict[key] = None

        return converted_dict
