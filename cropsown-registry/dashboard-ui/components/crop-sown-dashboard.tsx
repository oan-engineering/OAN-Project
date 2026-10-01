"use client"

// Crop Sown Registry view. Rendered in place of the tabbed dashboard whenever the
// Farming Type filter is set to crop farming. Laid out as a single screen with no
// scrolling, using the same band grid and panel density as the landing overview.

import { useMemo } from "react"
import { MapPinned, Ruler, Sprout, Users, Wheat } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { useChartGroupData } from "@/hooks/use-data"
import { MapWhenVisible } from "@/components/lazy/map-when-visible"
import {
  BarList,
  BRIGHT,
  BRIGHT_SOFT,
  DeltaChip,
  EmptyPanel,
  RankList,
  REGISTRY_COLORS,
  RegistryCard,
  RegistryDonut,
  RegistryStat,
  formatCompact,
  formatFull,
} from "@/components/registry/registry-ui"
import {
  RegistryFilters,
  buildTrend,
  monthLabel,
  toNumber,
  useRegistryTrend,
} from "@/components/registry/registry-data"

const CHART_NAMES = [
  "cropKpis",
  "cropAreaByCrop",
  "cropAreaByRegion",
  "cropTopWoredas",
  "landTenureSplit",
  "registryTrendByMonth",
]

// Module scope keeps the reference stable so the map's drill-down effect doesn't loop.
const CROP_CHILD_CHARTS = {
  zones: "cropAreaByZone",
  woredas: "cropAreaByWoreda",
  kebeles: "cropAreaByKebele",
}

const TENURE_COLORS: Record<string, string> = {
  Owner: BRIGHT.green,
  Rented: BRIGHT.amber,
  Shared: BRIGHT.tealSoft,
  Unknown: "#9CA3AF",
}

export function CropSownDashboard({
  filters,
  geoJsonData,
  onMapFilterChange,
}: {
  filters: RegistryFilters
  geoJsonData?: any
  onMapFilterChange?: (filters: Record<string, string>) => void
}) {
  const { data, loading, error } = useChartGroupData(CHART_NAMES, filters as any)
  const charts = data?.data || {}

  const kpis = charts.cropKpis?.[0] || null
  const totalArea = toNumber(kpis?.total_area)
  const ownedArea = toNumber(kpis?.owned_area)
  const farmers = toNumber(kpis?.farmers)
  const cropTypes = toNumber(kpis?.crop_types)
  const avgPlotSize = toNumber(kpis?.avg_plot_size)
  const woredasReporting = toNumber(kpis?.woredas_reporting)
  const ownedShare = totalArea > 0 ? (ownedArea / totalArea) * 100 : 0

  const trend = useRegistryTrend(charts.registryTrendByMonth)

  // Panels are height-capped in the band grid, so the longest tails are trimmed
  // rather than allowed to overflow their card.
  const areaByCrop = useMemo(
    () =>
      (charts.cropAreaByCrop || []).slice(0, 10).map((row: any) => ({
        name: row.crop,
        value: toNumber(row.area),
      })),
    [charts.cropAreaByCrop]
  )

  const areaByRegion = useMemo(
    () =>
      (charts.cropAreaByRegion || []).map((row: any) => ({
        region: row.region,
        region_code: row.region_code,
        farmers: toNumber(row.farmers),
      })),
    [charts.cropAreaByRegion]
  )

  const topWoredas = useMemo(
    () =>
      (charts.cropTopWoredas || []).slice(0, 8).map((row: any) => ({
        name: row.woreda,
        value: toNumber(row.area),
      })),
    [charts.cropTopWoredas]
  )

  const tenureSegments = useMemo(
    () =>
      (charts.landTenureSplit || [])
        .map((row: any) => ({
          name: row.ownership_type,
          value: toNumber(row.parcels),
          color: TENURE_COLORS[row.ownership_type] || BRIGHT.violet,
          sub: `${formatCompact(toNumber(row.area))} ha`,
        }))
        .filter((segment: { value: number }) => segment.value > 0),
    [charts.landTenureSplit]
  )

  const tenureParcels = tenureSegments.reduce((acc: number, segment: { value: number }) => acc + segment.value, 0)

  // The seeded registry runs to the end of 2025, so anchor on the newest month
  // that actually has rows rather than on today's date.
  const recentMonths = useMemo(() => trend.series.slice(-12), [trend.series])

  const timeChartData = useMemo(
    () =>
      recentMonths.map((point) => ({
        period: monthLabel(point.period),
        registered: Math.round(point.totalArea),
        owned: Math.round(point.ownedArea),
      })),
    [recentMonths]
  )

  const areaTrend = buildTrend(trend.series, "totalArea", { cumulative: true })
  const farmerTrend = buildTrend(trend.series, "farmers", { cumulative: true })
  const plotTrend = buildTrend(trend.series, "avgArea")

  if (error) {
    return (
      <RegistryCard title="Crop Sown Registry">
        <div className="px-4 pb-5 pt-3 text-[16.5px]" style={{ color: REGISTRY_COLORS.red }}>
          Failed to load registry data: {error}
        </div>
      </RegistryCard>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 @[860px]:grid @[860px]:grid-rows-[auto_auto_minmax(0,1.32fr)_minmax(0,1fr)_auto]">
      {/* Title line */}
      <header className="flex flex-none flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <h2 className="text-[22px] font-bold leading-tight tracking-[-0.3px]" style={{ color: REGISTRY_COLORS.ink }}>
          Crop Sown Registry
        </h2>
        <p className="text-[17px]" style={{ color: REGISTRY_COLORS.muted }}>
          National Crop Sown Registry Module
        </p>
      </header>

      {/* Band 1 — KPI ribbon */}
      <section className="grid flex-none grid-cols-2 gap-3 @[640px]:grid-cols-3 @[860px]:grid-cols-[1.07fr_1.08fr_0.82fr_1.04fr_0.94fr_1.05fr]">
        <RegistryStat
          icon={<Sprout className="h-9 w-9" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.green}
          iconColor={BRIGHT.green}
          tint="green"
          value={formatCompact(totalArea)}
          unit="ha"
          label="Hectares Sown"
          delta={areaTrend.delta}
          loading={loading}
        />
        <RegistryStat
          icon={<Users className="h-9 w-9" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.blue}
          iconColor={BRIGHT.blue}
          tint="blue"
          value={formatFull(farmers)}
          label="Farmers Reporting"
          delta={farmerTrend.delta}
          loading={loading}
        />
        <RegistryStat
          icon={<Wheat className="h-9 w-9" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.orange}
          iconColor={BRIGHT.orange}
          tint="peach"
          value={formatFull(cropTypes)}
          label="Crop Types"
          note="commodities"
          loading={loading}
        />
        <RegistryStat
          icon={<Ruler className="h-9 w-9" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.violet}
          iconColor={BRIGHT.violet}
          tint="violet"
          value={avgPlotSize.toFixed(2)}
          unit="ha"
          label="Avg. Plot Size"
          delta={plotTrend.delta}
          loading={loading}
        />
        <RegistryStat
          icon={<Sprout className="h-9 w-9" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.teal}
          iconColor={BRIGHT.teal}
          tint="teal"
          value={`${ownedShare.toFixed(1)}%`}
          label="Land Owned"
          note={`${formatCompact(ownedArea)} ha`}
          loading={loading}
        />
        <RegistryStat
          icon={<MapPinned className="h-9 w-9" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.amber}
          iconColor={BRIGHT.amber}
          tint="amber"
          value={formatFull(woredasReporting)}
          label="Woredas Reporting"
          note="with sown land"
          loading={loading}
        />
      </section>

      {/* Band 2 — map, crop mix, tenure */}
      <section className="grid min-h-0 flex-none grid-cols-1 gap-3 @[720px]:grid-cols-2 @[860px]:grid-cols-[2.3fr_1.6fr_2fr]">
        <RegistryCard
          dense
          title="Hectares Sown by Region"
          subtitle={
            loading
              ? "Loading coverage…"
              : `${formatFull(woredasReporting)} woreda${woredasReporting === 1 ? "" : "s"} reporting · click to drill down`
          }
          className="flex min-h-[260px] flex-col overflow-hidden @[860px]:min-h-0"
          bodyClassName="relative min-h-0 flex-1"
        >
          <MapWhenVisible
            fill
            legendPosition="overlay"
            className="absolute inset-0 flex flex-col"
            minHeight="100%"
            variant="registry"
            popOutTitle="Hectares Sown by Region"
            valueLabel="hectares"
            valueFormatter={(value: number) => formatCompact(value)}
            childChartKeys={CROP_CHILD_CHARTS}
            currentFilters={{
              region: filters.region !== "all" ? filters.region : undefined,
              zone: filters.zone !== "all" ? filters.zone : undefined,
              woreda: filters.woreda !== "all" ? filters.woreda : undefined,
            }}
            onFilterChange={(mapFilters: any) => onMapFilterChange?.(mapFilters)}
            farmerData={areaByRegion}
            geoJsonData={geoJsonData}
          />
        </RegistryCard>

        <RegistryCard
          dense
          title="Area Sown by Crop"
          subtitle="Leading commodities by hectares"
          className="flex min-h-[220px] flex-col overflow-hidden @[860px]:min-h-0"
          bodyClassName="flex min-h-0 flex-1 flex-col"
        >
          <BarList dense items={areaByCrop} unitLabel="Hectares" />
        </RegistryCard>

        <RegistryCard
          dense
          title="Land Tenure of Sown Plots"
          subtitle="Parcels by ownership type"
          className="flex min-h-[220px] flex-col overflow-hidden @[860px]:min-h-0"
          bodyClassName="flex min-h-0 flex-1 items-center"
        >
          <RegistryDonut
            ringSize={260}
            className="w-full"
            segments={tenureSegments}
            centerValue={formatCompact(tenureParcels)}
            centerLabel="Parcels"
            totalLabel="Total"
            totalValue={`${formatFull(tenureParcels)} parcels`}
          />
        </RegistryCard>
      </section>

      {/* Band 3 — top woredas, monthly area */}
      <section className="grid min-h-0 flex-none grid-cols-1 gap-3 @[860px]:grid-cols-[2fr_3.9fr]">
        <RegistryCard
          dense
          title="Top Producing Woredas"
          className="flex min-h-[200px] flex-col overflow-hidden @[860px]:min-h-0"
          bodyClassName="flex min-h-0 flex-1 flex-col"
        >
          <RankList dense items={topWoredas} nameHeader="Woreda" valueHeader="Hectares" />
        </RegistryCard>

        <RegistryCard
          dense
          title="Registered vs Owned Area by Month"
          subtitle={
            recentMonths.length
              ? `${monthLabel(recentMonths[0].period)} – ${monthLabel(recentMonths[recentMonths.length - 1].period)}`
              : undefined
          }
          actions={areaTrend.delta ? <DeltaChip delta={areaTrend.delta} /> : undefined}
          className="flex min-h-[220px] flex-col overflow-hidden @[860px]:min-h-0"
          bodyClassName="min-h-0 flex-1 px-1 pb-1 pt-1"
        >
          {timeChartData.length === 0 ? (
            <EmptyPanel message="No registrations in range" className="px-3 pb-3" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeChartData} margin={{ top: 4, right: 10, left: 0, bottom: 0 }} barGap={3}>
                <CartesianGrid vertical={false} stroke={REGISTRY_COLORS.line2} />
                <XAxis
                  dataKey="period"
                  tickLine={false}
                  axisLine={false}
                  interval="preserveStartEnd"
                  minTickGap={20}
                  tick={{ fontSize: 9.5, fill: REGISTRY_COLORS.muted }}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  width={34}
                  tick={{ fontSize: 9.5, fill: REGISTRY_COLORS.muted }}
                  tickFormatter={(value: number) => formatCompact(value)}
                />
                <Tooltip
                  cursor={{ fill: REGISTRY_COLORS.g50 }}
                  contentStyle={{
                    borderRadius: 10,
                    border: `1px solid ${REGISTRY_COLORS.line}`,
                    fontSize: 11,
                  }}
                  formatter={(value: any, name: any) => [`${formatFull(toNumber(value))} ha`, String(name)]}
                />
                <Legend
                  align="right"
                  verticalAlign="top"
                  height={18}
                  iconType="circle"
                  iconSize={7}
                  wrapperStyle={{ fontSize: 10, color: REGISTRY_COLORS.ink2 }}
                />
                <Bar dataKey="registered" name="Registered Area (ha)" fill={BRIGHT.blue} radius={[2, 2, 0, 0]} />
                <Bar dataKey="owned" name="Owned Area (ha)" fill={BRIGHT.amber} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </RegistryCard>
      </section>

      {/* Source ribbon */}
      <div
        className="flex flex-none items-center gap-2 rounded-xl border bg-white px-4 py-1 text-[14.5px]"
        style={{ borderColor: REGISTRY_COLORS.line, color: REGISTRY_COLORS.muted }}
      >
        <Sprout className="h-3.5 w-3.5 flex-none" style={{ color: BRIGHT.green }} />
        <span className="min-w-0 flex-1 truncate">
          Boundaries: geoBoundaries gbOpen ETH ADM1/ADM3 (CC BY 4.0). Figures reflect registered farmer profiles for the
          selected filters.
        </span>
      </div>
    </div>
  )
}
