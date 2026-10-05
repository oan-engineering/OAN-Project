# Crop Sown Registry (CSR) — End-to-End ODK Flow Guide

This document provides a comprehensive technical guide for the **end-to-end ODK data collection, ingestion, approval, and live registry flow** for the **Crop Sown Registry (CSR)**. It details every architectural hop, service API, data model, validation rule, database table, and troubleshooting procedure.

---

## 1. High-Level Architecture & Pipeline

The Crop Sown Registry uses a multi-stage lifecycle model. Field agents collect crop activities through four progressive ODK forms, which flow asynchronously through the connector, partner API, Celery worker pipeline, and approval workflow engine before landing in permanent registry tables.

```
[ODK Collect App]                  Field Agent (DA / Surveyor) on mobile device
        │
        ▼ (Auto-sync / Manual upload)
[ODK Central]                      Form Management & Submission Storage (OData API)
        │
        ▼ (OData Polling every 60s via Celery Beat)
[OpenG2P Connector Service]        Deduplicates, extracts payload, wraps in G2P envelope
        │
        ▼ (HTTP POST /partner/ingest_data?data_model=CSR_DATA_MODEL)
[Partner API Gateway]              Validates partner-id header, writes to raw tables, enqueues to Redis
        │
        ▼ (Celery Task Queue: redis://redis:6379/1)
[Celery Worker (Transformation)]   Renders csr_odk_transform.j2, performs geo-lookup, validates rules
        │
        ├── ✅ Valid ──► [g2p_intake_form_crop_sowns & Stage Sections] (Status: PENDING)
        │                         │
        │                         ▼
        │                [Staff Portal UI / AWE Approval]
        │                         │
        │                         ▼ (Approved)
        │                [process_submission_register_ingest()]
        │                         │
        │                         ▼
        │                [Permanent Registry: g2p_register_crop_sowns & Child Tables]
        │
        └── ❌ Invalid ─► [Incoming Classified Data: FAILED] (DLQ / Ingestion Error Log)
```

### Component & Network Topology

| Component | Container Name | Host URL / Port | Auth / Identity |
| :--- | :--- | :--- | :--- |
| **ODK Central** | `odk-central` | `https://odk.13.207.43.8.nip.io` | ODK Session Cookie / Bearer |
| **Connector Service** | `connector-service` | `http://localhost:8050` | Internal Service |
| **Connector UI** | `connector-ui` | `http://localhost:5173` | None (Local Admin) |
| **Partner API Gateway** | `partner-api` | `http://localhost:8002` (internal `:8000`) | Header `partner-id: crop-partner` |
| **Celery Worker** | `celery-worker` | Internal container | Redis broker (`redis://redis:6379/1`) |
| **Staff Portal UI** | `staff-ui` | `http://portal.localtest.me:3020` | Keycloak Session Cookie |
| **Staff API Gateway** | `staff-api` | `http://localhost:8000` | Keycloak Bearer Token |
| **Approval Engine (AWE)**| `awe` | `http://localhost:8000` (internal `:8000`)| Service Bearer JWT + HMAC Webhook |
| **PostgreSQL Database** | `postgres` | `localhost:5432` (`cropsown`, `master_data`)| Database Credentials |

---

## 2. Four-Stage Lifecycle & ODK Forms Design

Crop Sown Registry tracks agricultural activity across four discrete sequential stages:

```
Stage 1: Planning  ──►  Stage 2: Cultivation  ──►  Stage 3: Sowing  ──►  Stage 4: Harvesting
   (No Prerequisite)       (Requires Planning)      (Requires Cultivation)    (Requires Sowing)
```

> [!IMPORTANT]
> **Stage Dependency Enforcement:** Each stage beyond Planning requires that the preceding stage exists and has been **APPROVED** in the Staff Portal. Ingesting Stage 3 without an approved Stage 2 will result in a validation rejection (`A cultivation record is required before a sowing record`).

### Stage Breakdown

| Stage | Form Name | ODK Form ID | Data Captured |
| :---: | :--- | :--- | :--- |
| **1** | CSR – 1. Planning | `crop_sown_registry_plan` | Farmer identity (Fayda FAN ID, Owner ID), Land parcel ID, total land area, planned crop commodities, planned dates, production season. |
| **2** | CSR – 2. Cultivation & Land | `crop_sown_registry_prep` | Matching Land ID & Fayda FAN ID, actual cultivation date, actual cultivated area, soil type, irrigation source. |
| **3** | CSR – 3. Sowing | `crop_sown_registry_sown` | Farming arrangement (Cluster vs. Independent), sowing date, area sown, seed rate, fertilizer types and application quantities. |
| **4** | CSR – 4. Harvesting | `crop_sown_registry_harvest` | Harvest date, area harvested, total yield quantity, post-harvest losses, quantity stored, quantity sold. |

---

## 3. Strict Validation & Constraint Rules

The following business rules must be implemented in the ODK XLSForm definition and are strictly verified by the Celery worker during ingestion:

### 3.1 Universal Field Rules
1. **Alphabetical Names Only**: Surveyor (`da_name`), supervisor, and farmer names must contain letters and spaces only:
   ```csv
   constraint: regex(., '^[a-zA-Z ]+$')
   constraint_message: "Name must contain only alphabetical characters and spaces."
   ```
2. **Ethiopian Mobile Numbers**: Development Agent and supervisor mobile numbers must match standard Ethiopian formats:
   ```csv
   constraint: regex(., '^(\+251[79][0-9]{8}|0[79][0-9]{8})$')
   appearance: numbers
   constraint_message: "Must be a valid Ethiopian mobile number (e.g., 0911223344 or +251911223344)."
   ```
3. **Fayda National ID (FAN ID)**: 16 digits with optional `FAN-` prefix:
   ```csv
   constraint: regex(., '^(FAN-)?[0-9]{16}$')
   appearance: numbers
   constraint_message: "Fayda FAN ID must be 16 digits (e.g., 1234567890123456)."
   ```
4. **Dates Cannot Be in the Future**:
   ```csv
   constraint: . <= today()
   constraint_message: "Activity date cannot be in the future."
   ```

### 3.2 Stage Chronology & Area Cascades
1. **Date Progression**:
   $$\text{Planned Date} \le \text{Cultivation Date} \le \text{Sowing Date} < \text{Harvest Date} \le \text{Today}$$
2. **Cascading Area Constraints**:
   $$\text{Total Land Area} \ge \text{Planned Area} \ge \text{Cultivated Area} \ge \text{Area Sown} \ge \text{Area Harvested} > 0$$
   - `planned_area`: `. > 0 and . <= ${total_land_area}`
   - `actual_crop_area`: `. > 0 and . <= ${planned_area}`
   - `area_sown`: `. > 0 and . <= ${actual_crop_area}`
   - `area_harvested`: `. > 0 and . <= ${area_sown}`
3. **Disposal & Yield Arithmetic**:
   $$\text{Quantity Stored} + \text{Quantity Sold} \le \text{Total Quantity Harvested}$$
   $$\text{Post-Harvest Loss Percentage}: 0 \le \text{loss} \le 100$$
4. **Cluster vs. Independent Farming Exclusivity**:
   Use `relevant` bindings in the XLSForm so that hidden conditional fields do not emit default dates or zero values:
   ```csv
   begin_group,clustered_group,Cluster Information,"selected(${farming_mode}, 'clustered')"
   begin_group,independent_group,Independent Information,"selected(${farming_mode}, 'independent')"
   ```

---

## 4. Technical Hop-by-Hop Execution Path

### Hop 1: ODK Central → Connector Service
- **Mechanism**: Connector polling loop executed by Celery Beat / Worker.
- **Source File**: `openg2p_connector_service/transports/odk_central.py:L131-L260`
- **ODK API Call**:
  ```http
  GET /v1/projects/15/forms/crop_sown_registry_plan.svc/Submissions?$top=100&$skip=0&$orderby=__system/submissionDate asc&$filter=__system/submissionDate ge 2026-10-01T00:00:00Z
  Host: odk.13.207.43.8.nip.io
  Authorization: Bearer <odk_session_token>
  ```
  *(Repeat groups such as planned crops query their nested navigation link via `@odata.navigationLink`)*.
- **Connector DB Checkpoint**: Updates `connector.idempotency_keys` and logs checkpoint timestamp.

### Hop 2: Connector Packaging → Partner API Gateway
- **Mechanism**: Synchronous HTTP POST client with retry and Dead Letter Queue (DLQ) support.
- **Source File**: `openg2p_connector_service/services/ingestion_service.py` & `clients/partner_ingest_client.py`
- **Request**:
  ```http
  POST /partner/ingest_data?data_model=CSR_DATA_MODEL HTTP/1.1
  Host: partner-api:8000
  partner-id: crop-partner
  Content-Type: application/json

  {
    "header": {
      "message_id": "uuid:49c12345-789a-4bcd-ef01-23456789abcd",
      "sender_id": "crop-partner",
      "signature": "stub-sig",
      "signature_algorithm": "none",
      "timestamp": "2026-10-05T10:15:30.000Z"
    },
    "message": {
      "payload": {
        "register_mnemonic": "CropSown",
        "planning": [
          {
            "land_id": "RU/01/02/003/00045",
            "fayda_fan_id": "1234567890123456",
            "production_season": "meher",
            "crop_year": "2026",
            "crop_name": "maize",
            "planned_area": 1.5
          }
        ]
      }
    }
  }
  ```
- **Response**: Partner API responds within 50ms with `{"response_body": {"response_payload": {"correlation_id": "9a8b7c6d-..."}}}`.

### Hop 3: Partner API Storage & Celery Task Enqueue
- **Source File**: `core_pkg/services/g2p_ingest_service.py:L31-L108`
- **Database Operations (`cropsown` database)**:
  1. Inserts raw envelope into `g2p_incoming_raw_data`.
  2. Inserts payload into `g2p_incoming_raw_data_payload`.
  3. Pre-classifies record into `g2p_incoming_classified_data` with `transformation_status = 'PENDING'`.
  4. Publishes Celery task message to Redis broker (`redis://redis:6379/1`).

### Hop 4: Celery Worker Transformation & Intake Rows Creation
- **Source File**: `cropsown-extension/src/openg2p_registry_cropsown_extension/templates/csr_odk_transform.j2`
- **Worker Execution**:
  1. Celery task `ingest_data_transformation_worker` dequeues record.
  2. Evaluates `csr_odk_transform.j2` using Jinja2 engine.
  3. Maps crop choices (`maize` $\rightarrow$ `CROP_COMMODITY_1`), seasons (`meher` $\rightarrow$ `CROP_SEASON_MEHER`), and ownership codes (`owner` $\rightarrow$ `OWNERSHIP_TYPE_OWNER`).
  4. Creates draft submission in `g2p_intake_form_submissions` (`draft_status = 'FINAL'`, `approval_status = 'PENDING'`).
  5. Inserts parsed rows into section tables:
     - `g2p_intake_form_crop_sowns` (parent)
     - `g2p_intake_form_plannings` / `g2p_intake_form_cultivations` / `g2p_intake_form_sowings` / `g2p_intake_form_harvests` (child lines).

### Hop 5: Staff Review & Approval Workflow (AWE)
- **Source File**: `core_pkg/services/g2p_awe_integration_service.py` & `services/intake_form_data_service.py`
- **Execution**:
  1. Submission displays under **Intake Form $\rightarrow$ Crop Sown** in Staff Portal (`http://portal.localtest.me:3020`).
  2. When staff clicks **Approve** (or AWE webhook triggers final approval):
     - `intake_service.approve_submission_with_session()` executes.
     - `approval_status` transitions from `PENDING` $\rightarrow$ `APPROVED`.
     - `register_ingest_process_status` set to `PENDING`.

### Hop 6: Permanent Live Registry Commit
- **Source File**: `core_pkg/services/intake_form_data_service.py:L1040-L1132` (`process_submission_register_ingest`)
- **Execution**:
  1. Reads approved rows from `g2p_intake_form_*`.
  2. Inserts permanent records into:
     - `g2p_register_crop_sowns` (Parent subject record)
     - `g2p_register_plannings` (Stage 1 records)
     - `g2p_register_cultivations` (Stage 2 records)
     - `g2p_register_sowings` (Stage 3 records)
     - `g2p_register_harvests` (Stage 4 records)
  3. Writes audit trail snapshots into `g2p_register_history_crop_sowns`.
  4. Marks submission `register_ingest_process_status = 'PROCESSED'`.

---

## 5. Connector Pipeline Seed Configuration

Crop Sown Registry requires **4 separate pipelines** in the Connector service, one per lifecycle stage:

```sql
-- Pipeline 1: Planning
INSERT INTO connector_definitions (connector_id, name, platform, auth_type, source_config_json, target_url, target_headers, data_model_mnemonic, g2p_sender_id, g2p_register_mnemonic)
VALUES (
  'csr-pipeline-plan',
  'CSR 1. Planning',
  'odk_central',
  'odk_session',
  '{"base_url": "https://odk.13.207.43.8.nip.io", "project_id": 15, "form_id": "crop_sown_registry_plan", "resolve_nav_links": true, "strict_incremental": false}',
  'http://partner-api:8000/partner/ingest_data',
  '{"partner-id": "crop-partner", "Content-Type": "application/json"}',
  'CSR_DATA_MODEL',
  'crop-partner',
  'CropSown'
);

-- Pipeline 2: Cultivation
INSERT INTO connector_definitions (connector_id, name, platform, auth_type, source_config_json, target_url, target_headers, data_model_mnemonic, g2p_sender_id, g2p_register_mnemonic)
VALUES (
  'csr-pipeline-prep',
  'CSR 2. Cultivation',
  'odk_central',
  'odk_session',
  '{"base_url": "https://odk.13.207.43.8.nip.io", "project_id": 15, "form_id": "crop_sown_registry_prep", "resolve_nav_links": true, "strict_incremental": false}',
  'http://partner-api:8000/partner/ingest_data',
  '{"partner-id": "crop-partner", "Content-Type": "application/json"}',
  'CSR_DATA_MODEL',
  'crop-partner',
  'CropSown'
);

-- Pipeline 3: Sowing
INSERT INTO connector_definitions (connector_id, name, platform, auth_type, source_config_json, target_url, target_headers, data_model_mnemonic, g2p_sender_id, g2p_register_mnemonic)
VALUES (
  'csr-pipeline-sown',
  'CSR 3. Sowing',
  'odk_central',
  'odk_session',
  '{"base_url": "https://odk.13.207.43.8.nip.io", "project_id": 15, "form_id": "crop_sown_registry_sown", "resolve_nav_links": true, "strict_incremental": false}',
  'http://partner-api:8000/partner/ingest_data',
  '{"partner-id": "crop-partner", "Content-Type": "application/json"}',
  'CSR_DATA_MODEL',
  'crop-partner',
  'CropSown'
);

-- Pipeline 4: Harvesting
INSERT INTO connector_definitions (connector_id, name, platform, auth_type, source_config_json, target_url, target_headers, data_model_mnemonic, g2p_sender_id, g2p_register_mnemonic)
VALUES (
  'csr-pipeline-harvest',
  'CSR 4. Harvesting',
  'odk_central',
  'odk_session',
  '{"base_url": "https://odk.13.207.43.8.nip.io", "project_id": 15, "form_id": "crop_sown_registry_harvest", "resolve_nav_links": true, "strict_incremental": false}',
  'http://partner-api:8000/partner/ingest_data',
  '{"partner-id": "crop-partner", "Content-Type": "application/json"}',
  'CSR_DATA_MODEL',
  'crop-partner',
  'CropSown'
);
```

---

## 6. Database Verification & SQL Monitoring Queries

Run these commands inside the `cropsown` database container (`docker exec -it <postgres_container> psql -U postgres -d cropsown`):

### 6.1 Check Ingestion Pipeline Status
```sql
SELECT
    ingest_id,
    data_model_id,
    partner_id,
    transformation_status,
    ingestion_status,
    ingestion_latest_error_code,
    intake_form_submission_id
FROM g2p_incoming_classified_data
ORDER BY classified_date_time DESC
LIMIT 10;
```
*Healthy state: `transformation_status = 'PROCESSED'`, `ingestion_status = 'PROCESSED'`, `intake_form_submission_id` is populated.*

### 6.2 Monitor Intake Form Submissions
```sql
SELECT
    submission_id,
    application_reference,
    form_id,
    draft_status,
    approval_status,
    register_ingest_process_status,
    approved_by,
    first_created_at
FROM g2p_intake_form_submissions
ORDER BY first_created_at DESC
LIMIT 10;
```

### 6.3 Verify Permanent Live Tables
```sql
-- Total Parent Crop Sown records
SELECT count(*) AS total_live_crop_sowns FROM g2p_register_crop_sowns;

-- Count per stage table
SELECT count(*) AS plannings FROM g2p_register_plannings;
SELECT count(*) AS cultivations FROM g2p_register_cultivations;
SELECT count(*) AS sowings FROM g2p_register_sowings;
SELECT count(*) AS harvests FROM g2p_register_harvests;
```

---

## 7. Troubleshooting & Failure Modes

| Symptom / Error | Root Cause | Resolution |
| :--- | :--- | :--- |
| `A cultivation record is required before a sowing record` | Stage 2 (Cultivation) was not approved before Stage 3 was submitted. | Navigate to Staff Portal (`:3020`) and approve Stage 2. Reprocess or resubmit Stage 3. |
| `Area Sown cannot exceed Actual Crop Area` | Sowing area is greater than cultivated land area. | Correct XLSForm constraints; verify field agent input on parcel area. |
| `Season does not match the Production Season` | Section season choice differs from header season. | Enforce consistency constraint in form: `. = ${production_season}`. |
| `Harvest Date must be after the Sowing Date` | Harvest date is earlier than or equal to sowing date. | Adjust harvest date constraint: `. > ${sowing_date}`. |
| `Partner API rejected payload: [403]` | Missing or invalid `partner-id` header in Connector pipeline. | Ensure target header `partner-id: crop-partner` is set on the connector pipeline. |
| `Submissions stuck in transformation_status = PENDING` | Celery worker is offline, crashed, or Redis broker connection dropped. | Restart Celery worker container (`docker compose restart celery-worker`) and inspect worker logs. |
