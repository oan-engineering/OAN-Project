#!/usr/bin/env python3
"""Populate all sub-register tables (planning, cultivation, sowing, harvest, production, cluster, cultivation_cluster, infestation) for all 502 crop_sowns."""

import json
import random
import psycopg2
from datetime import date, timedelta

SEED = 20260415
rng = random.Random(SEED)
STAMP = "2026-04-01 00:00:00"
PRODUCTION_YEAR = "2026"

conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5446/cropsown")
conn.autocommit = True
cur = conn.cursor()

# Get lookup lists
cur.execute("SELECT attribute_id, value_code FROM g2p_attribute_values ORDER BY sort_order, value_code;")
lookups = {}
for attr_id, val_code in cur.fetchall():
    lookups.setdefault(attr_id, []).append(val_code)

def dnum(lo, hi, places=2):
    return round(rng.uniform(lo, hi), places)

class Cycle:
    def __init__(self, values, fallback="UNKNOWN"):
        self.values = list(values) if values else [fallback]
        self.i = 0
    def next(self):
        v = self.values[self.i % len(self.values)]
        self.i += 1
        return v

cyc = {k: Cycle(v) for k, v in lookups.items()}
# Standard fallbacks
if "PLOT_CATEGORY" not in cyc: cyc["PLOT_CATEGORY"] = Cycle(["PLOT_CATEGORY_ANNUAL_CROP", "PLOT_CATEGORY_PERENNIAL_CROP"])
if "OWNERSHIP_TYPE" not in cyc: cyc["OWNERSHIP_TYPE"] = Cycle(["OWNERSHIP_TYPE_OWNER", "OWNERSHIP_TYPE_TENANT"])
if "SOIL_FERTILITY" not in cyc: cyc["SOIL_FERTILITY"] = Cycle(["SOIL_FERTILITY_MEDIUM", "SOIL_FERTILITY_HIGH", "SOIL_FERTILITY_LOW"])
if "CROP_SEASON" not in cyc: cyc["CROP_SEASON"] = Cycle(["CROP_SEASON_MEHER", "CROP_SEASON_BELG"])
if "CROP_COMMODITY" not in cyc: cyc["CROP_COMMODITY"] = Cycle(["CROP_COMMODITY_2", "CROP_COMMODITY_1", "CROP_COMMODITY_6"])  # Bread wheat, Maize, Tef (catalogue codes)
if "CROP_VARIETY" not in cyc: cyc["CROP_VARIETY"] = Cycle(["CROP_VARIETY_ethioseed-712", "CROP_VARIETY_maize-bh660", "CROP_VARIETY_tef-quncho-dz-cr-387-ril-355"])  # Kubsa, BH660, Quncho (catalogue codes)
if "CROP_CATEGORY" not in cyc: cyc["CROP_CATEGORY"] = Cycle(["CROP_CATEGORY_1", "CROP_CATEGORY_2"])  # Cereal Crops, Pulse Crops (catalogue codes)
if "FERTILIZER_TYPE" not in cyc: cyc["FERTILIZER_TYPE"] = Cycle(["FERTILIZER_TYPE_UREA", "FERTILIZER_TYPE_NPS", "FERTILIZER_TYPE_DAP"])
if "WATER_SOURCE" not in cyc: cyc["WATER_SOURCE"] = Cycle(["WATER_SOURCE_RAINFED", "WATER_SOURCE_IRRIGATION_SCHEME", "WATER_SOURCE_WELL"])
if "LAND_PREP_METHOD" not in cyc: cyc["LAND_PREP_METHOD"] = Cycle(["LAND_PREP_METHOD_TRACTOR_DISC_MOLDBOARD_PLOUGHING", "LAND_PREP_METHOD_TRADITIONAL_MARESHA_PLOUGHING"])
if "MACHINERY" not in cyc: cyc["MACHINERY"] = Cycle(["MACHINERY_TRACTOR_PLOUGHING", "MACHINERY_OXEN_TILLAGE", "MACHINERY_POWER_TILLER"])
if "INFESTATION_TYPE" not in cyc: cyc["INFESTATION_TYPE"] = Cycle(["INFESTATION_TYPE_PEST", "INFESTATION_TYPE_WEED", "INFESTATION_TYPE_DISEASE"])
if "PEST" not in cyc: cyc["PEST"] = Cycle(["PEST_ARMYWORM", "PEST_LOCUST"])
if "WEED" not in cyc: cyc["WEED"] = Cycle(["WEED_BROADLEAF", "WEED_GRASS"])
if "CROP_DISEASE" not in cyc: cyc["CROP_DISEASE"] = Cycle(["DISEASE_RUST", "DISEASE_BLIGHT"])
if "AGRO_CHEMICAL" not in cyc: cyc["AGRO_CHEMICAL"] = Cycle(["AGRO_CHEMICAL_PESTICIDE_CYPERMETHRIN", "AGRO_CHEMICAL_PESTICIDE_2_4_D"])

# Fetch all crop_sowns
cur.execute('''
    SELECT internal_record_id, functional_record_id, record_name, region, zone, woreda, kebele, search_text 
    FROM g2p_register_crop_sowns 
    ORDER BY internal_record_id;
''')
crop_sowns = cur.fetchall()
print(f"Generating child records for {len(crop_sowns)} crop sown records...")

def get_table_cols(tbl):
    cur.execute(f'''
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = '{tbl}';
    ''')
    return {row[0]: row[1] for row in cur.fetchall()}

target_tables = [
    'g2p_register_plannings',
    'g2p_register_cultivations',
    'g2p_register_sowings',
    'g2p_register_harvests',
    'g2p_register_productions',
    'g2p_register_clusters',
    'g2p_register_cultivation_clusters',
    'g2p_register_infestations'
]
table_cols = {t: get_table_cols(t) for t in target_tables}

# Truncate existing child tables first to ensure clean state
for t in target_tables:
    cur.execute(f"TRUNCATE TABLE {t} CASCADE;")

season_start = date(2026, 6, 1)

rows_to_insert = {t: [] for t in target_tables}

for idx, (cs_id, func_id, rec_name, region, zone, woreda, kebele, search_text) in enumerate(crop_sowns, 1):
    n = idx
    farmer_name = rec_name or f"Farmer {n:04d}"
    land_id = f"LD/{region or '01'}/{n%12+1:02d}/{n%900+1:03d}/{n:05d}"
    land_area = dnum(1.0, 10.0)
    plot = cyc["PLOT_CATEGORY"].next()
    owner = cyc["OWNERSHIP_TYPE"].next()
    soil = cyc["SOIL_FERTILITY"].next()
    season = cyc["CROP_SEASON"].next()
    commodity = cyc["CROP_COMMODITY"].next()
    variety = cyc["CROP_VARIETY"].next()
    category = cyc["CROP_CATEGORY"].next()
    sub_kebele = f"Gote {(n % 6) + 1}"

    base = {
        "created_by": "bulk-seed", "created_at": STAMP,
        "last_approved_at": STAMP, "last_approved_by": "bulk-seed",
        "record_status": "ACTIVE", "record_status_reason": None,
        "link_internal_record_id": cs_id,
        "land_id": land_id, "ownership_type": owner, "soil_fertility_type": soil,
        "plot_category": plot, "land_area": land_area, "unit": "HECTARE", "sub_kebele": sub_kebele,
        "region": region, "zone": zone, "woreda": woreda, "kebele": kebele,
        "season": season, "commodity": commodity, "crop_variety": variety, "crop_category": category,
        "sync_id": f"sync-{n:04d}",
        "start_gc": season_start, "start_month": 6, "start_day": 1,
        "end_gc": date(2026, 9, 30), "end_month": 9, "end_day": 30,
        "da_name": f"DA {n%120:03d}", "da_mobile_number": f"+2519{n%100000000:08d}",
        "supervisor_name": f"Supervisor {n%40:03d}", "supervisor_mobile_number": f"+2519{(n*7)%100000000:08d}",
    }

    # 1. Planning
    planned_area = round(land_area * 0.85, 2)
    planned_fert = dnum(30, 300, 1)
    planned_seed = dnum(20, 150, 1)
    rows_to_insert["g2p_register_plannings"].append({
        **base,
        "internal_record_id": f"plan_{cs_id}",
        "functional_record_id": f"CROP/PLAN/{PRODUCTION_YEAR}/{n:05d}",
        "record_name": f"{farmer_name} Planning",
        "search_text": f"{land_id} {commodity} {variety} {season}",
        "local_name": f"Local {n%150:03d}", "scientific_name": f"Species {n%150:03d}",
        "cropping_system": ["MONO_CROPPING", "INTER_CROPPING", "MIXED_CROPPING", "RELAY_CROPPING"][n % 4],
        "planned_date": season_start + timedelta(days=n % 90),
        "planned_date_ec": f"2018-10-{(n % 28) + 1:02d}",
        "planned_area": planned_area, "growth_duration_days": 90 + (n % 90),
        "expected_yield": dnum(10, 80, 1),
        "seed_class": ["LOCAL", "IMPROVED"][n % 2],
        "seed_source": ["OWN_SAVED", "COOPERATIVE", "GOVERNMENT", "MARKET", "NGO"][n % 5],
        "seed_variety": variety,
        "planned_seed_qty": planned_seed,
        "planned_fertilizer_type": cyc["FERTILIZER_TYPE"].next(),
        "planned_fertilizer_qty": planned_fert,
        "planned_labor": 2 + (n % 25),
        "water_source": cyc["WATER_SOURCE"].next(),
        "water_source_method": "WATER_SOURCE_METHOD_GRAVITY",
        "water_source_frequency": "WATER_SOURCE_FREQUENCY_WEEKLY",
        "is_plot_not_registered": False,
        "cluster_details": [{"cluster_name": f"Cluster {n:04d}", "cluster_status": "CLUSTERED"}]
    })

    # 2. Cultivation
    actual_area = round(planned_area * 0.95, 2)
    rows_to_insert["g2p_register_cultivations"].append({
        **base,
        "internal_record_id": f"cult_{cs_id}",
        "functional_record_id": f"CROP/CULT/{PRODUCTION_YEAR}/{n:05d}",
        "record_name": f"{farmer_name} Cultivation",
        "search_text": f"{land_id} {commodity} {season}",
        "cropping_system": ["MONO_CROPPING", "INTER_CROPPING", "MIXED_CROPPING", "RELAY_CROPPING"][n % 4],
        "actual_cultivation_date": season_start + timedelta(days=(n % 80) + 5),
        "actual_cultivation_date_ec": f"2018-11-{(n % 28) + 1:02d}",
        "actual_crop_area": actual_area,
        "actual_growth_duration_days": 88 + (n % 95),
        "actual_seed_class": ["LOCAL", "IMPROVED"][(n + 1) % 2],
        "actual_seed_source": ["OWN_SAVED", "COOPERATIVE", "GOVERNMENT", "MARKET", "NGO"][(n + 2) % 5],
        "seed_variety": variety,
        "actual_seed_qty": planned_seed,
        "actual_fertilizer_type": cyc["FERTILIZER_TYPE"].next(),
        "actual_fertilizer_qty": planned_fert,
        "land_prep_method": cyc["LAND_PREP_METHOD"].next(),
        "cultivation_type": cyc["MACHINERY"].next(),
        "water_source": cyc["WATER_SOURCE"].next(),
        "water_source_method": "WATER_SOURCE_METHOD_PUMP",
        "water_source_frequency": "WATER_SOURCE_FREQUENCY_DAILY",
        "remark": "Cultivation completed on schedule",
        "is_crop_changed": False,
    })

    # 3. Sowing
    area_sown = round(actual_area * 0.98, 2)
    rows_to_insert["g2p_register_sowings"].append({
        **base,
        "internal_record_id": f"sow_{cs_id}",
        "functional_record_id": f"CROP/SOW/{PRODUCTION_YEAR}/{n:05d}",
        "record_name": f"{farmer_name} Sowing",
        "search_text": f"{land_id} {commodity} {season}",
        "sowing_status": ["FULLY_SOWN", "PARTIALLY_SOWN", "NOT_SOWN"][n % 3],
        "sowing_date": season_start + timedelta(days=(n % 70) + 10),
        "sowing_date_ec": f"2018-12-{(n % 28) + 1:02d}",
        "area_sown": area_sown,
        "fertilizer_type": cyc["FERTILIZER_TYPE"].next(),
        "fertilizer_qty": planned_fert,
        "cluster_status": ["CLUSTER_STATUS_CLUSTERED"],
        "has_pest_disease": (n % 5 == 0),
        "cluster_id": f"CL-{n:05d}",
        "cluster_name": f"Cluster {n:04d}",
        "agro_ecological_zone": "WOINA_DEGA",
        "cluster_area_hectare": round(area_sown * 4, 2),
        "cluster_season": season,
        "cluster_area_sown": area_sown,
        "cluster_has_pest_disease": False,
    })

    # 4. Harvest
    qty_harvested = dnum(10, 100, 2)
    rows_to_insert["g2p_register_harvests"].append({
        **base,
        "internal_record_id": f"harv_{cs_id}",
        "functional_record_id": f"CROP/HARV/{PRODUCTION_YEAR}/{n:05d}",
        "record_name": f"{farmer_name} Harvest",
        "search_text": f"{land_id} {commodity}",
        "crop_maturity_status": "HARVESTED",
        "harvest_date": date(2026, 10, 1) + timedelta(days=n % 60),
        "area_harvested": area_sown,
        "qty_harvested": qty_harvested,
        "post_harvest_loss_pct": dnum(1.0, 10.0, 2),
        "qty_stored": round(qty_harvested * 0.6, 2),
        "qty_sold": round(qty_harvested * 0.3, 2),
        "harvested_by": cyc["MACHINERY"].next(),
        "yield_per_ha": round((qty_harvested * 100) / area_sown, 2) if area_sown else 0.0,
        "cluster_status": ["CLUSTER_STATUS_CLUSTERED"]
    })

    # 5. Production
    rows_to_insert["g2p_register_productions"].append({
        **base,
        "internal_record_id": f"prod_{cs_id}",
        "functional_record_id": f"CROP/PROD/{PRODUCTION_YEAR}/{n:05d}",
        "record_name": f"{farmer_name} Production",
        "search_text": f"{land_id} {commodity}",
        "growth_stage": "MATURITY",
        "area_under_production": area_sown,
        "expected_yield": dnum(15, 90, 1),
        "actual_yield": qty_harvested,
        "yield_per_ha": round((qty_harvested * 100) / area_sown, 2) if area_sown else 0.0,
        "land_utilization_rate": round(area_sown / planned_area, 2) if planned_area else 1.0,
        "seed_productivity": round((qty_harvested * 100) / planned_seed, 2) if planned_seed else 1.0,
        "fertilizer_efficiency": round((qty_harvested * 100) / planned_fert, 2) if planned_fert else 1.0,
        "water_source": cyc["WATER_SOURCE"].next(),
        "remark": "Good overall yield"
    })

    # 6. Cluster
    rows_to_insert["g2p_register_clusters"].append({
        **base,
        "internal_record_id": f"clus_{cs_id}",
        "functional_record_id": f"CLTR/{PRODUCTION_YEAR}/{n:05d}",
        "record_name": f"Cluster {n:04d}",
        "search_text": f"Cluster {n:04d} {commodity}",
        "cluster_id": f"CL-{n:05d}",
        "cluster_name": f"Cluster {n:04d}",
        "agro_ecological_zone": "WOINA_DEGA",
        "cluster_area_timad": round(area_sown * 4, 2),
        "cluster_area_hectare": area_sown,
        "number_of_smallholders": 10 + (n % 50),
        "collected_land": area_sown,
        "collected_quintal": qty_harvested,
        "water_source": cyc["WATER_SOURCE"].next(),
        "water_source_method": "WATER_SOURCE_METHOD_GRAVITY",
        "water_source_frequency": "WATER_SOURCE_FREQUENCY_WEEKLY",
        "cluster_plan": area_sown * 1.2,
        "collected_by_combiner": dnum(1.0, 15.0, 2),
    })

    # 7. Cultivation Cluster
    rows_to_insert["g2p_register_cultivation_clusters"].append({
        **base,
        "internal_record_id": f"cc_{cs_id}",
        "functional_record_id": f"CULT/CLTR/{PRODUCTION_YEAR}/{n:05d}",
        "record_name": f"Cultivation Cluster {n:04d}",
        "search_text": f"Cultivation Cluster {n:04d} {commodity}",
        "cluster_id": f"CL-{n:05d}",
        "cluster_name": f"Cluster {n:04d}",
        "agro_ecological_zone": "WOINA_DEGA",
        "cluster_area_timad": round(area_sown * 4, 2),
        "cluster_area_hectare": area_sown,
        "number_of_smallholders": 10 + (n % 50),
        "collected_land": area_sown,
        "collected_quintal": qty_harvested,
        "water_source": cyc["WATER_SOURCE"].next(),
        "water_source_method": "WATER_SOURCE_METHOD_GRAVITY",
        "water_source_frequency": "WATER_SOURCE_FREQUENCY_WEEKLY",
        "cluster_plan": area_sown * 1.2,
        "collected_by_combiner": dnum(1.0, 15.0, 2),
    })

    # 8. Infestation
    rows_to_insert["g2p_register_infestations"].append({
        **base,
        "internal_record_id": f"inf_{cs_id}",
        "functional_record_id": f"PI/{PRODUCTION_YEAR}/{n:05d}",
        "record_name": f"{farmer_name} Infestation",
        "search_text": f"{land_id} {commodity}",
        "infestation_id": f"INF-{n:05d}",
        "growth_stage": "VEGETATIVE",
        "cluster_status": ["CLUSTER_STATUS_CLUSTERED"],
        "infestation_type": ["INFESTATION_TYPE_PEST"],
        "pest_name": cyc["PEST"].next(),
        "weed_name": cyc["WEED"].next(),
        "disease_name": cyc["CROP_DISEASE"].next(),
        "severity_level": ["LOW", "MEDIUM", "HIGH"][n % 3],
        "estimated_damage_pct": dnum(1.0, 30.0, 2),
        "observation_date": season_start + timedelta(days=(n % 100) + 20),
        "observation_date_ec": f"2019-01-{(n % 28) + 1:02d}",
        "action_taken": "Applied recommended pesticide and monitored plot"
    })

# Batch insert into DB
for tbl in target_tables:
    cols_dict = table_cols[tbl]
    rows = rows_to_insert[tbl]
    if not rows:
        continue
    
    # Filter keys matching valid columns
    sample_row = rows[0]
    valid_cols = [c for c in cols_dict.keys() if c in sample_row]
    col_str = ", ".join(f'"{c}"' for c in valid_cols)
    placeholders = ", ".join(["%s"] * len(valid_cols))
    
    insert_sql = f'INSERT INTO "{tbl}" ({col_str}) VALUES ({placeholders}) ON CONFLICT ("internal_record_id") DO NOTHING;'
    
    data_tuples = []
    for r in rows:
        row_vals = []
        for c in valid_cols:
            val = r.get(c)
            col_type = cols_dict[c]
            if col_type in ('json', 'jsonb') and val is not None and not isinstance(val, str):
                val = json.dumps(val)
            row_vals.append(val)
        data_tuples.append(tuple(row_vals))
    
    from psycopg2.extras import execute_batch
    execute_batch(cur, insert_sql, data_tuples, page_size=200)
    print(f"Inserted {len(data_tuples)} rows into {tbl}")

print("All child records populated successfully!")
