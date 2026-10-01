-- Crop Sown Registry reporting layer
-- =============================================================================
-- Flattens the register into small, indexed materialized views that the
-- cropsown-registry-dashboard-api service reads. That service reads ONLY these
-- views, never the g2p_register_* tables, so a change to the register's schema
-- is absorbed here, in the repository that owns the schema.
--
--   cs_rpt_crop_sown  one row per farmer-plot-season registration
--                     (g2p_register_crop_sowns): geography, workflow status,
--                     lifecycle stage, season and year.
--   cs_rpt_sowing     one row per sowing line (g2p_register_sowings): crop,
--                     area sown in hectares, sowing date, pest flag and the
--                     plot's ownership type, with the registration's
--                     geography, status and farmer carried down.
--
-- Geography
-- ---------
-- A registration stores each level as a lookup key (REGION_ET04) plus its
-- display name (region_name). The P-code the dashboards filter and draw maps by
-- is the key without its level prefix (ET04).
--
-- Ownership
-- ---------
-- The plot's ownership type is captured on the cultivation stage
-- (g2p_register_cultivations), not on the sowing line. Each sowing line takes
-- the ownership of its registration's cultivation, preferring one for the same
-- crop; a registration without a cultivation yet has NULL ownership.
--
-- Area
-- ----
-- area_sown is captured in hectares (the sowing form has no unit field);
-- area_sown_ha is the column to aggregate, so a unit can be introduced here
-- later without touching the dashboards.
--
-- Personal data
-- -------------
-- None. Farmer, surveyor and supervisor names, phone numbers, GPS points and
-- ids are not carried. A farmer is counted through farmer_key, a one-way hash
-- of the farmer's id, so "how many farmers" is answerable without the id.
--
-- Record status
-- -------------
-- Every row is kept, whatever its record_status: the service counts ACTIVE
-- records by default and needs the others for a status breakdown.
--
-- Refresh
-- -------
-- Materialized, so Postgres never updates them on its own. The reporting job
-- re-applies this file on every install/upgrade; a CronJob refreshes them in
-- dependency order (cs_rpt_crop_sown before cs_rpt_sowing, which reads it).
-- CONCURRENTLY needs the unique indexes created below.
-- =============================================================================

DROP MATERIALIZED VIEW IF EXISTS cs_rpt_sowing CASCADE;
DROP MATERIALIZED VIEW IF EXISTS cs_rpt_crop_sown CASCADE;

-- ---------------------------------------------------------------------------
-- Registrations
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW cs_rpt_crop_sown AS
SELECT
    cs.internal_record_id                                   AS crop_sown_id,
    cs.record_status,
    NULLIF(TRIM(cs.status), '')                             AS status,
    NULLIF(TRIM(cs.lifecycle_stage), '')                    AS lifecycle_stage,
    NULLIF(TRIM(cs.crop_year), '')                          AS crop_year,
    NULLIF(TRIM(cs.production_season), '')                  AS production_season,
    COALESCE(NULLIF(TRIM(ps.value_display), ''), NULLIF(TRIM(cs.production_season), '')) AS production_season_name,
    cs.created_at::date                                     AS registration_date,
    md5(COALESCE(NULLIF(cs.farmer_uuid, ''), NULLIF(cs.farmer_id, ''),
                 NULLIF(cs.fayda_fan_id, ''), cs.internal_record_id)) AS farmer_key,

    COALESCE(NULLIF(TRIM(cs.region_name), ''), NULLIF(TRIM(gr.value_display), ''), NULLIF(TRIM(cs.region), '')) AS region_name,
    COALESCE(NULLIF(TRIM(cs.zone_name), ''),   NULLIF(TRIM(gz.value_display), ''), NULLIF(TRIM(cs.zone), ''))   AS zone_name,
    COALESCE(NULLIF(TRIM(cs.woreda_name), ''), NULLIF(TRIM(gw.value_display), ''), NULLIF(TRIM(cs.woreda), '')) AS woreda_name,
    COALESCE(NULLIF(TRIM(cs.kebele_name), ''), NULLIF(TRIM(gk.value_display), ''), NULLIF(TRIM(cs.kebele), '')) AS kebele_name,
    NULLIF(regexp_replace(TRIM(cs.region), '^[A-Za-z]+[-_]', ''), '') AS region_code,
    NULLIF(regexp_replace(TRIM(cs.zone),   '^[A-Za-z]+[-_]', ''), '') AS zone_code,
    NULLIF(regexp_replace(TRIM(cs.woreda), '^[A-Za-z]+[-_]', ''), '') AS woreda_code,
    NULLIF(regexp_replace(TRIM(cs.kebele), '^[A-Za-z]+[-_]', ''), '') AS kebele_code
FROM g2p_register_crop_sowns cs
LEFT JOIN g2p_attribute_values ps ON ps.value_id = cs.production_season
LEFT JOIN g2p_attribute_values gr ON gr.value_id = cs.region
LEFT JOIN g2p_attribute_values gz ON gz.value_id = cs.zone
LEFT JOIN g2p_attribute_values gw ON gw.value_id = cs.woreda
LEFT JOIN g2p_attribute_values gk ON gk.value_id = cs.kebele;

CREATE UNIQUE INDEX cs_rpt_crop_sown_pk ON cs_rpt_crop_sown (crop_sown_id);
CREATE INDEX cs_rpt_crop_sown_geo_idx ON cs_rpt_crop_sown (region_code, zone_code, woreda_code, kebele_code);

-- ---------------------------------------------------------------------------
-- Sowing lines
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW cs_rpt_sowing AS
SELECT
    sw.internal_record_id                                   AS sowing_id,
    c.crop_sown_id,
    sw.record_status,
    c.record_status                                         AS crop_sown_record_status,
    c.status,
    c.lifecycle_stage,
    c.crop_year,
    c.production_season,
    c.farmer_key,

    NULLIF(TRIM(sw.commodity), '')                          AS commodity,
    COALESCE(NULLIF(TRIM(cm.value_display), ''), NULLIF(TRIM(sw.commodity), '')) AS commodity_name,
    NULLIF(TRIM(sw.season), '')                             AS season,
    COALESCE(NULLIF(TRIM(se.value_display), ''), NULLIF(TRIM(sw.season), ''))    AS season_name,
    sw.area_sown::numeric(18, 6)                            AS area_sown_ha,
    sw.sowing_date,
    COALESCE(sw.sowing_date, c.registration_date)           AS recorded_on,
    sw.has_pest_disease,
    o.ownership_type,
    COALESCE(NULLIF(TRIM(ow.value_display), ''), o.ownership_type) AS ownership_type_name,
    (o.ownership_type IN ('OWNERSHIP_TYPE_OWNER', 'OWNER'))  AS is_owned,

    c.region_name, c.zone_name, c.woreda_name, c.kebele_name,
    c.region_code, c.zone_code, c.woreda_code, c.kebele_code
FROM g2p_register_sowings sw
JOIN cs_rpt_crop_sown c ON c.crop_sown_id = sw.link_internal_record_id
LEFT JOIN LATERAL (
    SELECT NULLIF(TRIM(cu.ownership_type), '') AS ownership_type
    FROM g2p_register_cultivations cu
    WHERE cu.link_internal_record_id = sw.link_internal_record_id
      AND cu.record_status = 'ACTIVE'
      AND NULLIF(TRIM(cu.ownership_type), '') IS NOT NULL
    ORDER BY (cu.commodity IS NOT DISTINCT FROM sw.commodity) DESC, cu.created_at DESC
    LIMIT 1
) o ON true
LEFT JOIN g2p_attribute_values cm ON cm.value_id = sw.commodity
LEFT JOIN g2p_attribute_values se ON se.value_id = sw.season
LEFT JOIN g2p_attribute_values ow ON ow.value_id = o.ownership_type;

CREATE UNIQUE INDEX cs_rpt_sowing_pk ON cs_rpt_sowing (sowing_id);
CREATE INDEX cs_rpt_sowing_crop_sown_idx ON cs_rpt_sowing (crop_sown_id);
CREATE INDEX cs_rpt_sowing_commodity_idx ON cs_rpt_sowing (commodity);
CREATE INDEX cs_rpt_sowing_geo_idx ON cs_rpt_sowing (region_code, zone_code, woreda_code, kebele_code);
