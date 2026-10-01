# OpenG2P Gen2 — ODK Form Creation & Import-Safe Validation Guide

This document provides a comprehensive, field-by-field specification and reference manual for creating **ODK Forms (XLSForm)** that integrate seamlessly with the **OpenG2P Gen2 Registry** (e.g., Crop Sown Registry, Livestock Registry).

By embedding correct client-side validations in ODK Collect / XLSForm, you prevent background ingestion pipeline errors (`ingest_data_worker`), eliminate manual triage, and ensure that field surveys are **100% import-safe** when transferred via the OpenG2P Connector Service into the Intake Form and Registry.

---

## 1. Why ODK Validations Matter in OpenG2P Gen2

In OpenG2P Gen2, data flows asynchronously from mobile devices to the permanent registry:

```
[ODK Collect App]
       │  (Fills survey in field)
       ▼
[ODK Central]
       │  (Connector polls OData submissions)
       ▼
[OpenG2P Connector Service]
       │  (POST /partner/ingest_data)
       ▼
[Partner API] ──► [Redis Queue] ──► [Celery Worker: ingest_data_worker]
                                           │
                                           ▼ (Validates Domain Attributes)
                                ┌──────────────────────┐
                                │ Passed Validation?   │
                                └───┬──────────────┬───┘
                               YES  │              │  NO
                                    ▼              ▼
                        [Intake Form Submissions] [FAILED Ingest Queue]
                        (Visible in Staff Portal) (Hidden / Blocked)
```

### The Ingestion Gatekeeper
The **Celery Worker** evaluates every incoming record against domain rules defined in Python service classes (such as `G2PRegisterDomainServicePlanning`, `G2PRegisterDomainServiceSowing`, `G2PRegisterDomainServiceHarvest`).

If **any** single validation rule fails:
1. An unhandled `G2PRegistryException` is raised.
2. The row in `incoming_classified_data` is marked with `ingestion_status = 'FAILED'`.
3. The submission is **NOT created** in `g2p_intake_form_submissions`.
4. Staff members cannot see or review the submission in the Staff Portal.

> [!IMPORTANT]
> **Prevention at the Source:** The ODK form must enforce all registry constraints directly on the surveyor's device so invalid values cannot be entered or submitted.

---

## 2. The 7 Core Registry Constraints & XLSForm Implementations

Every ODK form must adhere to the following 7 validation categories:

### Rule 1: Text Fields — Strict Alphabetical Only
* **Registry Rule:** Names (`farmer_name`, `da_name`, `supervisor_name`, `local_name`, `scientific_name`) must contain **only English letters and spaces**. No numbers, hyphens, periods, or symbols.
* **Registry Code:** `validate_alphabetical_name(value, field_name)` -> `^[a-zA-Z\s]+$`
* **XLSForm Definition:**
  ```csv
  type,name,label,constraint,constraint_message
  text,da_name,Development Agent Name,"regex(., '^[a-zA-Z ]+$')","Name must contain only alphabetical characters and spaces."
  text,supervisor_name,Supervisor Name,"regex(., '^[a-zA-Z ]+$')","Supervisor Name must contain only alphabetical characters and spaces."
  ```

### Rule 2: Mobile Numbers — Ethiopian Mobile Format
* **Registry Rule:** Mobile numbers must be valid Ethiopian numbers starting with `+251` or `0`, followed by `7` or `9`, followed by exactly 8 digits (10 digits total starting with 0, or 13 digits with +251).
* **Registry Code:** `validate_mobile_number(value, field_name)` -> `^(\+251[79]\d{8}|0[79]\d{8})$`
* **XLSForm Definition:**
  ```csv
  type,name,label,appearance,constraint,constraint_message
  text,da_mobile_number,DA Mobile Number,numbers,"regex(., '^(\+251[79][0-9]{8}|0[79][0-9]{8})$')","Must be a valid Ethiopian phone number (e.g. 0911234567 or +251911234567)."
  text,supervisor_mobile_number,Supervisor Mobile Number,numbers,"regex(., '^(\+251[79][0-9]{8}|0[79][0-9]{8})$')","Must be a valid Ethiopian phone number (e.g. 0911234567 or +251911234567)."
  ```

### Rule 3: Fayda FAN ID / National ID Format
* **Registry Rule:** Fayda FAN IDs are 16 digits, with or without a `FAN-` prefix.
* **XLSForm Definition:**
  ```csv
  type,name,label,constraint,constraint_message
  text,fyda_id,Farmer Fayda ID,"regex(., '^(FAN-)?[0-9]{16}$')","Fayda ID must be 16 digits (e.g. FAN-1020304050607080 or 1020304050607080)."
  ```

### Rule 4: Chronological Date Progression
* **Registry Rule:** Lifecycle activities must happen forward in time:
  $$\text{Planned Date} \le \text{Cultivation Date} \le \text{Sowing Date} < \text{Harvest Date} \le \text{Today}$$
  * `actual_cultivation_date` cannot be in the future (`<= today()`).
  * `sowing_date` cannot be in the future (`<= today()`).
  * `harvest_date` must be **strictly after** `sowing_date` (`harvest_date > sowing_date`).
  * Dates must fall within the selected season window (`start_gc .. end_gc`).
* **XLSForm Definition:**
  ```csv
  type,name,label,constraint,constraint_message
  date,planned_date,Planned Planting Date,". <= today() + 365","Planned date cannot be more than one year ahead."
  date,actual_cultivation_date,Actual Cultivation Date,". <= today()","Cultivation date cannot be in the future."
  date,sowing_date,Sowing Date,". <= today()","Sowing date cannot be in the future."
  date,harvest_date,Harvest Date,". <= today() and (. > ${sowing_date})","Harvest Date must be after Sowing Date and cannot be in the future."
  ```

### Rule 5: Cascading Area Constraints (Non-Negative & Decreasing)
* **Registry Rule:** Land area cannot expand across stages:
  $$\text{Total Land Area} \ge \text{Planned Area} \ge \text{Cultivated Area} \ge \text{Area Sown} \ge \text{Area Harvested} > 0$$
  * Individual `planned_area` cannot exceed `land_area`.
  * Cumulative planned area across crops on the same land cannot exceed `land_area`.
  * `area_sown` cannot exceed `actual_crop_area` (or `planned_area`).
  * `area_harvested` cannot exceed `area_sown`.
* **XLSForm Definition:**
  ```csv
  type,name,label,constraint,constraint_message
  decimal,planned_area,Planned Area (ha),". > 0 and . <= ${total_land_area}","Planned area must be > 0 and cannot exceed Total Land Area."
  decimal,actual_crop_area,Actual Cultivated Area (ha),". > 0 and . <= ${planned_area}","Cultivated area cannot exceed Planned Area."
  decimal,area_sown,Area Sown (ha),". > 0 and . <= ${actual_crop_area}","Area Sown cannot exceed Cultivated Area."
  decimal,area_harvested,Area Harvested (ha),". > 0 and . <= ${area_sown}","Area Harvested cannot exceed Area Sown."
  ```

### Rule 6: Disposal Quantities & Loss Percentages
* **Registry Rule:**
  * Post-harvest loss percentage must be between 0 and 100%: $0 \le \text{loss\_pct} \le 100$.
  * Disposed quantities must not exceed total harvested:
    $$\text{Quantity Stored} + \text{Quantity Sold} \le \text{Quantity Harvested}$$
* **XLSForm Definition:**
  ```csv
  type,name,label,constraint,constraint_message
  decimal,qty_harvested,Total Quantity Harvested (quintals),". >= 0","Quantity harvested cannot be negative."
  decimal,post_harvest_loss_pct,Post-Harvest Loss (%),". >= 0 and . <= 100","Loss percentage must be between 0% and 100%."
  decimal,qty_stored,Quantity Stored (quintals),". >= 0 and . <= ${qty_harvested}","Stored quantity cannot exceed total harvested."
  decimal,qty_sold,Quantity Sold (quintals),". >= 0 and (. + ${qty_stored} <= ${qty_harvested})","Total of stored and sold quantity cannot exceed harvested quantity."
  ```

### Rule 7: Cluster vs. Independent Exclusivity (Relevant Logic)
* **Registry Rule:**
  * If a farmer operates in a **Cluster**, cluster details must be populated (`cluster_harvest_date`, `cluster_area_harvested`, etc.), while independent details (`harvest_date`, `area_harvested`) must be **blank**.
  * If an ODK form leaves hidden independent fields populated with defaults (e.g. today's date), the backend erroneously validates independent rules (such as demanding an approved sowing record and `harvest_date > sowing_date`).
* **XLSForm Solution:** Use strict `relevant` bindings so fields are skipped and cleared when not applicable:
  ```csv
  type,name,label,relevant
  select_multiple cluster_status_list,cluster_status_ids,Farming Arrangement,
  begin_group,clustered_details,Cluster Farming Details,"selected(${cluster_status_ids}, 'clustered')"
  ...
  end_group,,
  begin_group,independant_details,Independent Farming Details,"selected(${cluster_status_ids}, 'independent')"
  ...
  end_group,,
  ```

---

## 3. The 4 Stage Lifecycle Sequence in OpenG2P

A common reason imports fail is submitting lifecycle stages **out of sequence** or **before prior stages are approved**.

| Stage | Form ID | Pre-requisite in Registry | What Happens if Pre-requisite is Missing |
| :--- | :--- | :--- | :--- |
| **1. Planning** | `crop_sown_registry_plan` | None (Initial registration) | Always passes if syntax and land constraints pass. |
| **2. Cultivation** | `crop_sown_registry_prep` | Planning record must exist | `Cultivation Date cannot be earlier than Planned Date`. |
| **3. Sowing** | `crop_sown_registry_sown` | **Cultivation must be APPROVED** in `g2p_register_cultivations` | `Area Sown cannot exceed Cultivation Area` or `Land ID does not match`. |
| **4. Harvesting** | `crop_sown_registry_harvest` | **Sowing must be APPROVED** in `g2p_register_sowings` | `A sowing record is required for this land before a harvest can be recorded.` |

> [!WARNING]
> **Approval Workflow Rule:** Even if a surveyor submits Sowing at 10:00 AM and Harvesting at 10:05 AM, the Harvesting import will **fail** if Staff has not yet approved the Sowing submission in the Staff Portal. For testing or automated flows, ensure prior stage submissions are approved first.

---

## 4. XLSForm Specification Recipes

### Form 1: Crop Planning (`crop_sown_registry_plan`)

#### `survey` Sheet
| type | name | label | hint | constraint | constraint_message | required |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `begin_group` | `farmer_identity` | Farmer Identity | | | | |
| `text` | `fyda_id` | Fayda FAN ID | 16 digits | `regex(., '^(FAN-)?[0-9]{16}$')` | Fayda ID must be 16 digits | yes |
| `integer` | `crop_year` | Crop Year | e.g. 2026 | `. >= 2020 and . <= 2035` | Enter a valid year between 2020 and 2035 | yes |
| `select_one seasons` | `production_season` | Production Season | | | | yes |
| `end_group` | | | | | | |
| `begin_repeat` | `planning` | Land Planning Details | Repeat for each land parcel | | | |
| `text` | `land_info_id` | Land ID | Format: RU/XX/XX/XXX/XXXXX | `regex(., '^[A-Z]{2}/[0-9]{2}/[0-9]{2}/[0-9]{3}/[0-9]{5}$')` | Enter valid Land ID format | yes |
| `decimal` | `total_land_area` | Total Land Area (ha) | Parcel size in hectares | `. > 0` | Must be greater than 0 | yes |
| `select_one seasons` | `planning_season` | Planning Season | Must match Production Season | `. = ${production_season}` | Planning Season must match Production Season | yes |
| `select_one crop_list` | `crop_name_id` | Commodity / Crop | Select crop | | | yes |
| `decimal` | `planned_crop_area` | Planned Crop Area (ha) | | `. > 0 and . <= ${total_land_area}` | Planned area cannot exceed total land area | yes |
| `date` | `planned_date` | Planned Date | Target planting date | `. <= today() + 365` | Cannot be more than 1 year ahead | yes |
| `end_repeat` | | | | | | |
| `begin_group` | `survey_personnel` | Survey Personnel | | | | |
| `text` | `surveyor_name` | DA Name | Full name of surveyor | `regex(., '^[a-zA-Z ]+$')` | Alphabetical characters only | yes |
| `text` | `surveyor_mobile_number` | DA Mobile Number | 10 digits (09/07) | `regex(., '^(\+251[79][0-9]{8}|0[79][0-9]{8})$')` | Valid Ethiopian mobile number required | yes |
| `text` | `supervisor_name` | Supervisor Name | Full name | `regex(., '^[a-zA-Z ]+$')` | Alphabetical characters only | no |
| `text` | `supervisor_mobile_number` | Supervisor Mobile Number | 10 digits (09/07) | `regex(., '^(\+251[79][0-9]{8}|0[79][0-9]{8})$')` | Valid Ethiopian mobile number required | no |
| `end_group` | | | | | | |

---

### Form 2: Cultivation & Land Prep (`crop_sown_registry_prep`)

#### `survey` Sheet Highlights
| type | name | label | constraint | constraint_message | required |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `text` | `land_info_id` | Land ID | `regex(., '^[A-Z]{2}/[0-9]{2}/[0-9]{2}/[0-9]{3}/[0-9]{5}$')` | Enter valid Land ID format | yes |
| `select_one seasons` | `season_id` | Season | `. = ${production_season}` | Season must match Production Season | yes |
| `select_one crop_list` | `crop_name_id` | Crop | | | yes |
| `date` | `actual_cultivation_date` | Actual Cultivation Date | `. <= today()` | Cultivation date cannot be in the future | yes |
| `decimal` | `actual_crop_area` | Actual Cultivated Area (ha) | `. > 0` | Area must be greater than 0 | yes |

---

### Form 3: Sowing (`crop_sown_registry_sown`)

#### `survey` Sheet Highlights
| type | name | label | relevant | constraint | constraint_message |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `text` | `land_info_id` | Land ID | | `regex(., '^[A-Z]{2}/[0-9]{2}/[0-9]{2}/[0-9]{3}/[0-9]{5}$')` | Valid Land ID |
| `select_multiple cluster_status_list` | `cluster_status_ids` | Farming Arrangement | | | |
| `begin_group` | `clustered_details` | Cluster Sowing Details | `selected(${cluster_status_ids}, 'clustered')` | | |
| `decimal` | `cluster_area_sown` | Cluster Area Sown (ha) | | `. > 0` | Must be greater than 0 |
| `end_group` | | | | | |
| `begin_group` | `independant_details` | Independent Sowing Details | `selected(${cluster_status_ids}, 'independent')` | | |
| `date` | `sowing_date` | Sowing Date | | `. <= today()` | Cannot be in future |
| `decimal` | `area_sown` | Area Sown (ha) | | `. > 0` | Must be greater than 0 |
| `select_one fert_list` | `actual_fertilizer_type_id` | Fertilizer Type | | | |
| `decimal` | `actual_fertilizer_qty` | Fertilizer Quantity (kg) | | `. >= 0` | Cannot be negative |
| `end_group` | | | | | |

---

### Form 4: Harvesting (`crop_sown_registry_harvest`)

#### `survey` Sheet (Fixing the Sowing Dependency Issue)
| type | name | label | relevant | constraint | constraint_message |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `text` | `land_info_id` | Land ID | | `regex(., '^[A-Z]{2}/[0-9]{2}/[0-9]{2}/[0-9]{3}/[0-9]{5}$')` | Valid Land ID format |
| `select_multiple cluster_status_list` | `cluster_status_ids` | Arrangement | | | |
| **Begin Group** | `clustered_details` | Cluster Harvest | `selected(${cluster_status_ids}, 'clustered')` | | |
| `select_one maturity_list` | `cluster_crop_maturity_status` | Crop Maturity | | | |
| `date` | `cluster_harvest_date` | Cluster Harvest Date | | `. <= today()` | Cannot be in future |
| `decimal` | `cluster_area_harvested` | Area Harvested (ha) | | `. > 0` | Must be greater than 0 |
| `decimal` | `cluster_qty_harvested` | Qty Harvested (qt) | | `. >= 0` | Cannot be negative |
| `decimal` | `cluster_post_harvest_loss_pct` | Post-Harvest Loss (%) | | `. >= 0 and . <= 100` | Between 0 and 100% |
| `decimal` | `cluster_qty_stored` | Qty Stored (qt) | | `. >= 0 and . <= ${cluster_qty_harvested}` | Cannot exceed harvested qty |
| `decimal` | `cluster_qty_sold` | Qty Sold (qt) | | `. >= 0 and (. + ${cluster_qty_stored} <= ${cluster_qty_harvested})` | Stored + Sold cannot exceed Harvested |
| **End Group** | | | | | |
| **Begin Group** | `independant_details` | Independent Harvest | `selected(${cluster_status_ids}, 'independent')` | | |
| `select_one maturity_list` | `independent_crop_maturity_status` | Crop Maturity | | | |
| `date` | `independent_harvest_date` | Independent Harvest Date | | `. <= today()` | Cannot be in future |
| `decimal` | `independent_area_harvested` | Area Harvested (ha) | | `. > 0` | Must be greater than 0 |
| `decimal` | `independent_qty_harvested` | Qty Harvested (qt) | | `. >= 0` | Cannot be negative |
| `decimal` | `independent_post_harvest_loss_pct`| Post-Harvest Loss (%) | | `. >= 0 and . <= 100` | Between 0 and 100% |
| `decimal` | `independent_qty_stored` | Qty Stored (qt) | | `. >= 0 and . <= ${independent_qty_harvested}` | Cannot exceed harvested qty |
| `decimal` | `independent_qty_sold` | Qty Sold (qt) | | `. >= 0 and (. + ${independent_qty_stored} <= ${independent_qty_harvested})` | Stored + Sold cannot exceed Harvested |
| **End Group** | | | | | |

---

## 5. Master Data Enum Values (`choices` Sheet)

ODK choice names (`name` column in the `choices` worksheet) must map to OpenG2P master enums:

### Season Choices (`seasons`)
| list_name | name | label | OpenG2P Database Value |
| :--- | :--- | :--- | :--- |
| `seasons` | `meher` | Meher | `CROP_SEASON_MEHER` |
| `seasons` | `belg` | Belg | `CROP_SEASON_BELG` |
| `seasons` | `bega` | Bega | `CROP_SEASON_BEGA` |

### Cluster Status Choices (`cluster_status_list`)
| list_name | name | label | OpenG2P Database Value |
| :--- | :--- | :--- | :--- |
| `cluster_status_list` | `clustered` | Clustered Farming | `CLUSTER` |
| `cluster_status_list` | `independent` | Independent Farming | `INDEPENDENT` |

### Fertilizer Choices (`fert_list`)
| list_name | name | label | OpenG2P Database Value |
| :--- | :--- | :--- | :--- |
| `fert_list` | `nps` | NPS | `FERTILIZER_TYPE_NPS` |
| `fert_list` | `npsb` | NPSB | `FERTILIZER_TYPE_NPSB` |
| `fert_list` | `urea` | UREA | `FERTILIZER_TYPE_UREA` |
| `fert_list` | `dap` | DAP | `FERTILIZER_TYPE_DAP` |
| `fert_list` | `bio_fertilizer` | Bio-Fertilizer | `FERTILIZER_TYPE_BIO_FERTILIZER` |
| `fert_list` | `manure` | Manure | `FERTILIZER_TYPE_MANURE` |
| `fert_list` | `compost` | Compost | `FERTILIZER_TYPE_COMPOST` |

### Crop Maturity Status (`maturity_list`)
| list_name | name | label | OpenG2P Database Value |
| :--- | :--- | :--- | :--- |
| `maturity_list` | `ready_for_harvest` | Ready for Harvest | `READY_FOR_HARVEST` |
| `maturity_list` | `harvested` | Harvested | `HARVESTED` |
| `maturity_list` | `partially_harvested` | Partially Harvested | `PARTIALLY_HARVESTED` |

---

## 6. Pre-Deployment Validation Checklist

Before uploading an XLSForm to ODK Central, verify each item on this checklist:

- [ ] **1. Name Regex Checked:** All surveyor, supervisor, and farmer names have constraint `regex(., '^[a-zA-Z ]+$')`.
- [ ] **2. Phone Numbers Checked:** All phone numbers have constraint `regex(., '^(\+251[79][0-9]{8}|0[79][0-9]{8})$')` with `appearance="numbers"`.
- [ ] **3. No Default Values on Hidden Dates:** Ensure `independent_harvest_date` or `sowing_date` have **NO** default values (`today()`) that get submitted when the group is irrelevant.
- [ ] **4. Disposal Arithmetic Checked:** Formula `. + ${qty_stored} <= ${qty_harvested}` is applied on `qty_sold`.
- [ ] **5. Loss Percentage Constrained:** Form limits loss to `. >= 0 and . <= 100`.
- [ ] **6. Area Hierarchy Constrained:** Child areas are constrained against parent areas (`area_sown <= actual_crop_area <= planned_area <= land_area`).
- [ ] **7. Land ID Matches:** Ensure field officers select or input the exact Land ID (`RU/XX/XX/XXX/XXXXX`) registered in earlier stages.
- [ ] **8. Prior Stage Approved:** If testing Sowing or Harvesting, confirm via the Staff Portal (`http://portal.localtest.me:3020`) that the preceding stage has been reviewed and **Approved**.

---

## 7. Troubleshooting Ingestion Failures

If an ODK submission does not show up in the Intake Form, inspect the ingestion pipeline using PostgreSQL:

```bash
docker exec cropsown-postgres-1 psql -U cropsown_user -d cropsown -c "
SELECT ingest_id, intake_form_id, transformation_status, ingestion_status, 
       ingestion_latest_error_code, classified_date_time 
FROM incoming_classified_data 
ORDER BY classified_date_time DESC 
LIMIT 5;
"
```

### Common Error Messages & Root Causes

| Error Message in `ingestion_latest_error_code` | Root Cause | How to Fix |
| :--- | :--- | :--- |
| `DA Name must contain only alphabetical characters and spaces` | Surveyor name contained numbers, hyphens, or punctuation. | Enforce `regex(., '^[a-zA-Z ]+$')` in XLSForm. |
| `DA Mobile Number must be a valid Ethiopian mobile number` | Phone number was not in format `09XXXXXXXX` or `+2519XXXXXXXX`. | Enforce `regex(., '^(\+251[79][0-9]{8}|0[79][0-9]{8})$')`. |
| `A sowing record is required for this land before a harvest can be recorded` | 1. Sowing submission is still `PENDING` approval.<br>2. Form filled as cluster-only, but template populated independent `harvest_date`. | 1. Approve Sowing in Staff Portal.<br>2. Ensure `relevant` skips independent fields. |
| `Harvest Date must be after the Sowing Date` | `harvest_date <= sowing_date` or date defaulted to submission date. | Enforce `. > ${sowing_date}` in XLSForm. |
| `Area Sown (...) cannot exceed Actual Crop Area (...)` | Sowing area is larger than cultivation area on record. | Add constraint `. <= ${actual_crop_area}` in ODK. |
| `Season '...' in ... does not match the Production Season '...'` | Season choice selected in details differed from header season. | In XLSForm, add constraint `. = ${production_season}`. |
