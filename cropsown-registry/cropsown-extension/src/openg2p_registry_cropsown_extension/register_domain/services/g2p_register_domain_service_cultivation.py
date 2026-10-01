import logging
from datetime import date

from openg2p_registry_core.services import G2PRegisterDomainService

from .domain_compute_utils import (
    compute_season_parts,
    is_date_in_season,
    compute_ec_date
)

from .domain_validation_utils import as_float, parse_date, validation_error

_logger = logging.getLogger("g2p-register-domain-service")


class G2PRegisterDomainServiceCultivation(G2PRegisterDomainService):
    async def validate_domain_attributes(self, records: list[dict], session=None, **kwargs):
        for record in records:
            from .domain_validation_utils import validate_alphabetical_name, validate_mobile_number
            validate_alphabetical_name(record.get("farmer_name"), "Farmer Name")
            validate_alphabetical_name(record.get("da_name"), "DA Name")
            validate_alphabetical_name(record.get("supervisor_name"), "Supervisor Name")
            validate_alphabetical_name(record.get("local_name"), "Local Name")
            validate_alphabetical_name(record.get("scientific_name"), "Scientific Name")
            validate_mobile_number(record.get("da_mobile_number"), "DA Mobile Number")
            validate_mobile_number(record.get("supervisor_mobile_number"), "Supervisor Mobile Number")
            if not str(record.get("season") or "").strip():
                validation_error("Season is required in Cultivation / Land Preparation.")
            if not str(record.get("commodity") or "").strip():
                validation_error("Crop is required in Cultivation / Land Preparation.")

            prod_season = record.get("production_season")
            submission_id = record.get("submission_id")

            if session and submission_id and not prod_season:
                from sqlalchemy import text
                res_hdr = await session.execute(
                    text(
                        "SELECT production_season "
                        "FROM g2p_intake_form_crop_sowns "
                        "WHERE submission_id = :sub_id"
                    ),
                    {"sub_id": submission_id}
                )
                row_hdr = res_hdr.fetchone()
                if row_hdr:
                    prod_season = row_hdr[0]

            season = record.get("season")
            if prod_season and season:
                p_clean = str(prod_season).replace("CROP_SEASON_", "").strip().upper()
                s_clean = str(season).replace("CROP_SEASON_", "").strip().upper()
                if p_clean != s_clean:
                    validation_error(
                        f"Season '{season}' in Cultivation Details does not match the Production Season '{prod_season}' specified in Farmer Identity."
                    )

            compute_season_parts(record)
            await self._validate_date_in_season_enhanced(record, "actual_cultivation_date", session)
            self._validate_actual_cultivation_date(record)
            if session:
                await self._validate_date_after_planning(record, session)
            compute_ec_date(record, "actual_cultivation_date", "actual_cultivation_date_ec")

    def _validate_actual_cultivation_date(self, record: dict) -> None:
        cultivation_date = parse_date(record.get("actual_cultivation_date"))
        if cultivation_date is not None and cultivation_date > date.today():
            validation_error("actual_cultivation_date must not be in the future")

    async def _validate_date_after_planning(self, record: dict, session) -> None:
        cult_date = parse_date(record.get("actual_cultivation_date"))
        if cult_date is None:
            return

        planned_date = await self._resolve_planning_date(record, session)
        if planned_date is not None and cult_date < planned_date:
            validation_error(
                f"Cultivation Date ({cult_date.strftime('%Y-%m-%d')}) cannot be earlier than "
                f"Planned Date ({planned_date.strftime('%Y-%m-%d')}) from Crop Planning."
            )

    async def _resolve_planning_date(self, record: dict, session) -> date | None:
        if not session:
            return None
        land_id = str(record.get("land_id") or "").strip()
        submission_id = record.get("submission_id")
        link_internal_record_id = record.get("link_internal_record_id")
        internal_record_id = record.get("internal_record_id")
        fayda_fan_id = record.get("fayda_fan_id")

        from sqlalchemy import text

        if submission_id:
            query = "SELECT planned_date FROM g2p_intake_form_plannings WHERE submission_id = :sub_id"
            params = {"sub_id": submission_id}
            if land_id:
                query += " AND land_id = :land_id"
                params["land_id"] = land_id
            res = await session.execute(text(query), params)
            row = res.fetchone()
            if row and row[0]:
                return parse_date(row[0])

        master_ids = set()
        if link_internal_record_id:
            master_ids.add(str(link_internal_record_id))
        if internal_record_id:
            res_root = await session.execute(
                text("SELECT internal_record_id::text FROM g2p_register_crop_sowns WHERE internal_record_id = :rec_id AND record_status = 'ACTIVE'"),
                {"rec_id": str(internal_record_id)}
            )
            if res_root.fetchone():
                master_ids.add(str(internal_record_id))
            else:
                res_child = await session.execute(
                    text("SELECT link_internal_record_id::text FROM g2p_register_cultivations WHERE internal_record_id = :rec_id"),
                    {"rec_id": str(internal_record_id)}
                )
                row_c = res_child.fetchone()
                if row_c and row_c[0]:
                    master_ids.add(str(row_c[0]))

        if fayda_fan_id:
            res_m = await session.execute(
                text("SELECT internal_record_id::text FROM g2p_register_crop_sowns WHERE fayda_fan_id = :fayda AND record_status = 'ACTIVE'"),
                {"fayda": fayda_fan_id}
            )
            for r in res_m.fetchall():
                if r[0]:
                    master_ids.add(str(r[0]))

        if master_ids:
            query = "SELECT planned_date FROM g2p_register_plannings WHERE link_internal_record_id = ANY(:m_ids) AND record_status = 'ACTIVE'"
            params = {"m_ids": list(master_ids)}
            if land_id:
                query += " AND land_id = :land_id"
                params["land_id"] = land_id
            res = await session.execute(text(query), params)
            row = res.fetchone()
            if row and row[0]:
                return parse_date(row[0])

        if land_id:
            query = "SELECT planned_date FROM g2p_register_plannings WHERE land_id = :land_id AND record_status = 'ACTIVE' ORDER BY created_at DESC"
            res = await session.execute(text(query), {"land_id": land_id})
            row = res.fetchone()
            if row and row[0]:
                return parse_date(row[0])

        return None

        return None

    async def _validate_date_in_season_enhanced(self, record: dict, field: str, session) -> None:
        value = parse_date(record.get(field))
        if value is None:
            return

        start_gc = parse_date(record.get("start_gc"))
        end_gc = parse_date(record.get("end_gc"))

        if (not start_gc or not end_gc) and session:
            start_gc, end_gc = await self._resolve_season_bounds(record, session)

        if start_gc and value < start_gc:
            validation_error(
                f"Cultivation Date ({value.strftime('%Y-%m-%d')}) is before Season Start Date ({start_gc.strftime('%Y-%m-%d')})."
            )
        if end_gc and value > end_gc:
            validation_error(
                f"Cultivation Date ({value.strftime('%Y-%m-%d')}) is after Season End Date ({end_gc.strftime('%Y-%m-%d')})."
            )

        if not is_date_in_season(value, record.get("start_month"), record.get("start_day"),
                                 record.get("end_month"), record.get("end_day")):
            validation_error(f"{field} falls outside the season window on this record")

    async def _resolve_season_bounds(self, record: dict, session) -> tuple[date | None, date | None]:
        start = parse_date(record.get("start_gc"))
        end = parse_date(record.get("end_gc"))
        if start and end:
            return start, end

        if not session:
            return start, end

        land_id = str(record.get("land_id") or "").strip()
        submission_id = record.get("submission_id")
        link_internal_record_id = record.get("link_internal_record_id")
        internal_record_id = record.get("internal_record_id")
        fayda_fan_id = record.get("fayda_fan_id")

        from sqlalchemy import text

        if submission_id:
            query = "SELECT start_gc, end_gc FROM g2p_intake_form_plannings WHERE submission_id = :sub_id"
            params = {"sub_id": submission_id}
            if land_id:
                query += " AND land_id = :land_id"
                params["land_id"] = land_id
            res = await session.execute(text(query), params)
            row = res.fetchone()
            if row and (row[0] or row[1]):
                s_val = parse_date(row[0]) if row[0] else start
                e_val = parse_date(row[1]) if row[1] else end
                return s_val, e_val

        master_ids = set()
        if link_internal_record_id:
            master_ids.add(str(link_internal_record_id))
        if internal_record_id:
            res_root = await session.execute(
                text("SELECT internal_record_id::text FROM g2p_register_crop_sowns WHERE internal_record_id = :rec_id AND record_status = 'ACTIVE'"),
                {"rec_id": str(internal_record_id)}
            )
            if res_root.fetchone():
                master_ids.add(str(internal_record_id))
            else:
                res_child = await session.execute(
                    text("SELECT link_internal_record_id::text FROM g2p_register_cultivations WHERE internal_record_id = :rec_id"),
                    {"rec_id": str(internal_record_id)}
                )
                row_c = res_child.fetchone()
                if row_c and row_c[0]:
                    master_ids.add(str(row_c[0]))

        if fayda_fan_id:
            res_m = await session.execute(
                text("SELECT internal_record_id::text FROM g2p_register_crop_sowns WHERE fayda_fan_id = :fayda AND record_status = 'ACTIVE'"),
                {"fayda": fayda_fan_id}
            )
            for r in res_m.fetchall():
                if r[0]:
                    master_ids.add(str(r[0]))

        if master_ids:
            query = "SELECT start_gc, end_gc FROM g2p_register_plannings WHERE link_internal_record_id = ANY(:m_ids) AND record_status = 'ACTIVE'"
            params = {"m_ids": list(master_ids)}
            if land_id:
                query += " AND land_id = :land_id"
                params["land_id"] = land_id
            res = await session.execute(text(query), params)
            row = res.fetchone()
            if row and (row[0] or row[1]):
                s_val = parse_date(row[0]) if row[0] else start
                e_val = parse_date(row[1]) if row[1] else end
                return s_val, e_val

        if land_id:
            query = "SELECT start_gc, end_gc FROM g2p_register_plannings WHERE land_id = :land_id AND record_status = 'ACTIVE' ORDER BY created_at DESC"
            res = await session.execute(text(query), {"land_id": land_id})
            row = res.fetchone()
            if row and (row[0] or row[1]):
                s_val = parse_date(row[0]) if row[0] else start
                e_val = parse_date(row[1]) if row[1] else end
                return s_val, e_val

        return start, end

    def construct_search_text(self, payload: dict, extra: list[str] = None) -> str:
        _logger.info("Constructing search text for cultivation")

        keys = [
            "functional_record_id",
            "land_id",
            "season",
            "commodity",
            "crop_variety",
            "crop_category",
            "land_prep_method",
            "cultivation_type",
            "cropping_system",
            "actual_crop_area",
            "actual_seed_class",
            "actual_seed_source",
            "seed_variety",
            "actual_fertilizer_type",
            "water_source",
            "water_source_method",
            "water_source_frequency",
         ]
        search_text = []
        if extra:
            search_text.extend(str(item).strip() for item in extra if str(item).strip())
        for key in keys:
            val = payload.get(key)
            if isinstance(val, (list, tuple)):
                val = ",".join(str(v) for v in val if v is not None)
            if str(val or "").strip():
                search_text.append(str(val).strip())

        return " ".join(search_text).strip()

    def construct_record_name(self, payload: dict, extra: list[str] = None) -> str:
        _logger.info("Constructing record name for cultivation")

        keys = ["commodity", "land_prep_method", "actual_crop_area"]
        record_name = []
        if extra:
            record_name.extend(str(item).strip() for item in extra if str(item).strip())
        for key in keys:
            val = payload.get(key)
            if isinstance(val, (list, tuple)):
                val = ",".join(str(v) for v in val if v is not None)
            if str(val or "").strip():
                record_name.append(str(val).strip())

        return " ".join(record_name).strip()
