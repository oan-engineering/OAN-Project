import logging
import uuid
import enum
import importlib
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta, date
from difflib import SequenceMatcher

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine

from openg2p_registry_core.schemas import DeduplicationFieldConfig
from sqlalchemy.orm import Session
from sqlalchemy import func, insert, select, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import (
    G2PRegisterChangeRequest,
    G2PRegisterDefinition,
    G2PRegisterSection,
    G2PRegisterVerification,
    G2PRegisterSchema,
    DeduplicationRegisterResult,
    DeduplicationChangerequestResult,
    DeduplicationStatusEnum
)
from ..schemas import ChangeRequestRequest
from ..errors import G2PRegistryErrorCodes, G2PRegistryException

_logger = logging.getLogger('g2p-register-domain-service')
_engine = dbengine.get()

class G2PRegisterDomainService(BaseService):

    class DeduplicationMatchType(str, enum.Enum):
        EXACT = "EXACT"
        FUZZY = "FUZZY"
        PHONETIC = "PHONETIC"
        NUMERIC_RANGE = "NUMERIC_RANGE"
        DATE_RANGE = "DATE_RANGE"

    @classmethod
    def _normalize_match_type(cls, match_type: Optional[str]) -> str:
        """Normalize persisted match type values to enum-compatible constants."""
        if not match_type:
            return cls.DeduplicationMatchType.EXACT.value

        normalized_value = str(match_type).strip().replace("-", "_").upper()
        alias_map = {
            "NUMERIC": cls.DeduplicationMatchType.NUMERIC_RANGE.value,
            "DATE": cls.DeduplicationMatchType.DATE_RANGE.value,
        }
        return alias_map.get(normalized_value, normalized_value)
    
    def construct_record_name(self, payload: dict, extra: list[str] = None) -> str:
        raise NotImplementedError("Register Domain Service should be overridden by the domain service implementation")

    def construct_intake_record_name(self, payload: dict, extra: list[str] = None) -> str:
        """Build intake-form record_name; default appends application_reference when present."""
        record_name = self.construct_record_name(payload, extra)
        application_reference = str(payload.get("application_reference") or "").strip()
        if application_reference and application_reference not in record_name:
            return f"{record_name} {application_reference}".strip() if record_name else application_reference
        return record_name

    def construct_search_text(self, payload: dict, extra: list[str] = None) -> str:
        raise NotImplementedError("Register Domain Service should be overridden by the domain service implementation")

    async def validate_domain_attributes(self, records: list[dict], **kwargs):
        raise NotImplementedError("Register Domain Service should be overridden by the domain service implementation")

    async def pre_approve(self, change_request: G2PRegisterChangeRequest, session: AsyncSession):
        pass

    async def post_approve(self, change_request: G2PRegisterChangeRequest, session: AsyncSession):
        pass

    async def post_ingest(self, register_id: str, register_row, session: AsyncSession):
        pass

    async def populate_link_internal_record_id_for_intake_form(self, session: AsyncSession):
        pass

    def compute_deduplication_score_for_register(
        self,
        change_request_id: str,
        register_id: str,
        incoming_data: dict,
        session: Session
    ) -> List[Dict]:
        """
        Compute deduplication scores for a change request against register records.
        Returns list of matching records with scores.
        """
        try:
            incoming_data = self._normalize_dedup_input(
                incoming_data,
                context=f"register/change_request_id={change_request_id}",
            )
            if not incoming_data:
                return []

            # Get register definition with dedup config
            register_definition: G2PRegisterDefinition = (
                session.execute(
                    select(G2PRegisterDefinition).where(
                        G2PRegisterDefinition.register_id == register_id
                    )
                )
            ).scalar()

            if not register_definition or not register_definition.dedup_is_enabled:
                _logger.info(f"Deduplication is disabled for register {register_id}")
                return []

            # Get register schema with deduplicate_schema
            register_schema: G2PRegisterSchema = (
                session.execute(
                    select(G2PRegisterSchema).where(
                        G2PRegisterSchema.register_id == register_id
                    )
                )
            ).scalar()

            deduplicate_schema: List[DeduplicationFieldConfig] = (
                register_schema.deduplicate_schema if register_schema else None
            ) or []

            # Find candidate records
            candidates = self._find_candidate_records(
                incoming_data,
                register_definition,
                deduplicate_schema,
                session
            )

            # Compute scores for each candidate
            results = []
            for candidate in candidates:
                score = self._compute_score(
                    incoming_data,
                    candidate,
                    deduplicate_schema
                )

                if score >= (register_definition.dedup_threshold_score or 0):
                    field_matches = self._compute_field_matches(
                        incoming_data,
                        candidate,
                        deduplicate_schema
                    )
                    results.append({
                        "candidate_id": candidate.internal_record_id,
                        "score": score,
                        "field_matches": field_matches
                    })

            return results

        except Exception as e:
            _logger.error(f"Error computing deduplication score for register: {str(e)}")
            raise

    def compute_deduplication_score_for_change_request(
        self,
        change_request_id: str,
        register_id: str,
        incoming_data: dict,
        other_change_requests: List,
        session: Session
    ) -> List[Dict]:
        """
        Compute deduplication scores for a change request against other pending change_requests.
        Returns list of matching change_request records with scores.
        """
        try:
            incoming_data = self._normalize_dedup_input(
                incoming_data,
                context=f"change_request/change_request_id={change_request_id}",
            )
            if not incoming_data:
                return []

            # Get register definition with dedup config
            register_definition: G2PRegisterDefinition = (
                session.execute(
                    select(G2PRegisterDefinition).where(
                        G2PRegisterDefinition.register_id == register_id
                    )
                )
            ).scalar()

            if not register_definition or not register_definition.dedup_is_enabled:
                _logger.info(f"Deduplication is disabled for register {register_id}")
                return []

            # Get register schema with deduplicate_schema
            register_schema: G2PRegisterSchema = (
                session.execute(
                    select(G2PRegisterSchema).where(
                        G2PRegisterSchema.register_id == register_id
                    )
                )
            ).scalar()

            deduplicate_schema: List[DeduplicationFieldConfig] = (
                register_schema.deduplicate_schema if register_schema else None
            ) or []

            results = []
            other_change_requests = other_change_requests or []
            for other_change_request in other_change_requests:
                candidate_id = other_change_request.get("change_request_id")
                normalized_payload = self._normalize_dedup_input(
                    other_change_request.get("change_payload"),
                    context=f"candidate_change_request_id={candidate_id}",
                )
                if not normalized_payload:
                    continue
                # Create a simple object from the other payload for field matching
                other_obj = type('obj', (object,), normalized_payload)()

                score = self._compute_score(
                    incoming_data,
                    other_obj,
                    deduplicate_schema
                )

                if score >= (register_definition.dedup_threshold_score or 0):
                    field_matches = self._compute_field_matches(
                        incoming_data,
                        other_obj,
                        deduplicate_schema
                    )
                    results.append({
                        "candidate_id": other_change_request.get('change_request_id'),
                        "score": score,
                        "field_matches": field_matches
                    })

            return results

        except Exception as e:
            _logger.error(f"Error computing deduplication score for change_request: {str(e)}")
            raise

    def _compute_score(
        self,
        incoming_data: dict,
        candidate_record,
        deduplicate_schema: List[DeduplicationFieldConfig]
    ) -> float:
        """Compute similarity score between incoming data and candidate record."""
        try:
            total_weighted_score = 0.0
            total_weight = 0.0

            for dedup_field in deduplicate_schema:
                field_name = dedup_field.get("field_name")
                match_type = self._normalize_match_type(
                    dedup_field.get("match_type", self.DeduplicationMatchType.EXACT.value)
                )
                weight = dedup_field.get("weight", 1.0)
                similarity_threshold = dedup_field.get("similarity_threshold", 0.7)

                incoming_value = incoming_data.get(field_name)
                candidate_value = getattr(candidate_record, field_name, None)

                total_weight += weight

                if not incoming_value or not candidate_value:
                    continue

                field_similarity = self._compute_field_similarity(
                    incoming_value,
                    candidate_value,
                    match_type
                )

                if field_similarity >= similarity_threshold:
                    total_weighted_score += field_similarity * weight

            if total_weight == 0:
                return 0.0

            final_score = (total_weighted_score / total_weight) * 100
            return final_score

        except Exception as e:
            _logger.error(f"Error computing score: {str(e)}")
            return 0.0

    def _find_candidate_records(
        self,
        incoming_data: dict,
        register_definition: G2PRegisterDefinition,
        deduplicate_schema: List[DeduplicationFieldConfig],
        session: Session
    ) -> list:
        """Find candidate records from the register based on dedup fields."""
        try:
            # Get register class
            import os
            ext_mod = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_extensions")
            module = importlib.import_module(f"{ext_mod}.register_domain.models")
            register_class_prefix = "G2PRegister"
            implementation_class_name = f"{register_class_prefix}{register_definition.register_mnemonic}"
            register_class = getattr(module, implementation_class_name)

            # Build query conditions
            query_conditions = []

            for dedup_field in deduplicate_schema:

                field_name = dedup_field.get("field_name")
                match_type = self._normalize_match_type(
                    dedup_field.get("match_type", self.DeduplicationMatchType.EXACT.value)
                )

                incoming_value = incoming_data.get(field_name)
                if not incoming_value or not hasattr(register_class, field_name):
                    continue

                column = getattr(register_class, field_name)

                if match_type == self.DeduplicationMatchType.EXACT.value:
                    query_conditions.append(column == incoming_value)
                elif match_type == self.DeduplicationMatchType.FUZZY.value:
                    query_conditions.append(column.ilike(f"%{incoming_value}%"))
                elif match_type == self.DeduplicationMatchType.PHONETIC.value:
                    # Phonetic matching - match first 3 characters
                    phonetic_prefix = str(incoming_value).strip().lower()[:3]
                    query_conditions.append(column.ilike(f"{phonetic_prefix}%"))
                elif match_type == self.DeduplicationMatchType.NUMERIC_RANGE.value:
                    # Numeric range matching
                    range_value = dedup_field.get("range_value", 0)
                    try:
                        incoming_num = float(incoming_value)
                        start_num = incoming_num - range_value
                        end_num = incoming_num + range_value
                        query_conditions.append(column.between(start_num, end_num))
                    except (ValueError, TypeError):
                        continue
                elif match_type == self.DeduplicationMatchType.DATE_RANGE.value:
                    # Date range matching
                    range_days = dedup_field.get("range_days", 0)
                    try:
                        if isinstance(incoming_value, str):
                            incoming_date = datetime.fromisoformat(incoming_value).date()
                        else:
                            incoming_date = incoming_value
                        start_date = incoming_date - timedelta(days=range_days)
                        end_date = incoming_date + timedelta(days=range_days)
                        query_conditions.append(column.between(start_date, end_date))
                    except (ValueError, TypeError):
                        continue

            if not query_conditions:
                return []
            candidates = (
                session.execute(
                    select(register_class).where(or_(*query_conditions))
                )
            ).scalars().all()

            _logger.info(f"Found {len(candidates)} candidate records for deduplication")
            return candidates

        except Exception as e:
            _logger.error(f"Error finding candidate records: {str(e)}")
            raise

    def _compute_field_matches(
        self,
        incoming_data: dict,
        candidate_record,
        deduplicate_schema: List[DeduplicationFieldConfig]
    ) -> dict:
        """Compute field matches with similarity scores for each dedup field."""
        try:
            field_matches = {}

            for dedup_field in deduplicate_schema:
                field_name = dedup_field.get("field_name")
                match_type = self._normalize_match_type(
                    dedup_field.get("match_type", self.DeduplicationMatchType.EXACT.value)
                )

                incoming_value = incoming_data.get(field_name)
                candidate_value = getattr(candidate_record, field_name, None)

                if not incoming_value or not candidate_value:
                    field_matches[field_name] = {
                        "incoming": incoming_value,
                        "candidate": candidate_value,
                        "similarity": 0.0,
                        "match_type": match_type
                    }
                    continue

                similarity = self._compute_field_similarity(
                    incoming_value,
                    candidate_value,
                    match_type
                )

                field_matches[field_name] = {
                    "incoming": str(incoming_value),
                    "candidate": str(candidate_value),
                    "similarity": similarity,
                    "match_type": match_type
                }

            return field_matches

        except Exception as e:
            _logger.error(f"Error computing field matches: {str(e)}")
            return {}

    def _compute_field_similarity(
        self,
        incoming_value,
        candidate_value,
        match_type: str
    ) -> float:
        """Compute similarity between two field values based on match type."""
        try:
            if match_type == self.DeduplicationMatchType.EXACT.value:
                return 1.0 if str(incoming_value).strip().lower() == str(candidate_value).strip().lower() else 0.0

            elif match_type == self.DeduplicationMatchType.FUZZY.value:
                incoming_str = str(incoming_value).strip().lower()
                candidate_str = str(candidate_value).strip().lower()
                return SequenceMatcher(None, incoming_str, candidate_str).ratio()

            elif match_type == self.DeduplicationMatchType.PHONETIC.value:
                # Simple phonetic matching using first 3 characters
                incoming_phonetic = str(incoming_value).strip().lower()[:3]
                candidate_phonetic = str(candidate_value).strip().lower()[:3]
                return 1.0 if incoming_phonetic == candidate_phonetic else 0.5

            elif match_type == self.DeduplicationMatchType.NUMERIC_RANGE.value:
                # Exact match for numeric values
                return 1.0 if str(incoming_value).strip() == str(candidate_value).strip() else 0.0

            elif match_type == self.DeduplicationMatchType.DATE_RANGE.value:
                # For date range, we check if dates are close (handled in _find_candidate_records)
                # Here we just check if they match exactly
                return 1.0 if str(incoming_value).strip() == str(candidate_value).strip() else 0.8

            else:
                return 0.0

        except Exception as e:
            _logger.error(f"Error computing field similarity: {str(e)}")
            return 0.0

    def _normalize_dedup_input(self, payload, *, context: str) -> dict:
        """Normalize payload variants to the dict shape expected by dedup scoring."""
        if isinstance(payload, dict):
            return payload

        if isinstance(payload, list):
            if not payload:
                _logger.info(f"Empty payload list for dedup input ({context}); dedup will produce no matches.")
                return {}
            first_item = payload[0]
            if isinstance(first_item, dict):
                _logger.info(f"Normalized payload list to first item for dedup input ({context}).")
                return first_item
            _logger.warning(
                f"Unsupported first list item type for dedup input ({context}): {type(first_item).__name__}; "
                "dedup will produce no matches."
            )
            return {}

        if payload is None:
            _logger.info(f"Missing dedup payload input ({context}); dedup will produce no matches.")
            return {}

        _logger.warning(
            f"Unsupported dedup payload input type ({context}): {type(payload).__name__}; dedup will produce no matches."
        )
        return {}
