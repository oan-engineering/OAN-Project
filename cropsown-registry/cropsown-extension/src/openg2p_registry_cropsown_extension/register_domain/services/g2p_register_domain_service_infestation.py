import logging
from datetime import date

from openg2p_registry_core.services import G2PRegisterDomainService

from .domain_compute_utils import compute_ec_date
from .domain_validation_utils import as_float, parse_date, validation_error

_logger = logging.getLogger("g2p-register-domain-service")


class G2PRegisterDomainServiceInfestation(G2PRegisterDomainService):
    async def validate_domain_attributes(self, records: list[dict], session=None, **kwargs):
        for record in records:
            inf_type = record.get("infestation_type")
            if isinstance(inf_type, list):
                record["infestation_type"] = inf_type[0] if inf_type else None
            elif isinstance(inf_type, str) and (inf_type.startswith("[") or inf_type.startswith('["')):
                import json
                try:
                    parsed = json.loads(inf_type)
                    if isinstance(parsed, list):
                        record["infestation_type"] = parsed[0] if parsed else None
                except Exception:
                    record["infestation_type"] = inf_type.replace("[", "").replace("]", "").replace('"', "").replace("'", "").strip()

            from .domain_validation_utils import validate_alphabetical_name, validate_mobile_number
            validate_alphabetical_name(record.get("farmer_name"), "Farmer Name")
            # validate_alphabetical_name(record.get("da_name"), "DA Name")
            # validate_alphabetical_name(record.get("supervisor_name"), "Supervisor Name")
            # validate_mobile_number(record.get("da_mobile_number"), "DA Mobile Number")
            # validate_mobile_number(record.get("supervisor_mobile_number"), "Supervisor Mobile Number")
            self._validate_observation_date(record)
            self._validate_estimated_damage(record)
            compute_ec_date(record, "observation_date", "observation_date_ec")
            if session:
                await self._validate_land_id_matches_sowing(record, session=session)

    async def _validate_land_id_matches_sowing(self, record: dict, session) -> None:
        land_id = record.get("land_id")
        if not land_id or not str(land_id).strip():
            return

        submission_id = record.get("submission_id")
        link_internal_record_id = record.get("link_internal_record_id")
        fayda_fan_id = record.get("fayda_fan_id")

        if not submission_id and not link_internal_record_id and not fayda_fan_id:
            return

        from sqlalchemy import text

        valid_land_ids = set()

        if submission_id:
            for tbl in ("g2p_intake_form_sowings", "g2p_intake_form_cultivations", "g2p_intake_form_plannings"):
                res = await session.execute(
                    text(f"SELECT land_id FROM {tbl} WHERE submission_id = :sub_id"),
                    {"sub_id": submission_id}
                )
                for row in res.fetchall():
                    if row[0] and str(row[0]).strip():
                        valid_land_ids.add(str(row[0]).strip())

            if not fayda_fan_id:
                res_f = await session.execute(
                    text("SELECT fayda_fan_id FROM g2p_intake_form_crop_sowns WHERE submission_id = :sub_id AND fayda_fan_id IS NOT NULL"),
                    {"sub_id": submission_id}
                )
                f_row = res_f.fetchone()
                if f_row and f_row[0]:
                    fayda_fan_id = f_row[0]

        master_ids = set()
        if link_internal_record_id:
            master_ids.add(str(link_internal_record_id))

        if fayda_fan_id:
            res_m = await session.execute(
                text("SELECT internal_record_id::text FROM g2p_register_crop_sowns WHERE fayda_fan_id = :fayda AND record_status = 'ACTIVE'"),
                {"fayda": fayda_fan_id}
            )
            for row in res_m.fetchall():
                if row[0]:
                    master_ids.add(str(row[0]))

        if master_ids:
            for tbl in ("g2p_register_sowings", "g2p_register_cultivations", "g2p_register_plannings"):
                res_db = await session.execute(
                    text(f"SELECT land_id FROM {tbl} WHERE link_internal_record_id = ANY(:m_ids) AND record_status = 'ACTIVE'"),
                    {"m_ids": list(master_ids)}
                )
                for row in res_db.fetchall():
                    if row[0] and str(row[0]).strip():
                        valid_land_ids.add(str(row[0]).strip())

        if str(land_id).strip() not in valid_land_ids:
            msg_fayda = f" for Fayda ID '{fayda_fan_id}'" if fayda_fan_id else ""
            validation_error(f"Land ID '{land_id}' in Pest/Disease Infestation does not match any Land ID specified in crop records{msg_fayda}.")

    def _validate_observation_date(self, record: dict) -> None:
        # Future observation dates are allowed; no restriction here.
        return

    def _validate_estimated_damage(self, record: dict) -> None:
        raw_val = record.get("estimated_damage_pct")
        if raw_val is None or str(raw_val).strip() == "":
            return

        val_str = str(raw_val).strip()

        # Reject any alphabetic characters
        if any(c.isalpha() for c in val_str):
            validation_error("Estimated Crop Damage cannot contain letters. Enter percentage with '%' (e.g. 50%) or pure number for hectares (e.g. 10.5)")

        if "%" in val_str:
            num_part = val_str.replace("%", "").strip()
            try:
                num = float(num_part)
                if not (0 <= num <= 100):
                    validation_error("Percentage damage must be between 0% and 100%")
            except ValueError:
                validation_error("Invalid percentage format for Estimated Crop Damage (e.g., 50%)")
        else:
            try:
                num = float(val_str)
                if num < 0:
                    validation_error("Estimated Crop Damage must be non-negative")
            except ValueError:
                validation_error("Estimated Crop Damage must be numeric (e.g. 10.5 for ha or 50% for percentage)")

    def construct_search_text(self, payload: dict, extra: list[str] = None) -> str:
        _logger.info("Constructing search text for infestation")

        keys = [
            "functional_record_id",
            "land_id",
            "commodity",
            "growth_stage",
            "infestation_type",
            "pest_name",
            "weed_name",
            "disease_name",
            "chemical_used",
            "severity_level",
            "observation_date",
        ]
        search_text = []
        if extra:
            search_text.extend(str(item).strip() for item in extra if str(item).strip())
        search_text.extend(
            str(payload.get(key) or "").strip()
            for key in keys
            if str(payload.get(key) or "").strip()
        )

        return " ".join(search_text).strip()

    def construct_record_name(self, payload: dict, extra: list[str] = None) -> str:
        _logger.info("Constructing record name for infestation")

        keys = ["infestation_type", "severity_level", "observation_date"]
        record_name = []
        if extra:
            record_name.extend(str(item).strip() for item in extra if str(item).strip())
        record_name.extend(
            str(payload.get(key) or "").strip()
            for key in keys
            if str(payload.get(key) or "").strip()
        )

        return " ".join(record_name).strip()
