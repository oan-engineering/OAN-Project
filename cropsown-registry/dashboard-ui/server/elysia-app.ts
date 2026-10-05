// HTTP surface of the dashboard. Every route reads the Crop Sown Registry
// database directly; nothing here serves fixtures or falls back to canned
// numbers, so an empty registry produces empty responses rather than filler.
import { Elysia } from 'elysia'
import cors from '@elysiajs/cors'
import { performance } from 'perf_hooks'
import { CHART_QUERIES, ChartFilters, DYNAMIC_FILTERS } from '@/lib/chart-queries'
import {
  fetchGeoOptions,
  fetchRecordStates,
  fetchRecordsForExport,
  pool,
  resolveGeoValueId,
  testConnection,
  type GeoLevel,
} from '@/lib/db'
import type { Context } from 'elysia'
import { generateCacheKey, getCachedData, setCachedData } from './cache'

// Filterable columns, all on the crop sown record. The queries expose their
// registration as `cs` at the point the filter fragment is spliced in, so one
// mapping serves every chart.
const FILTER_COLUMNS: Record<keyof ChartFilters, string> = {
  region: 'cs.region',
  zone: 'cs.zone',
  woreda: 'cs.woreda',
  kebele: 'cs.kebele',
  recordState: 'cs.status',
}

/** Geography filters carry lookup keys; which level each one belongs to. */
const GEO_LEVELS: Partial<Record<keyof ChartFilters, GeoLevel>> = {
  region: 'REGION',
  zone: 'ZONE',
  woreda: 'WOREDA',
  kebele: 'KEBELE',
}

function buildWhereClause(filters: ChartFilters): { clause: string; values: any[] } {
  const conditions: string[] = []
  const values: any[] = []

  for (const [key, column] of Object.entries(FILTER_COLUMNS)) {
    const value = filters[key as keyof ChartFilters]
    if (!value || value === 'all') continue
    conditions.push(`${column} = $${values.length + 1}`)
    values.push(value)
  }

  if (conditions.length === 0) return { clause: '', values: [] }
  return { clause: `AND ${conditions.join(' AND ')}`, values }
}

/**
 * Rewrites the P-codes the UI sends into the keys records are stored under.
 *
 * The sidebar and the choropleth both work in boundary P-codes ("ET07"), while a
 * record holds "REGION_ET07"; comparing the two directly matches nothing.
 */
async function resolveFilters(filters: ChartFilters): Promise<ChartFilters> {
  const resolved: ChartFilters = { ...filters }

  await Promise.all(
    Object.entries(GEO_LEVELS).map(async ([key, level]) => {
      const value = filters[key as keyof ChartFilters]
      if (!value || value === 'all') return
      resolved[key as keyof ChartFilters] = await resolveGeoValueId(level, value)
    })
  )

  return resolved
}

function prepareChartSql(baseQuery: string, resolved: ChartFilters) {
  const { clause, values } = buildWhereClause(resolved)
  return { sql: baseQuery.replace(DYNAMIC_FILTERS, clause), values }
}

async function executeChartQuery(chartName: string, filters: ChartFilters, resolved: ChartFilters) {
  const cacheKey = generateCacheKey(`chart:${chartName}`, filters)

  const cached = getCachedData<any>(cacheKey)
  if (cached) {
    return { ...cached, fromCache: true }
  }

  const startTime = performance.now()

  try {
    const baseQuery = CHART_QUERIES[chartName as keyof typeof CHART_QUERIES]
    if (!baseQuery) {
      throw new Error(`Query for chart "${chartName}" not found.`)
    }

    const { sql, values } = prepareChartSql(baseQuery, resolved)
    const { rows } = await pool.query(sql, values)

    const result = {
      chartName,
      success: true,
      data: rows,
      error: null,
      executionTime: Math.round(performance.now() - startTime),
    }
    setCachedData(cacheKey, result)
    return result
  } catch (error: any) {
    console.error(`Error executing ${chartName}:`, error)
    return {
      chartName,
      success: false,
      data: [],
      error: error instanceof Error ? error.message : 'Unknown error',
      executionTime: Math.round(performance.now() - startTime),
    }
  }
}

function parseChartFilters(query: Context['query']): ChartFilters {
  return {
    region: (query.region as string) || 'all',
    zone: (query.zone as string) || 'all',
    woreda: (query.woreda as string) || 'all',
    kebele: (query.kebele as string) || 'all',
    recordState: (query.recordState as string) || (query.state as string) || 'all',
  }
}

function jsonToCsv(items: any[]): string {
  if (!items || items.length === 0) return ''
  const replacer = (_key: any, value: any) => (value === null ? '' : value)
  const header = Object.keys(items[0])
  return [
    header.join(','),
    ...items.map(row => header.map(field => JSON.stringify(row[field], replacer)).join(',')),
  ].join('\r\n')
}

export function createElysiaApp(prefix = '/api') {
  return new Elysia({ prefix })
    .use(cors())
    .get('/health', async () => ({
      status: (await testConnection()) ? 'ok' : 'degraded',
      service: 'crop-sown-dashboard',
      timestamp: new Date().toISOString(),
    }))

    // Options for the sidebar's dropdowns, drawn from the registry's own lookup
    // tables so the filters can only offer geography the registry recognises.
    .get('/filter-options', async ({ set }) => {
      try {
        const [regions, recordStatuses] = await Promise.all([
          fetchGeoOptions('REGION'),
          fetchRecordStates(),
        ])
        return { regions, recordStatuses }
      } catch (error: any) {
        console.error('API Error fetching filter options:', error)
        set.status = 500
        return {
          message: 'Failed to fetch filter options',
          error: error instanceof Error ? error.message : 'Unknown error',
        }
      }
    })

    // One step of the geography cascade. The caller passes the parent it has
    // selected, as either a P-code or the stored key, and gets that parent's
    // children back.
    .get('/locations', async ({ query, set }) => {
      const steps: Array<{ param: string; parent: GeoLevel; child: GeoLevel; key: string }> = [
        { param: 'regionId', parent: 'REGION', child: 'ZONE', key: 'zones' },
        { param: 'zoneId', parent: 'ZONE', child: 'WOREDA', key: 'woredas' },
        { param: 'woredaId', parent: 'WOREDA', child: 'KEBELE', key: 'kebeles' },
      ]

      try {
        for (const step of steps) {
          const value = query[step.param] as string | undefined
          if (!value || value === 'all') continue
          const parentValueId = await resolveGeoValueId(step.parent, value)
          return { [step.key]: await fetchGeoOptions(step.child, parentValueId) }
        }

        set.status = 400
        return { error: 'A valid query parameter (regionId, zoneId, or woredaId) is required.' }
      } catch (error: any) {
        console.error('API Error fetching locations:', error)
        set.status = 500
        return { error: 'An internal server error occurred.' }
      }
    })

    // The rows behind the current view, as CSV.
    .post('/data/export', async ({ body, set }) => {
      try {
        const { filters, format, filename } = (body || {}) as any

        if (!format || !filename) {
          set.status = 400
          return { message: 'Missing required parameters' }
        }
        if (format !== 'csv') {
          set.status = 400
          return { message: 'Unsupported format' }
        }

        const resolved = await resolveFilters((filters || {}) as ChartFilters)
        const { clause, values } = buildWhereClause(resolved)
        const rows = await fetchRecordsForExport(clause, values)

        return new Response(jsonToCsv(rows), {
          status: 200,
          headers: {
            'Content-Type': 'text/csv',
            'Content-Disposition': `attachment; filename="${filename}"`,
          },
        })
      } catch (error: any) {
        console.error('API Export Error:', error)
        set.status = 500
        return {
          message: 'Failed to export data',
          error: error instanceof Error ? error.message : 'Unknown error',
        }
      }
    })

    // Chart data. `charts` selects a subset; without it every panel's query runs.
    .get('/charts', async ({ query, set }) => {
      try {
        const filters = parseChartFilters(query)
        const requested = (query.charts as string | undefined)?.split(',').filter(Boolean)
        const targetCharts = requested?.length ? requested : Object.keys(CHART_QUERIES)

        const resolved = await resolveFilters(filters)
        const resultsArray = await Promise.all(
          targetCharts.map(chartId => executeChartQuery(chartId, filters, resolved))
        )

        const results: Record<string, any> = {}
        let successful = 0
        let failed = 0
        let totalExecutionTime = 0

        resultsArray.forEach(result => {
          results[result.chartName] = result
          totalExecutionTime += result.executionTime || 0
          if (result.success) successful++
          else failed++
        })

        return {
          success: true,
          data: results,
          summary: { total: targetCharts.length, successful, failed, totalExecutionTime },
          filters,
          timestamp: new Date().toISOString(),
        }
      } catch (error: any) {
        console.error('Charts API Error:', error)
        set.status = 500
        return {
          success: false,
          error: 'Failed to fetch chart data',
          message: error instanceof Error ? error.message : 'Unknown error',
        }
      }
    })

    .get('/charts/:chartId', async ({ params, query, set }) => {
      const chartName = params.chartId

      try {
        if (!CHART_QUERIES[chartName as keyof typeof CHART_QUERIES]) {
          set.status = 404
          return { success: false, error: `Chart query '${chartName}' not found.` }
        }

        const filters = parseChartFilters(query)
        const resolved = await resolveFilters(filters)
        const result = await executeChartQuery(chartName, filters, resolved)

        if (!result.success) {
          set.status = 500
          return { success: false, error: result.error }
        }

        return { success: true, data: result.data, executionTime: result.executionTime }
      } catch (error: any) {
        console.error(`API Error for [${chartName}]:`, error)
        set.status = 500
        return {
          success: false,
          error: error instanceof Error ? error.message : 'An unknown database error occurred',
        }
      }
    })
}
