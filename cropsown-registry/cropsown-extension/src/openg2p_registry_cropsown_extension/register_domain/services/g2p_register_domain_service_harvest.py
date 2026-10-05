import logging
from datetime import date

from openg2p_registry_core.services import G2PRegisterDomainService

from .domain_compute_utils import compute_harvest_yield, compute_ec_date

from .domain_validation_utils import as_float, parse_date, validation_error, get_attribute_variants

_logger = logging.getLogger("g2p-register-domain-service")


class G2PRegisterDomainServiceHarvest(G2PRegisterDomainService):
    async def validate_domain_attributes(self, records: list[dict], session=None, **kwargs):
        for record in records:

            from .domain_validation_utils import validate_alphabetical_name, validate_mobile_number
            validate_alphabetical_name(record.get("farmer_name"), "Farmer Name")
            validate_alphabetical_name(record.get("da_name"), "DA Name")
            validate_alphabetical_name(record.get("supervisor_name"), "Supervisor Name")
            validate_mobile_number(record.get("da_mobile_number"), "DA Mobile Number")
            validate_mobile_number(record.get("supervisor_mobile_number"), "Supervisor Mobile Number")
            compute_harvest_yield(record)
            self._validate_post_harvest_loss(record)
            self._validate_disposal_quantities(record)
            compute_ec_date(record, "harvest_date", "harvest_date_ec")
            if session:
                await self._validate_land_id_matches_sowing(record, session=session)
                await self._validate_harvest_after_sowing(record, session=session)
                await self._validate_harvest_area_after_sowing(record, session=session)
                # Cluster harvest (cluster_harvest_date): must fall within the cluster's
                # selected season window (start_gc..end_gc), resolved from the cluster /
                # cultivation-cluster records. Independent harvest_date is blank for cluster
                # rows and has no season window, so this only affects cluster rows; if no
                # season window is found the check is skipped (no block).
                await self._validate_date_in_season_enhanced(record, "cluster_harvest_date", session=session)

    async def _validate_harvest_area_after_sowing(self, record: dict, session) -> None:
        area_harvested = as_float(record.get("area_harvested") if record.get("area_harvested") is not None else record.get("cluster_area_harvested"))
        if area_harvested is None or area_harvested <= 0:
            return

        land_id = str(record.get("land_id") or "").strip()
        submission_id = record.get("submission_id")
        link_internal_record_id = record.get("link_internal_record_id")
        season = record.get("season")

        from sqlalchemy import text
        from .domain_validation_utils import get_attribute_variants

        season_vars = get_attribute_variants(season, "CROP_SEASON")

        max_allowed_area = None
        stage_name = "Area Sown in Sowing"

        # 1. Check current submission (Intake Form)
        if submission_id:
            query = "SELECT area_sown FROM g2p_intake_form_sowings WHERE submission_id = :sub_id AND area_sown IS NOT NULL"
            params = {"sub_id": submission_id}
            if land_id:
                query += " AND TRIM(land_id) = :land_id"
                params["land_id"] = land_id
            if season_vars:
                query += " AND season = ANY(:season_vars)"
                params["season_vars"] = season_vars
            res = await session.execute(text(query), params)
            row = res.fetchone()
            if row and row[0] is not None:
                max_allowed_area = float(row[0])

        # 2. Check registered sowing by link_internal_record_id + season
        if max_allowed_area is None and link_internal_record_id:
            query = "SELECT area_sown FROM g2p_register_sowings WHERE link_internal_record_id = :link_id AND record_status = 'ACTIVE' AND area_sown IS NOT NULL"
            params = {"link_id": str(link_internal_record_id)}
            if land_id:
                query += " AND TRIM(land_id) = :land_id"
                params["land_id"] = land_id
            if season_vars:
                query += " AND season = ANY(:season_vars)"
                params["season_vars"] = season_vars
            query += " ORDER BY created_at DESC"
            res = await session.execute(text(query), params)
            row = res.fetchone()
            if row and row[0] is not None:
                max_allowed_area = float(row[0])

        # 3. Check registered sowing by land_id + season
        if max_allowed_area is None and land_id:
            if season_vars:
                query_ls = "SELECT area_sown FROM g2p_register_sowings WHERE TRIM(land_id) = :land_id AND record_status = 'ACTIVE' AND area_sown IS NOT NULL AND season = ANY(:season_vars) ORDER BY created_at DESC"
                res_ls = await session.execute(text(query_ls), {"land_id": land_id, "season_vars": season_vars})
                row_ls = res_ls.fetchone()
                if row_ls and row_ls[0] is not None:
                    max_allowed_area = float(row_ls[0])

            if max_allowed_area is None:
                res_s = await session.execute(
                    text("SELECT area_sown FROM g2p_register_sowings WHERE TRIM(land_id) = :land_id AND record_status = 'ACTIVE' AND area_sown IS NOT NULL ORDER BY created_at DESC"),
                    {"land_id": land_id}
                )
                row_s = res_s.fetchone()
                if row_s and row_s[0] is not None:
                    max_allowed_area = float(row_s[0])

        # 4. Fallback to registered Cultivation area if Sowing is not found
        if max_allowed_area is None:
            stage_name = "Actual Crop Area in Cultivation"
            if link_internal_record_id:
                query_c = "SELECT actual_crop_area FROM g2p_register_cultivations WHERE link_internal_record_id = :link_id AND record_status = 'ACTIVE' AND actual_crop_area IS NOT NULL"
                p_c = {"link_id": str(link_internal_record_id)}
                if season_vars:
                    query_c += " AND season = ANY(:season_vars)"
                    p_c["season_vars"] = season_vars
                query_c += " ORDER BY created_at DESC"
                res_c = await session.execute(text(query_c), p_c)
                row_c = res_c.fetchone()
                if row_c and row_c[0] is not None:
                    max_allowed_area = float(row_c[0])

            if max_allowed_area is None and land_id:
                query_cl = "SELECT actual_crop_area FROM g2p_register_cultivations WHERE TRIM(land_id) = :land_id AND record_status = 'ACTIVE' AND actual_crop_area IS NOT NULL"
                p_cl = {"land_id": land_id}
                if season_vars:
                    query_cl += " AND season = ANY(:season_vars)"
                    p_cl["season_vars"] = season_vars
                query_cl += " ORDER BY created_at DESC"
                res_cl = await session.execute(text(query_cl), p_cl)
                row_cl = res_cl.fetchone()
                if row_cl and row_cl[0] is not None:
                    max_allowed_area = float(row_cl[0])

        # 5. Compare area_harvested against max_allowed_area
        if max_allowed_area is not None and area_harvested > max_allowed_area:
            validation_error(
                f"Area Harvested ({area_harvested} ha) cannot exceed {stage_name} ({max_allowed_area} ha)."
            )

    async def _validate_harvest_after_sowing(self, record: dict, session) -> None:
        harvest_date = parse_date(record.get("harvest_date"))
        if harvest_date is None:
            return

        land_id = str(record.get("land_id") or "").strip()
        submission_id = record.get("submission_id")
        link_internal_record_id = record.get("link_internal_record_id")
        fayda_fan_id = record.get("fayda_fan_id")

        from sqlalchemy import text

        prior_date = None
        prior_stage = None

        if submission_id:
            query = "SELECT sowing_date FROM g2p_intake_form_sowings WHERE submission_id = :sub_id"
            params = {"sub_id": submission_id}
            if land_id:
                query += " AND land_id = :land_id"
                params["land_id"] = land_id
            res = await session.execute(text(query), params)
            row = res.fetchone()
            if row and row[0]:
                prior_date = parse_date(row[0])
                prior_stage = "Sowing Date"

            if not prior_date:
                query_c = "SELECT actual_cultivation_date FROM g2p_intake_form_cultivations WHERE submission_id = :sub_id"
                res_c = await session.execute(text(query_c), params)
                row_c = res_c.fetchone()
                if row_c and row_c[0]:
                    prior_date = parse_date(row_c[0])
                    prior_stage = "Cultivation Date"

            if not prior_date:
                query_p = "SELECT planned_date FROM g2p_intake_form_plannings WHERE submission_id = :sub_id"
                res_p = await session.execute(text(query_p), params)
                row_p = res_p.fetchone()
                if row_p and row_p[0]:
                    prior_date = parse_date(row_p[0])
                    prior_stage = "Planned Date"

        master_ids = set()
        internal_record_id = record.get("internal_record_id")
        if not prior_date and link_internal_record_id:
            master_ids.add(str(link_internal_record_id))
        if not prior_date and internal_record_id:
            res_root = await session.execute(
                text("SELECT internal_record_id::text FROM g2p_register_crop_sowns WHERE internal_record_id = :rec_id AND record_status = 'ACTIVE'"),
                {"rec_id": str(internal_record_id)}
            )
            if res_root.fetchone():
                master_ids.add(str(internal_record_id))
            else:
                res_child = await session.execute(
                    text("SELECT link_internal_record_id::text FROM g2p_register_harvests WHERE internal_record_id = :rec_id"),
                    {"rec_id": str(internal_record_id)}
                )
                row_c = res_child.fetchone()
                if row_c and row_c[0]:
                    master_ids.add(str(row_c[0]))

        if not prior_date and fayda_fan_id:
            res_m = await session.execute(
                text("SELECT internal_record_id::text FROM g2p_register_crop_sowns WHERE fayda_fan_id = :fayda AND record_status = 'ACTIVE'"),
                {"fayda": fayda_fan_id}
            )
            for r in res_m.fetchall():
                if r[0]:
                    master_ids.add(str(r[0]))

        season_vars = get_attribute_variants(record.get("season"), "CROP_SEASON")
        commodity_vars = get_attribute_variants(record.get("commodity"), "CROP_COMMODITY")

        if not prior_date and master_ids:
            query = "SELECT sowing_date FROM g2p_register_sowings WHERE link_internal_record_id = ANY(:m_ids) AND record_status = 'ACTIVE' AND sowing_date IS NOT NULL"
            params = {"m_ids": list(master_ids)}
            if season_vars:
                query += " AND season = ANY(:season_vars)"
                params["season_vars"] = season_vars
            if commodity_vars:
                query += " AND commodity = ANY(:commodity_vars)"
                params["commodity_vars"] = commodity_vars
            if land_id:
                query += " AND land_id = :land_id"
                params["land_id"] = land_id
            query += " ORDER BY sowing_date DESC"
            res = await session.execute(text(query), params)
            row = res.fetchone()
            if row and row[0]:
                prior_date = parse_date(row[0])
                prior_stage = "Sowing Date"

            if not prior_date:
                query_c = "SELECT actual_cultivation_date FROM g2p_register_cultivations WHERE link_internal_record_id = ANY(:m_ids) AND record_status = 'ACTIVE' AND actual_cultivation_date IS NOT NULL"
                params_c = {"m_ids": list(master_ids)}
                if season_vars:
                    query_c += " AND season = ANY(:season_vars)"
                    params_c["season_vars"] = season_vars
                if commodity_vars:
                    query_c += " AND commodity = ANY(:commodity_vars)"
                    params_c["commodity_vars"] = commodity_vars
                if land_id:
                    query_c += " AND land_id = :land_id"
                    params_c["land_id"] = land_id
                query_c += " ORDER BY actual_cultivation_date DESC"
                res_c = await session.execute(text(query_c), params_c)
                row_c = res_c.fetchone()
                if row_c and row_c[0]:
                    prior_date = parse_date(row_c[0])
                    prior_stage = "Cultivation Date"

            if not prior_date:
                query_p = "SELECT planned_date FROM g2p_register_plannings WHERE link_internal_record_id = ANY(:m_ids) AND record_status = 'ACTIVE' AND planned_date IS NOT NULL"
                params_p = {"m_ids": list(master_ids)}
                if season_vars:
                    query_p += " AND season = ANY(:season_vars)"
                    params_p["season_vars"] = season_vars
                if commodity_vars:
                    query_p += " AND commodity = ANY(:commodity_vars)"
                    params_p["commodity_vars"] = commodity_vars
                if land_id:
                    query_p += " AND land_id = :land_id"
                    params_p["land_id"] = land_id
                query_p += " ORDER BY planned_date DESC"
                res_p = await session.execute(text(query_p), params_p)
                row_p = res_p.fetchone()
                if row_p and row_p[0]:
                    prior_date = parse_date(row_p[0])
                    prior_stage = "Planned Date"

        if not prior_date and land_id:
            res_s_fallback = await session.execute(
                text("SELECT sowing_date FROM g2p_register_sowings WHERE land_id = :land_id AND record_status = 'ACTIVE' ORDER BY created_at DESC"),
                {"land_id": land_id}
            )
            row_s_f = res_s_fallback.fetchone()
            if row_s_f and row_s_f[0]:
                prior_date = parse_date(row_s_f[0])
                prior_stage = "Sowing Date"
            else:
                res_c_fallback = await session.execute(
                    text("SELECT actual_cultivation_date FROM g2p_register_cultivations WHERE land_id = :land_id AND record_status = 'ACTIVE' ORDER BY created_at DESC"),
                    {"land_id": land_id}
                )
                row_c_f = res_c_fallback.fetchone()
                if row_c_f and row_c_f[0]:
                    prior_date = parse_date(row_c_f[0])
                    prior_stage = "Cultivation Date"
                else:
                    res_p_fallback = await session.execute(
                        text("SELECT planned_date FROM g2p_register_plannings WHERE land_id = :land_id AND record_status = 'ACTIVE' ORDER BY created_at DESC"),
                        {"land_id": land_id}
                    )
                    row_p_f = res_p_fallback.fetchone()
                    if row_p_f and row_p_f[0]:
                        prior_date = parse_date(row_p_f[0])
                        prior_stage = "Planned Date"

        # Independent harvest (this method only runs for harvest_date, which is
        # blank for cluster rows): a sowing record is required, and the harvest
        # date must be strictly after that sowing date. Cluster harvest dates
        # (cluster_harvest_date) are intentionally not validated here.
        if prior_stage != "Sowing Date" or prior_date is None:
            validation_error(
                "A sowing record is required for this land before a harvest can be recorded."
            )
        if harvest_date <= prior_date:
            validation_error(
                f"Harvest Date ({harvest_date.strftime('%Y-%m-%d')}) must be after the "
                f"Sowing Date ({prior_date.strftime('%Y-%m-%d')})."
            )

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
                f"Cluster Harvest Date ({value.strftime('%Y-%m-%d')}) is before the Season Start Date ({start_gc.strftime('%Y-%m-%d')})."
            )
        if end_gc and value > end_gc:
            validation_error(
                f"Cluster Harvest Date ({value.strftime('%Y-%m-%d')}) is after the Season End Date ({end_gc.strftime('%Y-%m-%d')})."
            )

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
        fayda_fan_id = record.get("fayda_fan_id")

        from sqlalchemy import text

        if submission_id:
            for tbl in ("g2p_intake_form_cultivation_clusters", "g2p_intake_form_clusters"):
                query = f"SELECT start_gc, end_gc FROM {tbl} WHERE submission_id = :sub_id"
                params = {"sub_id": submission_id}
                if land_id:
                    query += " AND land_id = :land_id"
                    params["land_id"] = land_id
                res = await session.execute(text(query), params)
                row = res.fetchone()
                if row and (row[0] or row[1]):
                    return parse_date(row[0]) if row[0] else start, parse_date(row[1]) if row[1] else end

        master_ids = set()
        if link_internal_record_id:
            master_ids.add(str(link_internal_record_id))
        if fayda_fan_id:
            res_m = await session.execute(
                text("SELECT internal_record_id::text FROM g2p_register_crop_sowns WHERE fayda_fan_id = :fayda AND record_status = 'ACTIVE'"),
                {"fayda": fayda_fan_id}
            )
            for r in res_m.fetchall():
                if r[0]:
                    master_ids.add(str(r[0]))

        if master_ids:
            for tbl in ("g2p_register_cultivation_clusters", "g2p_register_clusters"):
                query = f"SELECT start_gc, end_gc FROM {tbl} WHERE link_internal_record_id = ANY(:m_ids) AND record_status = 'ACTIVE'"
                params = {"m_ids": list(master_ids)}
                if land_id:
                    query += " AND land_id = :land_id"
                    params["land_id"] = land_id
                res = await session.execute(text(query), params)
                row = res.fetchone()
                if row and (row[0] or row[1]):
                    return parse_date(row[0]) if row[0] else start, parse_date(row[1]) if row[1] else end

        return start, end

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
            validation_error(f"Land ID '{land_id}' in Harvest does not match any Land ID specified in Sowing or Crop Planning{msg_fayda}.")

    def _validate_post_harvest_loss(self, record: dict) -> None:
        loss_pct = as_float(record.get("post_harvest_loss_pct"))
        if loss_pct is not None and not 0 <= loss_pct <= 100:
            validation_error("post_harvest_loss_pct must be between 0 and 100")

    def _validate_disposal_quantities(self, record: dict) -> None:
        qty_harvested = as_float(record.get("qty_harvested"))
        if qty_harvested is None:
            return
        disposed = sum(
            value
            for value in (
                as_float(record.get("qty_stored")),
                as_float(record.get("qty_sold")),
            )
            if value is not None
        )
        if disposed > qty_harvested:
            validation_error(
                "qty_stored and qty_sold together must not exceed qty_harvested"
            )

    def construct_search_text(self, payload: dict, extra: list[str] = None) -> str:
        _logger.info("Constructing search text for harvest")

        keys = [
            "functional_record_id",
            "land_id",
            "commodity",
            "crop_maturity_status",
            "harvest_date",
            "area_harvested",
            "qty_harvested",
            "qty_stored",
            "qty_sold",
            "harvested_by",
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
        _logger.info("Constructing record name for harvest")

        keys = ["commodity", "harvest_date", "qty_harvested"]
        record_name = []
        if extra:
            record_name.extend(str(item).strip() for item in extra if str(item).strip())
        record_name.extend(
            str(payload.get(key) or "").strip()
            for key in keys
            if str(payload.get(key) or "").strip()
        )

        return " ".join(record_name).strip()
