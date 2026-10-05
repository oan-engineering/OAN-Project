# Crop Sown Registry — Complete Validation Rules Reference

All rules extracted from the domain service source code. Use this to implement matching constraints in ODK XLSForm and the import/ingestion pipeline.

> [!IMPORTANT]
> Rules marked **🔗 Cross-stage** require data from a previous lifecycle stage in the DB. These cannot be enforced in ODK forms alone — they must be handled in the import pipeline (template + backend).

---

## 0. Shared Field-Level Validators

These apply across **ALL** stages wherever the field appears.

| # | Field | Rule | Regex / Logic | Error Message |
|---|-------|------|---------------|---------------|
| S1 | `farmer_name` | Alphabetical only | `^[a-zA-Z\s]+$` | "Farmer Name must contain only alphabetical characters and spaces" |
| S2 | `da_name` | Alphabetical only | `^[a-zA-Z\s]+$` | "DA Name must contain only alphabetical characters and spaces" |
| S3 | `supervisor_name` | Alphabetical only | `^[a-zA-Z\s]+$` | "Supervisor Name must contain only alphabetical characters and spaces" |
| S4 | `local_name` | Alphabetical only (Planning/Cultivation) | `^[a-zA-Z\s]+$` | "Local Name must contain only alphabetical characters and spaces" |
| S5 | `scientific_name` | Alphabetical only (Planning/Cultivation) | `^[a-zA-Z\s]+$` | "Scientific Name must contain only alphabetical characters and spaces" |
| S6 | `da_mobile_number` | Ethiopian mobile format | `^(\+251[79]\d{8}\|0[79]\d{8})$` | "DA Mobile Number must be a valid Ethiopian mobile number (e.g. +251911234567 or 0911234567)" |
| S7 | `supervisor_mobile_number` | Ethiopian mobile format | `^(\+251[79]\d{8}\|0[79]\d{8})$` | "Supervisor Mobile Number must be a valid Ethiopian mobile number (e.g. +251911234567 or 0911234567)" |

> [!TIP]
> **ODK Implementation**: Use `regex(., '^[a-zA-Z ]+$')` constraint for name fields and `regex(., '^(\+251[79][0-9]{8}|0[79][0-9]{8})$')` for phone fields. All these are optional — blank values are allowed and skip validation.

---

## 1. Header / Farmer Identity (`cs_intake_record` / `cs_common_intake_record`)

**Source**: [`g2p_register_domain_service_crop_sown.py`](file:///home/vilbertraj/work/OAN/gen2-livestock%20registry/cropsown-regsitry/cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services/g2p_register_domain_service_crop_sown.py)

| # | Field | Rule | Error Message |
|---|-------|------|---------------|
| H1 | `farmer_name` | Alphabetical only (see S1) | — |
| H2 | `crop_year` | Must not be in the future (`≤ current year`) | "crop_year must not be in the future" |
| H3 | `farmer_id` | Format: `FR-` + 10 digits | "farmer_id must be FR- followed by 10 digits (got '{value}')" |
| H4 | `fayda_fan_id` | Format: `FAN-` + 16 digits | "Fayda ID must be in this format: FAN-1234567890123456" |
| H5 | 🔗 `fayda_fan_id` + `production_season` | If Fayda ID already exists in DB, the season must match | "Production Season does not match registered Crop Season for Fayda ID" |
| H6 | 🔗 `fayda_fan_id` + `crop_year` | If Fayda ID already exists in DB, the year must match | "Crop Year does not match registered Crop Year for Fayda ID" |

### Approval-Time Validations (pre_approve)

| # | Rule | Error Message |
|---|------|---------------|
| H7 | 🔗 One registration per `farmer_id` per `crop_year` | "Farmer {id} already has a crop sown record for {year}" |
| H8 | 🔗 Total planned/cultivated/sown area per plot ≤ `land_area` | "Total {label} area on plot {id} is {total} ha, exceeds registered area of {area} ha" |
| H9 | 🔗 Cluster `land_id` must exist in Planning land IDs | "Land ID in Cluster Information does not match any Land ID in Crop Planning" |
| H10 | 🔗 Cultivation Cluster `land_id` must exist in Cultivation land IDs | "Land ID in Cultivation Cluster does not match any Land ID in Cultivation/Land Preparation" |
| H11 | 🔗 Sowing `land_id` must exist in Planning land IDs | "Land ID in Sowing does not match any Land ID in Crop Planning" |
| H12 | 🔗 Infestation `land_id` must exist in Sowing land IDs | "Land ID in Pest/Disease Infestation does not match any Land ID in Sowing" |
| H13 | 🔗 Harvest `land_id` must exist in Sowing or Planning land IDs | "Land ID in Harvest does not match any Land ID in Sowing or Crop Planning" |
| H14 | 🔗 Season in all child sections must match header `production_season` | "Season in {section} does not match Crop Season in Farmer Identity" |

---

## 2. Planning Stage (`cs_planning_details`)

**Source**: [`g2p_register_domain_service_planning.py`](file:///home/vilbertraj/work/OAN/gen2-livestock%20registry/cropsown-regsitry/cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services/g2p_register_domain_service_planning.py)

| # | Field | Rule | Error Message |
|---|-------|------|---------------|
| P1 | `season` | **Required**, non-blank | "Season is required in Crop Planning." |
| P2 | `commodity` | **Required**, non-blank | "Crop is required in Crop Planning." |
| P3 | `season` vs `production_season` | Must match the header's production season | "Season in Crop Planning Details does not match the Production Season specified in Farmer Identity." |
| P4 | `planned_area` | Must be > 0 when provided | "planned_area must be greater than zero when provided" |
| P5 | `planned_area` vs `land_area` | `planned_area ≤ land_area` | "Planned Crop Area ({x} ha) cannot be greater than Total Land Area ({y} ha)." |
| P6 | Cumulative `planned_area` per `land_id` | Sum of all planned areas for same land ≤ `land_area` | "Total Planned Crop Area exceeds Total Land Area." |
| P7 | `planned_date` | Year must be ≤ current year + 1 | "planned_date must not be more than one season ahead" |
| P8 | `planned_date` | Must fall within the season window (`start_gc` → `end_gc`) | "planned_date falls outside the season window on this record" |
| P9 | `commodity` + `season` + `land_id` | No duplicates within same submission | "Duplicate commodity entries for the same season and land are not allowed" |

> [!TIP]
> **ODK Implementation for P1/P2**: Make `season` and `commodity` required fields (`required=yes`). For P4, add constraint `${planned_area} > 0`. For P7, use `today()` to constrain date.

---

## 3. Cultivation / Land Preparation Stage (`cs_cultivation_details`)

**Source**: [`g2p_register_domain_service_cultivation.py`](file:///home/vilbertraj/work/OAN/gen2-livestock%20registry/cropsown-regsitry/cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services/g2p_register_domain_service_cultivation.py)

| # | Field | Rule | Error Message |
|---|-------|------|---------------|
| C1 | `season` | **Required**, non-blank | "Season is required in Cultivation / Land Preparation." |
| C2 | `commodity` | **Required**, non-blank | "Crop is required in Cultivation / Land Preparation." |
| C3 | `season` vs `production_season` | Must match the header's production season | "Season in Cultivation Details does not match the Production Season specified in Farmer Identity." |
| C4 | `actual_cultivation_date` | **Must not be in the future** (`≤ today()`) | "actual_cultivation_date must not be in the future" |
| C5 | `actual_cultivation_date` | Must fall within the season window (`start_gc` → `end_gc`) | "Cultivation Date is before/after Season Start/End Date." |
| C6 | 🔗 `actual_cultivation_date` vs Planning `planned_date` | Cultivation date ≥ planned date from Planning stage | "Cultivation Date cannot be earlier than Planned Date from Crop Planning." |

> [!TIP]
> **ODK Implementation for C4**: Use constraint `. <= today()` on the cultivation date field. For C1/C2, make them `required=yes`.

---

## 4. Sowing Stage (`cs_sowing_details`)

**Source**: [`g2p_register_domain_service_sowing.py`](file:///home/vilbertraj/work/OAN/gen2-livestock%20registry/cropsown-regsitry/cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services/g2p_register_domain_service_sowing.py)

| # | Field | Rule | Error Message |
|---|-------|------|---------------|
| SW1 | `season` vs `production_season` | Must match the header's production season | "Season in Sowing Details does not match the Production Season." |
| SW2 | `area_sown` | Must be > 0 when provided | "area_sown must be greater than zero when provided" |
| SW3 | `sowing_date` | Must fall within season window (`start_gc` → `end_gc`) | "Sowing Date is before/after Season Start/End Date." |
| SW4 | 🔗 `land_id` | Must match a `land_id` from Planning **or** Cultivation for the same Fayda ID | "Land ID in Sowing does not match any Land ID specified in Crop Planning or Cultivation for Fayda ID." |
| SW5 | 🔗 `sowing_date` vs Cultivation/Planning date | Sowing date ≥ cultivation date (or planned date if no cultivation) | "Sowing Date cannot be earlier than Cultivation Date / Planned Date." |
| SW6 | 🔗 `area_sown` vs Cultivation `actual_crop_area` | `area_sown ≤ actual_crop_area` from Cultivation stage | "Area Sown ({x} ha) cannot exceed Actual Crop Area in Cultivation ({y} ha)." |

> [!TIP]
> **ODK Implementation for SW2**: Add constraint `${area_sown} > 0`.

---

## 5. Harvesting Stage (`cs_harvest_details`)

**Source**: [`g2p_register_domain_service_harvest.py`](file:///home/vilbertraj/work/OAN/gen2-livestock%20registry/cropsown-regsitry/cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services/g2p_register_domain_service_harvest.py)

| # | Field | Rule | Error Message |
|---|-------|------|---------------|
| HV1 | `post_harvest_loss_pct` | Must be between 0 and 100 | "post_harvest_loss_pct must be between 0 and 100" |
| HV2 | `qty_stored` + `qty_sold` | Sum must not exceed `qty_harvested` | "qty_stored and qty_sold together must not exceed qty_harvested" |
| HV3 | `cluster_harvest_date` | Must fall within season window | "Cluster Harvest Date is before/after Season Start/End Date." |
| HV4 | 🔗 `land_id` | Must match a `land_id` from Sowing **or** Planning for the same Fayda ID | "Land ID in Harvest does not match any Land ID specified in Sowing or Crop Planning for Fayda ID." |
| HV5 | 🔗 `harvest_date` vs Sowing date | Harvest date must be **strictly after** sowing date | "Harvest Date must be after the Sowing Date." |
| HV6 | 🔗 Sowing record required | A sowing record must exist for this land before harvest | "A sowing record is required for this land before a harvest can be recorded." |
| HV7 | 🔗 `area_harvested` vs Sowing `area_sown` | `area_harvested ≤ area_sown` (falls back to `actual_crop_area` from Cultivation) | "Area Harvested ({x} ha) cannot exceed Area Sown in Sowing ({y} ha)." |

> [!TIP]
> **ODK Implementation for HV1**: `constraint: . >= 0 and . <= 100`. For HV2: `constraint: ${qty_stored} + ${qty_sold} <= ${qty_harvested}`.

---

## Summary: Rules Enforceable in ODK Forms vs Import Pipeline

### ✅ Can be enforced in ODK XLSForm (client-side)

| Rule IDs | What to implement |
|----------|-------------------|
| S1–S5 | `constraint: regex(., '^[a-zA-Z ]+$')` on name fields |
| S6–S7 | `constraint: regex(., '^(\+251[79][0-9]{8}\|0[79][0-9]{8})$')` on phone fields |
| H2 | `constraint: . <= year(today())` on crop_year |
| H3 | `constraint: regex(., '^FR-[0-9]{10}$')` on farmer_id |
| H4 | `constraint: regex(., '^FAN-[0-9]{16}$')` on fayda_fan_id |
| P1, P2, C1, C2 | `required: yes` on season and commodity |
| P4, SW2 | `constraint: . > 0` on area fields |
| P7 | `constraint: year(.) <= year(today()) + 1` on planned_date |
| C4 | `constraint: . <= today()` on actual_cultivation_date |
| HV1 | `constraint: . >= 0 and . <= 100` on post_harvest_loss_pct |
| HV2 | `constraint: ${qty_stored} + ${qty_sold} <= ${qty_harvested}` |

### ⚠️ Must be handled in the Jinja2 template / import pipeline

| Rule IDs | Why |
|----------|-----|
| P5, P6 | Need `land_area` from master data / farmer registry |
| P8, C5, SW3, HV3 | Need season window dates (`start_gc`, `end_gc`) from master data |
| P9 | Duplicate detection across repeat groups (can partly be done in ODK with `count()`) |

### 🔗 Require DB cross-stage validation (backend only)

| Rule IDs | Dependency |
|----------|------------|
| H5, H6 | Requires existing Fayda ID registration in DB |
| H7 | Requires checking all existing farmer registrations |
| C6 | Requires Planning `planned_date` from DB |
| SW4 | Requires Planning/Cultivation `land_id` from DB |
| SW5 | Requires Cultivation/Planning date from DB |
| SW6 | Requires Cultivation `actual_crop_area` from DB |
| HV4 | Requires Sowing/Planning `land_id` from DB |
| HV5, HV6 | Requires Sowing `sowing_date` from DB |
| HV7 | Requires Sowing `area_sown` from DB |
| H8–H14 | Approval-time cross-section checks (backend only) |
