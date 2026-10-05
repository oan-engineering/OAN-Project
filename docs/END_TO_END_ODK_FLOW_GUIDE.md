# End-to-End ODK Data Flow Guide — Livestock & Crop Sown Registries

This document provides a comprehensive guide for the **end-to-end ODK data collection and ingestion flow** covering both the **Livestock Registry** and the **Crop Sown Registry**. It explains how data moves from the field (ODK Collect) through processing pipelines into the permanent registry, including form design rules, ingestion architecture, staff approval workflows, and troubleshooting.

---

## 1. ODK Data Flow Architecture

### 1.1 High-Level Pipeline

Both registries share the same architectural pattern for data ingestion:

```
[ODK Collect App]                    Field agent fills survey on mobile device
        │
        ▼  (Auto-sync / Manual submission)
[ODK Central]                        Centralized form management & submission storage
        │
        ▼  (OData API — polled every 60s by Celery Beat)
[OpenG2P Connector Service]          Transforms ODK submissions into OpenG2P schema
        │
        ▼  (HTTP POST /partner/ingest_data)
[Partner API]                        Authenticates partner & enqueues to Redis
        │
        ▼  (Celery task queue)
[Registry Celery Worker]             Classifies, transforms, validates, and ingests
        │
        ├── ✅ Passed → [Intake Form Submissions]  → Staff Portal (Review & Approve)
        │                                            → Permanent Registry
        │
        └── ❌ Failed → [FAILED Ingest Queue]       → Not visible in Staff Portal
```

### 1.2 Component Details

| Component | Livestock Registry | Crop Sown Registry |
| :--- | :--- | :--- |
| **Staff Portal** | `http://portal.localtest.me:3000` | `http://portal.localtest.me:3020` |
| **Partner API** | `http://localhost:8002` | `http://localhost:8002` |
| **Partner Header** | `partner-id: livestock-partner` | `partner-id: crop-partner` |
| **Connector Service** | `http://localhost:8050` | `http://localhost:8050` |
| **Connector UI** | `http://localhost:5173` | `http://localhost:5173` |
| **Data Model** | `MY_DATA_MODEL` | `CSR_DATA_MODEL` |
| **Registry Database** | `livestock` | `cropsown` |

---

## 2. ODK Forms Design & Structure

### 2.1 Livestock Registry — Single Form

The Livestock Registry uses a **single comprehensive ODK form** that captures all data in one submission:

| Section | Data Captured |
| :--- | :--- |
| **Farmer Identity** | Owner ID, Fayda FAN ID, farmer name |
| **Location** | Region, Zone, Woreda, Kebele |
| **Survey Personnel** | Surveyor name, mobile number, supervisor details |
| **Animal Details** (repeat) | Ear tag ID, species, breed, gender, weight, health status, vaccination status, registration date |
| **Health Events** (repeat) | Disease type, date onset/resolution, treatment, veterinarian, notifiable status |
| **Vaccinations** (repeat) | Vaccine type, date, next due date, batch number, administered by |
| **Vital Events** (repeat) | Birth/death events, offspring details, cause, reporting officer |
| **Breeding Events** (repeat) | Natural/AI breeding, sire/semen ID, expected calving date, outcome |

### 2.2 Crop Sown Registry — 4-Stage Lifecycle Forms

The Crop Sown Registry uses **4 separate ODK forms** corresponding to the crop lifecycle stages:

| Stage | ODK Form Name | ODK Form ID | Purpose |
| :---: | :--- | :--- | :--- |
| **1** | CSR – 1. Planning | `crop_sown_registry_plan` | Initial registration of land, farmer, and planned crops |
| **2** | CSR – 2. Cultivation & Land | `crop_sown_registry_prep` | Record actual cultivation activities and land preparation |
| **3** | CSR – 3. Sowing | `crop_sown_registry_sown` | Record sowing activities (cluster or independent) |
| **4** | CSR – 4. Harvesting | `crop_sown_registry_harvest` | Record harvest quantities, losses, and disposal |

> [!IMPORTANT]
> **Stage Dependency Rule:** Each stage after Planning requires the **previous stage to be APPROVED** in the Staff Portal before the next stage can be ingested. Submitting Stage 3 (Sowing) will fail if Stage 2 (Cultivation) has not been approved by staff.

#### Stage Dependency Chain
```
Planning (Stage 1) ──→ Cultivation (Stage 2) ──→ Sowing (Stage 3) ──→ Harvesting (Stage 4)
     │                       │                        │                       │
     └── No prereq           └── Planning must        └── Cultivation must    └── Sowing must
                                  exist                    be APPROVED             be APPROVED
```

---

## 3. ODK Form Validation Rules

### 3.1 Universal Rules (Apply to Both Registries)

#### Rule 1: Text Fields — Alphabetical Only
Names must contain only English letters and spaces:
```
constraint: regex(., '^[a-zA-Z ]+$')
```
**Applies to:** `farmer_name`, `da_name`, `supervisor_name`, `local_name`, `scientific_name`

#### Rule 2: Ethiopian Mobile Numbers
```
constraint: regex(., '^(\+251[79][0-9]{8}|0[79][0-9]{8})$')
appearance: numbers
```
**Applies to:** `da_mobile_number`, `supervisor_mobile_number`

#### Rule 3: Fayda FAN ID Format
16-digit national ID with optional `FAN-` prefix:
```
constraint: regex(., '^(FAN-)?[0-9]{16}$')
```

#### Rule 4: Dates Cannot Be in the Future
```
constraint: . <= today()
```
**Applies to:** All activity dates (cultivation, sowing, harvest, registration, health events, vaccinations)

### 3.2 Crop Sown Registry — Specific Rules

#### Rule 5: Chronological Date Progression
```
Planned Date ≤ Cultivation Date ≤ Sowing Date < Harvest Date ≤ Today
```

#### Rule 6: Cascading Area Constraints
```
Total Land Area ≥ Planned Area ≥ Cultivated Area ≥ Area Sown ≥ Area Harvested > 0
```
XLSForm constraints:
```csv
decimal,planned_area,Planned Area (ha),". > 0 and . <= ${total_land_area}","Cannot exceed total land area"
decimal,actual_crop_area,Cultivated Area (ha),". > 0 and . <= ${planned_area}","Cannot exceed planned area"
decimal,area_sown,Area Sown (ha),". > 0 and . <= ${actual_crop_area}","Cannot exceed cultivated area"
decimal,area_harvested,Area Harvested (ha),". > 0 and . <= ${area_sown}","Cannot exceed area sown"
```

#### Rule 7: Disposal Quantities
```
Quantity Stored + Quantity Sold ≤ Quantity Harvested
Post-Harvest Loss: 0% ≤ loss ≤ 100%
```

#### Rule 8: Cluster vs. Independent Exclusivity
Use `relevant` bindings to ensure cluster and independent fields are mutually exclusive:
```csv
begin_group,clustered_details,Cluster Details,"selected(${cluster_status_ids}, 'clustered')"
begin_group,independant_details,Independent Details,"selected(${cluster_status_ids}, 'independent')"
```

> [!WARNING]
> **Critical:** If independent fields are not properly hidden via `relevant`, they may submit default values (like `today()` for dates) even when the farmer operates in cluster mode. This causes backend validation failures.

### 3.3 Livestock Registry — Specific Rules

#### Animal Registration Dates
- `registration_date` cannot be in the future
- `date_of_birth` cannot be in the future

#### Health Event Treatment Uniqueness
- An animal can receive **multiple different treatments** on the same day
- Deduplication key: `(ear_tag_id, date_onset, event_type, treatment)`

#### Vaccination Auto-Fallback
If `vaccine_type` is omitted, the template auto-assigns based on species:

| Species | Default Vaccine |
| :--- | :--- |
| CATTLE | ANTHRAX_CATTLE |
| SHEEP | ANTHRAX_SHEEP |
| GOAT | ANTHRAX_GOAT |
| CAMEL | ANTHRAX_CAMEL |
| DONKEY | AHS_DONKEY |
| HORSE | AHS |
| POULTRY / CHICKEN | NEWCASTLE |

---

## 4. End-to-End Flow: Step by Step

### 4.1 Livestock Registry Flow

#### Step 1: Field Data Collection
1. Open **ODK Collect** on the mobile device
2. Fill in the livestock survey form:
   - Farmer identity (owner ID, Fayda FAN ID)
   - Location (select Region → Zone → Woreda → Kebele)
   - Animal details (one entry per animal in the repeat group)
   - Health events, vaccinations, vital events, breeding events (repeat groups per animal)
3. Submit the completed form

#### Step 2: Data Polling & Ingestion
1. **Connector Service** polls ODK Central every 60 seconds via Celery Beat
2. New submissions are fetched via OData API (with `resolve_nav_links: true` for repeat groups)
3. Submissions are POSTed to the Partner API at `/partner/ingest_data`

#### Step 3: Celery Worker Processing
1. Worker classifies the payload against `data_models` and `incoming_model_key_paths`
2. Fetches the `livestock_transform.j2` Jinja2 template from MinIO
3. Renders the OpenG2P domain structure (farmer, animals, health events, etc.)
4. Validates all domain attributes (names, dates, ear tags, etc.)
5. Creates a **Draft Intake Form Submission**

#### Step 4: Staff Review & Approval
1. Open Staff Portal at `http://portal.localtest.me:3000`
2. Navigate to **Intake Form → Livestock**
3. Click on a pending submission to review all tabs:
   - Farmer Identity, Livestock Location, Animal Details
   - Health Events, Vaccinations, Vital Events, Breedings
4. Click **Approve** to commit records to the permanent registry

#### Step 5: Permanent Registry
- Records are permanently stored in `g2p_register_livestocks` and `g2p_register_animals`

---

### 4.2 Crop Sown Registry Flow

#### Step 1: Field Data Collection (4 Stages)

**Stage 1 — Planning:**
1. Open ODK Collect → fill `CSR – 1. Planning` form
2. Enter farmer identity, Fayda FAN ID, crop year, production season
3. Add land parcels with land ID, total area, planned crops, and planned dates
4. Submit

**Stage 2 — Cultivation & Land:**
1. Open ODK Collect → fill `CSR – 2. Cultivation & Land` form
2. Enter the **same Fayda FAN ID** and land ID as Stage 1
3. Record actual cultivation date, cultivated area, crop details
4. Submit

**Stage 3 — Sowing:**
1. Open ODK Collect → fill `CSR – 3. Sowing` form
2. Select cluster or independent farming arrangement
3. Record sowing date, area sown, fertilizer details
4. Submit

**Stage 4 — Harvesting:**
1. Open ODK Collect → fill `CSR – 4. Harvesting` form
2. Select cluster or independent arrangement
3. Record harvest date, area harvested, quantities, disposal, and post-harvest loss
4. Submit

#### Step 2: Data Polling & Ingestion (Per Stage)
1. Each stage has its own **Connector Pipeline** polling the corresponding ODK form
2. Submissions flow through: Connector → Partner API → Redis → Celery Worker
3. Each stage creates a separate Intake Form Submission

#### Step 3: Staff Review & Approval (Sequential)
1. Open Staff Portal at `http://portal.localtest.me:3020`
2. Navigate to **Intake Form** → find Stage 1 (Planning) submission
3. Review and **Approve** Stage 1

> [!IMPORTANT]
> **You MUST approve Stage 1 before Stage 2 can be ingested.** Repeat this sequential approval for each stage:
> - Approve Planning → Submit & ingest Cultivation
> - Approve Cultivation → Submit & ingest Sowing
> - Approve Sowing → Submit & ingest Harvesting

#### Step 4: Permanent Registry
- Upon approval of each stage, records are committed to `g2p_register_crop_sowns`

---

## 5. Connector Pipeline Configuration

### 5.1 Livestock Registry — 1 Pipeline

| Setting | Value |
| :--- | :--- |
| Name | `Livestock Registry ODK` |
| Source Type | ODK Central |
| Base URL | `https://<odk-central-host>` |
| Project ID | `<project-id>` |
| Form ID | `<livestock-form-id>` |
| Resolve Nav Links | `true` |
| Target URL | `http://localhost:8002/partner/ingest_data` |
| Target Headers | `{"partner-id": "livestock-partner", "Content-Type": "application/json"}` |
| Data Model | `MY_DATA_MODEL` |

### 5.2 Crop Sown Registry — 4 Pipelines

| Pipeline | Form ID | Data Model |
| :--- | :--- | :--- |
| CSR 1 — Planning | `crop_sown_registry_plan` | `CSR_DATA_MODEL` |
| CSR 2 — Cultivation | `crop_sown_registry_prep` | `CSR_DATA_MODEL` |
| CSR 3 — Sowing | `crop_sown_registry_sown` | `CSR_DATA_MODEL` |
| CSR 4 — Harvesting | `crop_sown_registry_harvest` | `CSR_DATA_MODEL` |

**Common settings for all 4 pipelines:**
- **Target URL**: `http://localhost:8002/partner/ingest_data`
- **Target Headers**: `{"partner-id": "crop-partner", "Content-Type": "application/json"}`
- **Resolve Nav Links**: `true`

---

## 6. Monitoring & Verification

### 6.1 Check Ingestion Status in Database

**Livestock Registry:**
```sql
\c livestock;
SELECT ingest_id, data_model_id, transformation_status, ingestion_status, intake_form_submission_id
FROM incoming_classified_data
ORDER BY created_at DESC LIMIT 10;
```

**Crop Sown Registry:**
```sql
\c cropsown;
SELECT ingest_id, data_model_id, transformation_status, ingestion_status, intake_form_submission_id
FROM incoming_classified_data
ORDER BY created_at DESC LIMIT 10;
```

**Expected Results:**
- `transformation_status` = `PROCESSED`
- `ingestion_status` = `PROCESSED`
- `intake_form_submission_id` is populated (not NULL)

### 6.2 Check Intake Form Submissions

**Livestock:**
```sql
\c livestock;
SELECT submission_id, application_reference, form_id, draft_status, approval_status
FROM g2p_intake_form_submissions
ORDER BY first_created_at DESC;
```

**Crop Sown:**
```sql
\c cropsown;
SELECT submission_id, application_reference, form_id, draft_status, approval_status
FROM g2p_intake_form_submissions
ORDER BY first_created_at DESC;
```

### 6.3 Check Permanent Registry Records

**Livestock (after approval):**
```sql
\c livestock;
SELECT count(*) FROM g2p_register_livestocks;
SELECT count(*) FROM g2p_register_animals;
```

**Crop Sown (after approval):**
```sql
\c cropsown;
SELECT count(*) FROM g2p_register_crop_sowns;
```

### 6.4 Connector UI Monitoring

Open the Connector UI at `http://localhost:5173`:
- **Pipeline List**: See all active pipelines and their last poll time
- **Runs**: View individual polling runs, success/failure counts
- **Dead Letter Queue (DLQ)**: Inspect failed submissions

---

## 7. Troubleshooting Ingestion Failures

### 7.1 Submission Not Appearing in Staff Portal

**Step 1:** Check the `incoming_classified_data` table:
```sql
SELECT ingest_id, ingestion_status, ingestion_latest_error_code
FROM incoming_classified_data
ORDER BY classified_date_time DESC LIMIT 5;
```

**Step 2:** If `ingestion_status = 'FAILED'`, check the error code in `ingestion_latest_error_code`.

### 7.2 Common Error Messages & Solutions

| Error Message | Root Cause | Solution |
| :--- | :--- | :--- |
| `DA Name must contain only alphabetical characters` | Name contains numbers or special characters | Add `regex(., '^[a-zA-Z ]+$')` constraint to ODK form |
| `DA Mobile Number must be a valid Ethiopian mobile number` | Phone not in `09XXXXXXXX` or `+2519XXXXXXXX` format | Add phone regex constraint to ODK form |
| `A sowing record is required for this land before a harvest` | Previous stage not approved, or wrong land ID | Approve the Sowing stage first, verify land ID matches |
| `Harvest Date must be after the Sowing Date` | Harvest date ≤ sowing date, or date defaulted | Add `. > ${sowing_date}` constraint; remove default dates |
| `Area Sown cannot exceed Actual Crop Area` | Sowing area larger than cultivated area | Add `. <= ${actual_crop_area}` constraint |
| `Season does not match the Production Season` | Season choice differs from header selection | Add `. = ${production_season}` constraint |
| `registration_date cannot be in the future` | Docker runs in UTC, local time is ahead | Ensure dates are not in the future relative to UTC |
| `duplicate key error on application_reference` | Application reference collision | Increase randomness in reference format |

### 7.3 Pipeline Shows No New Submissions

1. **Verify ODK Central connectivity**: Check base URL, project ID, and credentials in the pipeline config
2. **Check Connector logs**: Look for authentication or network errors
3. **Verify Celery workers are running**: Both the connector worker and the registry worker must be active
4. **Check Redis broker**: Ensure Redis is running and accessible
5. **Manual test**: Use the Connector UI to click **Poll Now** and check the run result

---

## 8. Master Data Enum Values (ODK Choices → Registry)

### Crop Sown Registry Enums

| Choice List | ODK Name | Display Label | Registry Value |
| :--- | :--- | :--- | :--- |
| `seasons` | `meher` | Meher | `CROP_SEASON_MEHER` |
| `seasons` | `belg` | Belg | `CROP_SEASON_BELG` |
| `seasons` | `bega` | Bega | `CROP_SEASON_BEGA` |
| `cluster_status_list` | `clustered` | Clustered Farming | `CLUSTER` |
| `cluster_status_list` | `independent` | Independent Farming | `INDEPENDENT` |
| `fert_list` | `nps` | NPS | `FERTILIZER_TYPE_NPS` |
| `fert_list` | `urea` | UREA | `FERTILIZER_TYPE_UREA` |
| `fert_list` | `dap` | DAP | `FERTILIZER_TYPE_DAP` |
| `maturity_list` | `ready_for_harvest` | Ready for Harvest | `READY_FOR_HARVEST` |
| `maturity_list` | `harvested` | Harvested | `HARVESTED` |

### Livestock Registry Enums

| Choice List | ODK Name | Display Label | Registry Value |
| :--- | :--- | :--- | :--- |
| `species_list` | `cattle` | Cattle | `CATTLE` |
| `species_list` | `sheep` | Sheep | `SHEEP` |
| `species_list` | `goat` | Goat | `GOAT` |
| `species_list` | `camel` | Camel | `CAMEL` |
| `species_list` | `donkey` | Donkey | `DONKEY` |
| `species_list` | `horse` | Horse | `HORSE` |
| `species_list` | `poultry` | Poultry | `POULTRY` |
| `gender_list` | `male` | Male | `MALE` |
| `gender_list` | `female` | Female | `FEMALE` |
| `health_status_list` | `healthy` | Healthy | `HEALTHY` |
| `health_status_list` | `sick` | Sick | `SICK` |
| `breeding_type_list` | `natural` | Natural Mating | `NATURAL` |
| `breeding_type_list` | `ai` | Artificial Insemination | `AI` |

---

## 9. Pre-Deployment Validation Checklist

Before uploading any XLSForm to ODK Central, verify:

- [ ] **All name fields** have `regex(., '^[a-zA-Z ]+$')` constraint
- [ ] **All phone fields** have Ethiopian phone regex and `appearance="numbers"`
- [ ] **Fayda FAN ID** has `regex(., '^(FAN-)?[0-9]{16}$')` constraint
- [ ] **No default dates** on hidden fields (especially in cluster/independent groups)
- [ ] **Area hierarchy** is enforced: area_sown ≤ cultivated_area ≤ planned_area ≤ land_area
- [ ] **Disposal arithmetic** is constrained: qty_stored + qty_sold ≤ qty_harvested
- [ ] **Loss percentage** is bounded: 0 ≤ loss_pct ≤ 100
- [ ] **Land ID format** matches: `RU/XX/XX/XXX/XXXXX`
- [ ] **Season consistency** enforced: detail season = production season
- [ ] **Cluster/independent exclusivity** uses proper `relevant` bindings
- [ ] **Prior stages are approved** before testing subsequent stages

---

## 10. Quick Reference: Complete Flow Summary

### Livestock Registry
```
ODK Collect → ODK Central → Connector (1 pipeline) → Partner API → Celery Worker
    → Intake Form Submission → Staff Approval → g2p_register_livestocks + g2p_register_animals
```

### Crop Sown Registry
```
Stage 1: ODK Planning Form → Connector Pipeline 1 → Intake → Approve
Stage 2: ODK Cultivation Form → Connector Pipeline 2 → Intake → Approve
Stage 3: ODK Sowing Form → Connector Pipeline 3 → Intake → Approve
Stage 4: ODK Harvest Form → Connector Pipeline 4 → Intake → Approve
    → All stages approved → g2p_register_crop_sowns (permanent registry)
```
