// SQL behind the Crop Sown Registry dashboard.
//
// Every panel reads this registry's own tables — the ones the Staff Portal writes
// to — so the dashboard shows whatever the registry currently holds and nothing
// else. There is no fixture, sample constant or fallback dataset anywhere in this
// path: an empty registry renders empty panels.
//
// Shape of the data (cropsown-extension/register_domain/models):
//
//   g2p_register_crop_sowns   one row per farmer-plot-season registration. Holds
//                             the farmer's identifiers and the administrative
//                             address (region/zone/woreda/kebele).
//   g2p_register_sowings      the sowing lines beneath a registration, linked by
//                             link_internal_record_id. Holds the crop, the area
//                             sown and the plot's ownership type.
//
// Geography and ownership are stored as lookup keys ("REGION_ET07",
// "OWNERSHIP_TYPE_OWNER"), so both are resolved through g2p_attribute_values:
// value_display gives the label to render and value_code gives the P-code the
// choropleth matches its boundaries on. Where a lookup has no row — the crop
// commodity catalogue is served externally and is not seeded locally — the stored
// key is shown rather than inventing a label for it.

/** Filters the API accepts. Geography arrives as P-codes; see convertPcodesToValueIds. */
export interface ChartFilters {
  region?: string
  zone?: string
  woreda?: string
  kebele?: string
  recordState?: string
}

// Replaced with the compiled WHERE fragment by prepareChartSql. It sits inside
// each query's `scope` CTE, where `cs` is in scope, so one filter dialect covers
// every chart regardless of what it aggregates.
export const DYNAMIC_FILTERS = '--- DYNAMIC_FILTERS ---'

// Sowing lines with their registration, narrowed to the current filters. Only
// live records count: the platform keeps superseded rows in the same table and
// marks them, so record_status is checked on both sides of the join.
//
// One registration covers one plot but can carry several sowing lines, so a line
// is the unit of area and of "parcel"; farmers are counted distinctly by
// farmer_uuid because the same farmer legitimately appears on several plots.
const SCOPE = `
  WITH scope AS (
    SELECT
      cs.internal_record_id,
      cs.farmer_uuid,
      cs.region,
      cs.zone,
      cs.woreda,
      cs.kebele,
      sw.internal_record_id AS line_id,
      sw.commodity,
      sw.ownership_type,
      COALESCE(sw.area_sown, 0) AS area_sown,
      -- Registrations are dated by when the sowing happened; rows captured before
      -- a sowing date is known fall back to when the record was created so they
      -- still land somewhere on the timeline.
      COALESCE(sw.sowing_date, cs.created_at::date) AS recorded_on
    FROM g2p_register_crop_sowns cs
    JOIN g2p_register_sowings sw
      ON sw.link_internal_record_id = cs.internal_record_id
     AND sw.record_status = 'ACTIVE'
    WHERE cs.record_status = 'ACTIVE'
      ${DYNAMIC_FILTERS}
  )
`

/** Owner-occupied land, as the ownership value is stored on the record. */
const OWNED = `s.ownership_type = 'OWNER'`

/**
 * Area rolled up to one administrative level.
 *
 * The choropleth reads its value from a column called `farmers` whatever the
 * measure actually is, and matches boundaries on `<level>_code`, so hectares are
 * returned under that name and the lookup's P-code alongside it.
 */
function areaByLevel(level: 'region' | 'zone' | 'woreda' | 'kebele'): string {
  return `
    ${SCOPE}
    SELECT
      COALESCE(NULLIF(TRIM(av.value_display), ''), s.${level}, 'Unknown') AS ${level},
      av.value_code AS ${level}_code,
      ROUND(SUM(s.area_sown))::bigint AS farmers,
      COUNT(DISTINCT s.farmer_uuid) AS farmer_count
    FROM scope s
    LEFT JOIN g2p_attribute_values av ON av.value_id = s.${level}
    GROUP BY 1, 2
    ORDER BY farmers DESC
  `
}

export const CHART_QUERIES = {
  cropKpis: `
    ${SCOPE}
    SELECT
      COALESCE(SUM(s.area_sown), 0) AS total_area,
      COALESCE(SUM(CASE WHEN ${OWNED} THEN s.area_sown ELSE 0 END), 0) AS owned_area,
      COUNT(DISTINCT s.farmer_uuid) AS farmers,
      COUNT(DISTINCT s.commodity) AS crop_types,
      COUNT(DISTINCT s.woreda) AS woredas_reporting,
      -- Plots with nothing sown yet would drag the average down without saying
      -- anything about plot size, so they sit out of this one figure.
      COALESCE(AVG(NULLIF(s.area_sown, 0)), 0) AS avg_plot_size
    FROM scope s
  `,

  cropAreaByCrop: `
    ${SCOPE}
    SELECT
      COALESCE(NULLIF(TRIM(av.value_display), ''), s.commodity) AS crop,
      SUM(s.area_sown) AS area,
      COUNT(DISTINCT s.farmer_uuid) AS farmers
    FROM scope s
    LEFT JOIN g2p_attribute_values av ON av.value_id = s.commodity
    WHERE s.commodity IS NOT NULL
    GROUP BY 1
    HAVING SUM(s.area_sown) > 0
    ORDER BY area DESC
  `,

  cropAreaByRegion: areaByLevel('region'),
  cropAreaByZone: areaByLevel('zone'),
  cropAreaByWoreda: areaByLevel('woreda'),
  cropAreaByKebele: areaByLevel('kebele'),

  cropTopWoredas: `
    ${SCOPE}
    SELECT
      COALESCE(NULLIF(TRIM(av.value_display), ''), s.woreda, 'Unknown') AS woreda,
      av.value_code AS woreda_code,
      SUM(s.area_sown) AS area,
      COUNT(DISTINCT s.farmer_uuid) AS farmers
    FROM scope s
    LEFT JOIN g2p_attribute_values av ON av.value_id = s.woreda
    WHERE s.woreda IS NOT NULL
    GROUP BY 1, 2
    HAVING SUM(s.area_sown) > 0
    ORDER BY area DESC
    LIMIT 8
  `,

  landTenureSplit: `
    ${SCOPE}
    SELECT
      COALESCE(NULLIF(TRIM(av.value_display), ''), s.ownership_type, 'Unknown') AS ownership_type,
      COUNT(s.line_id) AS parcels,
      SUM(s.area_sown) AS area
    FROM scope s
    LEFT JOIN g2p_attribute_values av ON av.value_id = s.ownership_type
    GROUP BY 1
    ORDER BY parcels DESC
  `,

  registryTrendByMonth: `
    ${SCOPE}
    SELECT
      TO_CHAR(DATE_TRUNC('month', s.recorded_on), 'YYYY-MM') AS period,
      COUNT(DISTINCT s.farmer_uuid) AS farmers,
      SUM(s.area_sown) AS total_area,
      SUM(CASE WHEN ${OWNED} THEN s.area_sown ELSE 0 END) AS owned_area
    FROM scope s
    WHERE s.recorded_on IS NOT NULL
    GROUP BY 1
    ORDER BY 1
  `,
} as const

export type ChartName = keyof typeof CHART_QUERIES
