#!/usr/bin/env python3
"""Generate a bulk demo dataset for the Crop Sown Registry.

Produces `40_bulk_records.sql`: 500 crop sown records and their seven crop
lines, drawn from the lookup values actually seeded in the registry, so every
value resolves to a display name in the UI.

Coverage is deliberate, not random:
  * every REGION appears, with a zone/woreda/kebele that really belongs to it;
  * every SEED_VARIETY is used at least once (902 varieties over 1500 line
    slots);
  * crops, varieties, pests, weeds, agro-chemicals, machinery, land-prep
    methods, infestation types and cluster statuses are dealt round-robin, so
    each list is exhausted before repeating.

Inputs are exported from the running database (see the two psql commands in the
accompanying shell step) so the generator never invents an id:

    lookups.json   value_ids per attribute, plus the geo hierarchy
    columns.json   the real column list per table

Deterministic: a fixed RNG seed means re-running produces byte-identical SQL.

Usage:  python3 generate_bulk.py <lookups.json> <columns.json> <out.sql> [count]
"""

import json
import random
import sys
from datetime import date, timedelta

SEED = 20260415
COUNT = int(sys.argv[4]) if len(sys.argv) > 4 else 500
PRODUCTION_YEAR = "2026"
# Start above the hand-written demo records so functional ids never collide.
ID_OFFSET = 1000

lookups = json.load(open(sys.argv[1]))
columns = json.load(open(sys.argv[2]))
out_path = sys.argv[3]

rng = random.Random(SEED)
L = lookups["lists"]

# ── Geography: keep the hierarchy real ──────────────────────────────────────
geo = lookups["geo"]
by_attr = {"REGION": [], "ZONE": [], "WOREDA": [], "KEBELE": []}
children = {}
for row in geo:
    by_attr[row["attr"]].append(row)
    children.setdefault(row["parent"], []).append(row)

regions = sorted(by_attr["REGION"], key=lambda r: r["id"])


def descend(region):
    """Pick a zone -> woreda -> kebele chain that really hangs off this region.

    MDM is sparse in places: one zone has no woredas and 255 woredas have no
    kebeles. Prefer branches that reach a kebele so records do not end up with a
    half-empty address; fall back to the deepest available branch only when a
    region genuinely has nothing deeper.
    """
    zones = children.get(region["id"], [])
    full_zones = [z for z in zones
                  if any(children.get(w["id"]) for w in children.get(z["id"], []))]
    zone = rng.choice(full_zones or zones) if zones else None
    if zone is None:
        return None, None, None

    woredas = children.get(zone["id"], [])
    full_woredas = [w for w in woredas if children.get(w["id"])]
    woreda = rng.choice(full_woredas or woredas) if woredas else None
    if woreda is None:
        return zone, None, None

    kebeles = children.get(woreda["id"], [])
    return zone, woreda, (rng.choice(kebeles) if kebeles else None)


class Cycle:
    """Deal values round-robin so a list is exhausted before repeating."""

    def __init__(self, values):
        self.values = list(values)
        self.i = 0

    def next(self):
        if not self.values:
            return None
        v = self.values[self.i % len(self.values)]
        self.i += 1
        return v


cyc = {k: Cycle(v) for k, v in L.items()}


def q(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def row_sql(table, values):
    """Emit only the columns the table actually has, in its own order."""
    cols = [c["n"] for c in columns[table]]
    present = [c for c in cols if c in values]
    return present, "(" + ",".join(q(values[c]) for c in present) + ")"


STAMP = "2026-04-01 00:00:00"
BASE = {"record_image_document_id": None, "created_by": "bulk-seed", "created_at": STAMP,
        "last_approved_at": STAMP, "last_approved_by": "bulk-seed",
        "record_status": "ACTIVE", "record_status_reason": None}

tables = {t: [] for t in columns}
season_start = date(2026, 6, 1)


def dnum(lo, hi, places=2):
    return round(rng.uniform(lo, hi), places)


for i in range(1, COUNT + 1):
    n = i + ID_OFFSET
    region = regions[(n - 1) % len(regions)]          # every region, in turn
    zone, woreda, kebele = descend(region)

    rec = "bulk%04d" % n
    fid = "CROP/REG/%s/%05d" % (PRODUCTION_YEAR, n)
    farmer_id = "FR-%010d" % (100000 + n)
    farmer_name = "Farmer %04d" % n
    land_id = "%s/%02d/%03d/%05d" % (region["id"][-2:], (n % 12) + 1, (n % 900) + 1, n)
    land_area = dnum(0.75, 12.0)
    plot = cyc["PLOT_CATEGORY"].next()
    owner = cyc["OWNERSHIP_TYPE"].next()
    soil = cyc["SOIL_FERTILITY"].next()
    season = cyc["CROP_SEASON"].next()
    commodity = cyc["CROP_COMMODITY"].next()
    variety = cyc["CROP_VARIETY"].next()
    category = cyc["CROP_CATEGORY"].next()
    sub_kebele = "Gote %d" % ((n % 6) + 1)

    plot_block = {"land_id": land_id, "is_land_registered": True, "plot_category": plot,
                  "ownership_type": owner, "soil_fertility_type": soil,
                  "land_area": land_area, "unit": "HECTARE", "sub_kebele": sub_kebele,
                  "is_plot_not_registered": False, "sync_id": "sync-%04d" % n}
    crop_block = {"commodity": commodity, "crop_variety": variety, "crop_category": category,
                  "season": season}
    season_block = {"start_gc": season_start.isoformat(), "start_month": 6, "start_day": 1,
                    "end_gc": date(2026, 9, 30).isoformat(), "end_month": 9, "end_day": 30}

    tables["g2p_register_crop_sowns"].append({
        **BASE, "internal_record_id": rec, "functional_record_id": fid,
        "link_internal_record_id": None, "link_foundational_id": "%010d" % (2000000 + n),
        "record_name": farmer_name,
        "search_text": " ".join([fid, farmer_name, farmer_id, region["name"] or "", PRODUCTION_YEAR]),
        "farmer_uuid": "b0000000-0000-4000-8000-%012d" % n, "farmer_id": farmer_id,
        "fayda_fan_id": "%010d" % (3000000 + n), "farmer_name": farmer_name,
        "farmer_odk_ack_id": "ODK-ACK-%04d" % n,
        "region": region["id"], "zone": zone and zone["id"], "woreda": woreda and woreda["id"],
        "kebele": kebele and kebele["id"],
        "gps_coordinate": "%.4f, %.4f" % (dnum(3.4, 14.8, 4), dnum(33.0, 47.9, 4)),
        "status": cyc["APPROVAL_STATUS"].next(), "production_year": PRODUCTION_YEAR,
        "lifecycle_stage": ["DRAFT", "PENDING_PLANNING", "PLANNING_APPROVED",
                            "CULTIVATION_APPROVED", "SOWING_APPROVED",
                            "HARVESTING_APPROVED"][n % 6],
        "surveyor_name": "DA %03d" % (n % 120), "surveyor_mobile_number": "+2519%08d" % (n % 100000000),
        "supervisor_name": "Supervisor %03d" % (n % 40),
        "supervisor_mobile_number": "+2519%08d" % ((n * 7) % 100000000),
    })

    line_base = dict(BASE)
    line_base["link_internal_record_id"] = rec

    planned_area = round(min(land_area * 0.85, dnum(0.5, 9.0)), 2)
    planned_seed = dnum(15, 240, 1)
    planned_fert = dnum(25, 400, 1)

    tables["g2p_register_plannings"].append({
        **line_base, "internal_record_id": "bplan%04d" % n,
        "functional_record_id": "CROP/PLAN/%s/%05d" % (PRODUCTION_YEAR, n),
        "record_name": "%s %s" % (farmer_name, "planning"),
        "search_text": " ".join([land_id, commodity, variety, season]),
        **plot_block, **crop_block, **season_block,
        "local_name": "Local %03d" % (n % 150), "scientific_name": "Species %03d" % (n % 150),
        "cropping_system": ["MONO_CROPPING", "INTER_CROPPING", "MIXED_CROPPING", "RELAY_CROPPING"][n % 4],
        "planned_date": (season_start + timedelta(days=n % 90)).isoformat(),
        "planned_date_ec": "2018-10-%02d" % ((n % 28) + 1),
        "planned_area": planned_area, "growth_duration_days": 90 + (n % 90),
        "expected_yield": dnum(5, 90, 1),
        "seed_class": ["LOCAL", "IMPROVED"][n % 2],
        "seed_source": ["OWN_SAVED", "COOPERATIVE", "GOVERNMENT", "MARKET", "NGO"][n % 5],
        "seed_variety": cyc["SEED_VARIETY"].next(),
        "planned_seed_qty": planned_seed,
        "planned_fertilizer_type": cyc["FERTILIZER_TYPE"].next(),
        "planned_fertilizer_qty": planned_fert,
        "planned_fertilizer_sack": round(planned_fert / 50.0, 4),
        "planned_labor": 2 + (n % 25), "water_source": cyc["WATER_SOURCE"].next(),
        "cluster_status": cyc["CLUSTER_STATUS"].next(), "has_cluster_farming": n % 3 == 0,
    })

    actual_area = round(planned_area * rng.uniform(0.7, 1.0), 2)
    actual_fert = dnum(20, 380, 1)
    tables["g2p_register_cultivations"].append({
        **line_base, "internal_record_id": "bcult%04d" % n,
        "functional_record_id": "CROP/CULT/%s/%05d" % (PRODUCTION_YEAR, n),
        "record_name": "%s cultivation" % farmer_name,
        "search_text": " ".join([land_id, commodity, season]),
        **plot_block, **crop_block, **season_block,
        "cropping_system": ["MONO_CROPPING", "INTER_CROPPING", "MIXED_CROPPING", "RELAY_CROPPING"][n % 4],
        "actual_cultivation_date": (season_start + timedelta(days=(n % 80) + 5)).isoformat(),
        "actual_cultivation_date_ec": "2018-11-%02d" % ((n % 28) + 1),
        "actual_crop_area": actual_area,
        "actual_growth_duration_days": 88 + (n % 95),
        "actual_seed_class": ["LOCAL", "IMPROVED"][(n + 1) % 2],
        "actual_seed_source": ["OWN_SAVED", "COOPERATIVE", "GOVERNMENT", "MARKET", "NGO"][(n + 2) % 5],
        "seed_variety": cyc["SEED_VARIETY"].next(),
        "actual_seed_qty": dnum(12, 230, 1),
        "actual_fertilizer_type": cyc["FERTILIZER_TYPE"].next(),
        "actual_fertilizer_qty": actual_fert,
        "land_prep_method": cyc["LAND_PREP_METHOD"].next(),
        "cultivation_type": cyc["MACHINERY"].next(),
        "water_source": cyc["WATER_SOURCE"].next(),
        "remark": None if n % 4 else "Rain delayed land preparation",
        "has_cluster_farming": n % 3 == 0, "is_crop_changed": n % 11 == 0,
    })

    area_sown = round(actual_area * rng.uniform(0.85, 1.0), 2)
    tables["g2p_register_sowings"].append({
        **line_base, "internal_record_id": "bsow%04d" % n,
        "functional_record_id": "CROP/SOW/%s/%05d" % (PRODUCTION_YEAR, n),
        "record_name": "%s sowing" % farmer_name,
        "search_text": " ".join([land_id, commodity, season]),
        **plot_block, **crop_block,
        "sowing_status": ["SOWN", "PARTIALLY_SOWN", "NOT_SOWN"][n % 3],
        "sowing_date": (season_start + timedelta(days=(n % 70) + 10)).isoformat(),
        "sowing_date_ec": "2018-12-%02d" % ((n % 28) + 1),
        "area_sown": area_sown, "seed_class": ["LOCAL", "IMPROVED"][n % 2],
        "seed_variety": cyc["SEED_VARIETY"].next(),
        "actual_seed_qty": dnum(10, 220, 1),
        "fertilizer_type": cyc["FERTILIZER_TYPE"].next(), "fertilizer_qty": dnum(20, 350, 1),
        "cultivated_by": cyc["MACHINERY"].next(),
        "cluster_status": cyc["CLUSTER_STATUS"].next(),
        "has_pest_disease": n % 5 == 0,
    })

    qty_harvested = dnum(3, 120, 2)
    area_harvested = round(area_sown * rng.uniform(0.8, 1.0), 2)
    total_kg = qty_harvested * 100
    seed_used = dnum(10, 220, 1)
    fert_used = actual_fert
    tables["g2p_register_productions"].append({
        **line_base, "internal_record_id": "bprod%04d" % n,
        "functional_record_id": "CROP/PROD/%s/%05d" % (PRODUCTION_YEAR, n),
        "record_name": "%s production" % farmer_name,
        "search_text": " ".join([land_id, commodity]),
        **plot_block, **crop_block,
        "growth_stage": ["EMERGENCE", "VEGETATIVE", "FLOWERING", "MATURITY"][n % 4],
        "area_under_production": area_harvested,
        "expected_yield": dnum(5, 90, 1), "actual_yield": qty_harvested,
        "actual_sowing_date": (season_start + timedelta(days=(n % 70) + 10)).isoformat(),
        "yield_per_ha": round(total_kg / area_harvested, 4) if area_harvested else 0.0,
        "yield_performance_pct": round(rng.uniform(45, 130), 4),
        "land_utilization_rate": round(area_harvested / planned_area, 4) if planned_area else 0.0,
        "seed_productivity": round(total_kg / seed_used, 4) if seed_used else 0.0,
        "fertilizer_efficiency": round(total_kg / fert_used, 4) if fert_used else 0.0,
        "water_source": cyc["WATER_SOURCE"].next(),
        "remark": None if n % 6 else "Yield affected by late rains",
    })

    tables["g2p_register_harvests"].append({
        **line_base, "internal_record_id": "bharv%04d" % n,
        "functional_record_id": "CROP/HARV/%s/%05d" % (PRODUCTION_YEAR, n),
        "record_name": "%s harvest" % farmer_name,
        "search_text": " ".join([land_id, commodity]),
        **plot_block, "commodity": commodity,
        "crop_maturity_status": ["MATURING", "IMMATURE", "HARVESTED"][n % 3],
        "harvest_date": (date(2026, 10, 1) + timedelta(days=n % 60)).isoformat(),
        "harvest_date_ec": "2019-02-%02d" % ((n % 28) + 1),
        "area_harvested": area_harvested, "qty_harvested": qty_harvested,
        "post_harvest_loss_pct": dnum(0.5, 14.0, 2),
        "qty_stored": round(qty_harvested * 0.6, 2), "qty_sold": round(qty_harvested * 0.3, 2),
        "harvested_by": cyc["MACHINERY"].next(),
        "yield_per_ha": round(total_kg / area_harvested, 4) if area_harvested else 0.0,
    })

    tables["g2p_register_infestations"].append({
        **line_base, "internal_record_id": "binf%04d" % n,
        "functional_record_id": "PI/%s/%05d" % (PRODUCTION_YEAR, n),
        "record_name": "%s infestation" % farmer_name,
        "search_text": " ".join([land_id, commodity]),
        **plot_block, "commodity": commodity,
        "infestation_type": cyc["INFESTATION_TYPE"].next(),
        "pest_name": cyc["PEST"].next(), "weed_name": cyc["WEED"].next(),
        "disease_name": cyc["CROP_DISEASE"].next(),
        "chemical_used": cyc["AGRO_CHEMICAL"].next(),
        "growth_stage": ["EMERGENCE", "VEGETATIVE", "FLOWERING", "MATURITY"][n % 4],
        "severity_level": ["LOW", "MEDIUM", "HIGH"][n % 3],
        "estimated_damage_pct": dnum(1, 45, 2),
        "observation_date": (season_start + timedelta(days=(n % 100) + 20)).isoformat(),
        "observation_date_ec": "2019-01-%02d" % ((n % 28) + 1),
        "action_taken": "Applied recommended chemical and advised follow-up scouting",
    })

    cluster_timad = dnum(2, 40, 2)
    tables["g2p_register_clusters"].append({
        **line_base, "internal_record_id": "bclus%04d" % n,
        "functional_record_id": "CLTR/%s/%05d" % (PRODUCTION_YEAR, n),
        "record_name": "Cluster %04d" % n,
        "search_text": " ".join(["Cluster %04d" % n, commodity]),
        **plot_block, "commodity": commodity, "season": season, **season_block,
        "cluster_id": "CL-%05d" % n, "cluster_name": "Cluster %04d" % n,
        "cluster_status": cyc["CLUSTER_STATUS"].next(),
        "agro_ecological_zone": ["DEGA", "WOINA_DEGA", "KOLLA", "BEREHA"][n % 4],
        "cluster_area_timad": cluster_timad,
        "cluster_area_hectare": round(cluster_timad * 0.25, 4),
        "number_of_smallholders": 5 + (n % 60),
        "participant_farmers": 4 + (n % 55),
        "cluster_plan": dnum(1, 30, 2), "cluster_collected_land": dnum(1, 28, 2),
        "cluster_collected_quintal": dnum(5, 320, 2),
        "cluster_participant_farmers": 4 + (n % 55),
        "collected_land": dnum(1, 28, 2), "collected_quintal": dnum(5, 300, 2),
        "collected_land_quintal": dnum(5, 300, 2), "collected_by_combiner": dnum(0, 12, 2),
        "water_source": cyc["WATER_SOURCE"].next(),
        "gps_location": "%.4f, %.4f" % (dnum(3.4, 14.8, 4), dnum(33.0, 47.9, 4)),
        "is_actual": n % 2 == 0,
    })

with open(out_path, "w") as fh:
    fh.write("-- Crop Sown Registry — bulk demo dataset (generated; do not hand-edit).\n"
             "--\n"
             "-- %d crop sown records and their seven crop lines, built by\n"
             "-- generate_bulk.py from the lookup values seeded in this registry, so every\n"
             "-- coded value resolves to a display name.\n"
             "--\n"
             "-- Coverage: every region, every seed variety, and a round-robin sweep of the\n"
             "-- crop, pest, weed, agro-chemical, machinery and land-preparation catalogues.\n\n"
             % COUNT)
    for table, rows in tables.items():
        if not rows:
            continue
        cols, _ = row_sql(table, rows[0])
        fh.write('INSERT INTO "public"."%s" (\n    %s\n) VALUES\n'
                 % (table, ",".join('"%s"' % c for c in cols)))
        fh.write(",\n".join(row_sql(table, r)[1] for r in rows))
        fh.write('\nON CONFLICT ("internal_record_id") DO NOTHING;\n\n')

used = {k: min(c.i, len(c.values)) for k, c in cyc.items() if c.values}
print("rows: %d crop sown + %d line rows"
      % (len(tables["g2p_register_crop_sowns"]),
         sum(len(v) for k, v in tables.items() if k != "g2p_register_crop_sowns")))
for k in sorted(used):
    print("  %-18s %4d / %4d used" % (k, used[k], len(L[k])))
