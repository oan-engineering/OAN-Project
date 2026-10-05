# Crop Sown Extension

The Crop Sown domain package for the OpenG2P registry platform: SQLAlchemy
models, pydantic schemas, register domain services (validation, `search_text`
and `record_name` construction), the functional-ID generator, and the seed
metadata (register definitions/sections/UI tabs, lookup data, AWE policies, DCI
templates).

Installed into the registry-platform base images and selected at runtime by
`REGISTRY_EXTENSION_MODULE=openg2p_registry_cropsown_extension`.

## Registers

Modelled on the **CROP SOWN REGISTRY ERD UPDATED** diagram: the crop sown record
is the hub, and all seven crop lines link straight to it.

| Mnemonic | Parent | Table | ERD entity |
|---|---|---|---|
| `CropSown` | — (root) | `g2p_register_crop_sowns` | `CROP_SOWN_RECORDS` |
| `Planning` | CropSown | `g2p_register_plannings` | `CROP_PLANNING_LINES` |
| `Cultivation` | CropSown | `g2p_register_cultivations` | `CROP_CULTIVATION_LINES` |
| `Sowing` | CropSown | `g2p_register_sowings` | `CROP_SOWING_LINES` |
| `Production` | CropSown | `g2p_register_productions` | `CROP_PRODUCTION_LINES` |
| `Harvest` | CropSown | `g2p_register_harvests` | `CROP_HARVESTING_LINE` |
| `Infestation` | CropSown | `g2p_register_infestations` | `CROP_INFESTATION_INCIDENTS` |
| `Cluster` | CropSown | `g2p_register_clusters` | `CROP_CLUSTER_INFO` |

### The farmer is identified, not owned

There is **no Farmer register**. This registry is not the system of record for
farmers, and the ERD's `Farmer identification` box holds nothing but identifiers,
so those live on the crop sown record itself: `farmer_uuid`, `farmer_id`,
`fayda_fan_id` and a denormalised `farmer_name`. The Fayda FAN is also mirrored
into the platform's `link_foundational_id`, the column that exists for "this
record belongs to a person held elsewhere".

### The land is described, not registered

Land is **not** a register. A crop sown record covers exactly one plot, so the
ERD's `REGISTER_LAND` attributes sit flat on `CROP_SOWN_RECORDS` — including its
geometry, via the geo and geo-shape mixins — and are edited through the `Land`
tab's `cs_land_details` section, which writes to the crop sown record like every
other section on it.

Two identifiers survive the move:

* **`land_uuid`** is generated (`uuid4`) on the crop sown record and never typed.
  It stays the stable key every crop line references, so a plot can be renumbered
  without breaking anything pointing at it.
* **`land_id`** is the human identifier an operator reads off a certificate,
  e.g. `OR/01/02/003/00001`. It is what dedup and `record_name` use.

### Catalogs and lookups

Everything the ERD draws as a CATALOG, CACHED TABLE or LOOKUP TABLE is an
**attribute lookup** — a String column resolved against `g2p_attributes` /
`g2p_attribute_values`, seeded in `meta_data/lookup-data/`: crop, crop variety,
crop category, fertilizer type, soil fertility, season, plot category, ownership
type, approval/workflow status, land preparation method, water source,
infestation type, cluster status, machinery, pest, weed, crop disease and
agro-chemical.

REGION / ZONE / WOREDA / KEBELE are not seeded here: the platform resolves the
geo hierarchy from master-data through `G2PGeo.geo_lowest_level_value_id`.

Closed value sets the ERD leaves as plain columns stay as Python enums
(`register_domain/models/enums.py`): land size unit, cropping system, seed class,
seed source, sowing status, crop maturity status, growth stage, severity level,
agro-ecological zone and lifecycle stage.
