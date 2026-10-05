# Livestock Registry — End-to-End ODK Flow Guide

This document provides a comprehensive technical guide for the **end-to-end ODK data collection, ingestion, approval, and live registry flow** for the **Livestock Registry**. It details every architectural hop, service API, data model, validation rule, database table, and troubleshooting procedure.

---

## 1. High-Level Architecture & Pipeline

The Livestock Registry uses a **single comprehensive ODK form** capturing farmer identity, location, personnel, and repeat groups for individual animals and veterinary events. Data moves through the connector, partner API, Celery worker pipeline (patched with domain hooks and geo-resolution), a 4-tier hierarchical AWE approval workflow, and into permanent live tables.

```
[ODK Collect App]                  Field Agent (Veterinarian / DA) on mobile device
        │
        ▼ (Auto-sync / Manual upload)
[ODK Central]                      Form Management & Submission Storage (OData API)
        │
        ▼ (OData Polling every 60s via Celery Beat, resolve_nav_links: true)
[OpenG2P Connector Service]        Deduplicates, extracts repeat groups, wraps in G2P envelope
        │
        ▼ (HTTP POST /partner/ingest_data?data_model=MY_DATA_MODEL)
[Partner API Gateway]              Validates partner-id header, writes to raw tables, enqueues to Redis
        │
        ▼ (Celery Task Queue: redis://redis:6379/1)
[Celery Worker & Domain Hooks]     Renders ls_odk_transform.j2, master_data geo-lookup, normalizes enums
        │
        ├── ✅ Valid ──► [g2p_intake_form_livestocks & Repeat Sections] (Status: PENDING)
        │                         │
        │                         ▼
        │                [AWE 4-Level Approval Ladder]
        │                Kebele ──► Woreda ──► Zone ──► Region
        │                (Approvers resolved via /livestock/approver-resolver)
        │                         │
        │                         ▼ (Approved: Webhook /awe/webhooks/decision)
        │                [process_submission_register_ingest()]
        │                         │
        │                         ▼
        │                [Permanent Registry: g2p_register_livestocks & Child Tables]
        │
        └── ❌ Invalid ─► [Incoming Classified Data: FAILED] (DLQ / Ingestion Error Log)
```

### Component & Network Topology

| Component | Container Name | Host URL / Port | Auth / Identity |
| :--- | :--- | :--- | :--- |
| **ODK Central** | `odk-central` | `https://odk.13.207.43.8.nip.io` | ODK Session Cookie / Bearer |
| **Connector Service** | `connector-service` | `http://localhost:8050` | Internal Service |
| **Connector UI** | `connector-ui` | `http://localhost:5173` | None (Local Admin) |
| **Partner API Gateway** | `partner-api` | `http://localhost:8002` (internal `:8000`) | Header `partner-id: livestock-partner` |
| **Celery Worker** | `celery-worker` | Internal container | Redis broker (`redis://redis:6379/1`) |
| **Staff Portal UI** | `staff-ui` | `http://portal.localtest.me:3000` | Keycloak Session Cookie |
| **Staff API Gateway** | `staff-api` | `http://localhost:8000` | Keycloak Bearer Token |
| **Approval Engine (AWE)**| `awe` | `http://localhost:8000` (internal `:8000`)| Service Bearer JWT + HMAC Webhook |
| **PostgreSQL Database** | `postgres` | `localhost:5432` (`livestock`, `master_data`)| Database Credentials |

---

## 2. ODK Form Design & Structure

The Livestock Registry captures all farmer and animal data in a **single comprehensive submission** (`form_id: livestock_registry`).

### Form Sections & Repeat Groups

| Section | Type | Data Captured |
| :--- | :--- | :--- |
| **Farmer Identity** | Flat Group | Owner ID, Fayda FAN ID, Farmer Name, Gender, Date of Birth. |
| **Location** | Flat Group | Region, Zone, Woreda, Kebele administrative codes. |
| **Survey Personnel** | Flat Group | Surveyor DA name, DA mobile number, Supervisor name, Supervisor mobile number. |
| **Animal Details** | Repeat Group | Ear tag ID, species (Cattle, Sheep, Goat, etc.), breed, gender, weight, health status, vaccination status, registration date. |
| **Health Events** | Repeat Group | Linked ear tag ID, disease/event type, date onset, date resolution, treatment administered, attending veterinarian. |
| **Vaccinations** | Repeat Group | Linked ear tag ID, vaccine type, vaccination date, next due date, batch number, administered by. |
| **Vital Events** | Repeat Group | Linked ear tag ID, event type (Birth, Death), event date, offspring details, cause of death, reporting officer. |
| **Breeding Events** | Repeat Group | Linked ear tag ID, breeding method (Natural, AI), sire ID / semen straw ID, service date, expected calving date. |

---

## 3. Strict Validation & Normalization Rules

The Celery worker and `odk_ingest_hooks.py` enforce strict validation and sanitization prior to intake row creation:

### 3.1 Field Validation Rules
1. **Alphabetical Names**:
   ```csv
   constraint: regex(., '^[a-zA-Z ]+$')
   constraint_message: "Name must contain only letters and spaces."
   ```
   *Applies to:* `farmer_name`, `da_name`, `supervisor_name`, `veterinarian_name`.
2. **Ethiopian Mobile Numbers**:
   ```csv
   constraint: regex(., '^(\+251[79][0-9]{8}|0[79][0-9]{8})$')
   appearance: numbers
   constraint_message: "Must be a valid Ethiopian phone number."
   ```
3. **Fayda FAN ID**:
   ```csv
   constraint: regex(., '^(FAN-)?[0-9]{16}$')
   ```
4. **Historical Dates (No Future Dates)**:
   - `registration_date <= today()`
   - `date_of_birth <= today()`
   - `event_date <= today()`

### 3.2 Species & Breed Normalization
The ingestion pipeline normalizes ODK text values to canonical database codes:
- **Species**: `cattle` $\rightarrow$ `CATTLE`, `sheep` $\rightarrow$ `SHEEP`, `goat` $\rightarrow$ `GOAT`, `camel` $\rightarrow$ `CAMEL`, `donkey` $\rightarrow$ `DONKEY`, `horse` $\rightarrow$ `HORSE`, `poultry` $\rightarrow$ `POULTRY`.
- **Vaccine Auto-Fallback**: If `vaccine_type` is omitted in the survey, the template auto-assigns the mandatory baseline vaccine based on the animal's species:
  - `CATTLE` $\rightarrow$ `ANTHRAX_CATTLE`
  - `SHEEP` $\rightarrow$ `ANTHRAX_SHEEP`
  - `GOAT` $\rightarrow$ `ANTHRAX_GOAT`
  - `CAMEL` $\rightarrow$ `ANTHRAX_CAMEL`
  - `DONKEY` $\rightarrow$ `AHS_DONKEY`
  - `HORSE` $\rightarrow$ `AHS`
  - `POULTRY` $\rightarrow$ `NEWCASTLE`

### 3.3 Animal Count & Detail Synchronization
The worker counts entries in the `animal_details` repeat group and automatically injects:
- `total_animals = count(animal_details)` into the parent `g2p_intake_form_livestocks` record.
- Links health, vaccination, vital, and breeding event rows to the appropriate animal using the `ear_tag_id`.

---

## 4. Technical Hop-by-Hop Execution Path

### Hop 1: ODK Central → Connector Service
- **Mechanism**: Connector polling loop executed every 60 seconds.
- **Source File**: `openg2p_connector_service/transports/odk_central.py:L131-L260`
- **ODK API Call**:
  ```http
  GET /v1/projects/14/forms/livestock_registry.svc/Submissions?$top=100&$skip=0&$orderby=__system/submissionDate asc&$filter=__system/submissionDate ge 2026-10-01T00:00:00Z
  Host: odk.13.207.43.8.nip.io
  Authorization: Bearer <odk_session_token>
  ```
- **Repeat Groups Resolution**: Because `resolve_nav_links: true` is configured, the connector queries each repeat table URL (`.../Submissions('{id}')/animal_details`, `health_events`, etc.) and merges the children into the parent submission payload.

### Hop 2: Connector Packaging → Partner API Gateway
- **Mechanism**: Synchronous HTTP POST client with retry and Dead Letter Queue (DLQ).
- **Source File**: `openg2p_connector_service/services/ingestion_service.py` & `clients/partner_ingest_client.py`
- **Request**:
  ```http
  POST /partner/ingest_data?data_model=MY_DATA_MODEL HTTP/1.1
  Host: partner-api:8000
  partner-id: livestock-partner
  Content-Type: application/json

  {
    "header": {
      "message_id": "uuid:71a23456-89bc-4def-0123-456789abcdef",
      "sender_id": "livestock-partner",
      "signature": "stub-sig",
      "signature_algorithm": "none",
      "timestamp": "2026-10-05T10:20:00.000Z"
    },
    "message": {
      "payload": {
        "register_mnemonic": "Livestock",
        "farmer_name": "Derartu Tulu",
        "farmer_id": "FR-9876543210",
        "fayda_fan_id": "9876543210987654",
        "region": "region-oromia",
        "zone": "zone-arsi",
        "woreda": "woreda-bokoji",
        "kebele": "kebele-02",
        "animal_details": [
          {
            "ear_tag_id": "ET-771122",
            "species": "CATTLE",
            "breed": "BORAN",
            "gender": "FEMALE",
            "date_of_birth": "2022-04-10"
          }
        ]
      }
    }
  }
  ```
- **Response**: Partner API returns synchronous acknowledgement: `{"response_body": {"response_payload": {"correlation_id": "3b2a1c0d-..."}}}`.

### Hop 3: Partner API Storage & Celery Task Enqueue
- **Source File**: `cropsown-regsitry/core_pkg/services/g2p_ingest_service.py:L31-L108`
- **Database Operations (`livestock` database)**:
  1. Inserts raw envelope into `g2p_incoming_raw_data`.
  2. Inserts payload into `g2p_incoming_raw_data_payload`.
  3. Pre-classifies record into `g2p_incoming_classified_data` (`transformation_status = 'PENDING'`).
  4. Dispatches task to Redis queue `redis://redis:6379/1`.

### Hop 4: Celery Worker Transformation & Domain Hooks
- **Source Files**:
  - `livestock-extension/src/openg2p_registry_livestock_extension/odk_ingest_hooks.py`
  - `livestock-extension/src/openg2p_registry_livestock_extension/templates/ls_odk_transform.j2`
- **Worker Execution**:
  1. Celery task `ingest_data_transformation_worker` executes `patched_transform_json`.
  2. Evaluates `ls_odk_transform.j2` to map ODK fields to OpenG2P sections.
  3. **Geo-Resolution**: Calls `resolve_geo_label()` against `master_data.g2p_geo_level_values` to translate administrative codes (`kebele-02`) to display strings (`Bokoji 02`).
  4. **Validation**: Sanitizes enums (e.g. `event_type = 'AI'`, `location = 'HOME'`).
  5. Inserts draft submission into `g2p_intake_form_submissions` (`draft_status = 'FINAL'`, `approval_status = 'PENDING'`).
  6. Inserts child records into:
     - `g2p_intake_form_farmers`
     - `g2p_intake_form_livestocks`
     - `g2p_intake_form_animals`
     - `g2p_intake_form_health_events`
     - `g2p_intake_form_vaccinations`
     - `g2p_intake_form_vital_events`
     - `g2p_intake_form_breedings`

### Hop 5: AWE 4-Level Hierarchical Approval Workflow
- **Source Files**:
  - `awe_meta_data/10_approval_policy.sql` (`registry.intake_form.livestock`)
  - `awe_meta_data/20_approval_stage.sql` (Stages 1 to 4)
  - `awe_meta_data/30_approver_rule.sql` (HTTP approver rules)
  - `g2p_approver_resolver_controller.py` (`POST /livestock/approver-resolver`)
- **Execution Flow**:
  1. Submission triggers an AWE approval request:
     `POST http://awe:8000/v1/awe/requests`
     - Context payload: `{"submission_id": "...", "region": "Oromia", "zone": "Arsi", "woreda": "Bokoji", "kebele": "Bokoji 02"}`.
  2. **Approval Ladder Progression**:
     - **Stage 1 (Kebele)**: AWE calls `POST http://staff-api:8000/livestock/approver-resolver?level=kebele&secret=livestock-approver-resolver-secret`. Resolver queries Keycloak for users with role `Kebele Approver` assigned to `Bokoji 02`.
     - **Stage 2 (Woreda)**: Upon Kebele approval, advances to Woreda Approver for `Bokoji`.
     - **Stage 3 (Zone)**: Advances to Zone Approver for `Arsi`.
     - **Stage 4 (Region)**: Advances to Region Approver for `Oromia`.
  3. **Decision Webhook**:
     - Once Region approval completes, AWE issues an HMAC-signed webhook:
       `POST http://staff-api:8000/awe/webhooks/decision`
       Header: `X-AWE-Signature: <hmac_sha256>`
       Payload: `{"event_type": "request_approved", "artifact_id": "<submission_id>", "actor": "region.approver"}`.

### Hop 6: Permanent Live Registry Ingestion
- **Source File**: `livestock-registry/docker/staff-api/core-patches/apply_patches.py:L1200-L1242` & `cropsown-regsitry/core_pkg/services/intake_form_data_service.py`
- **Execution**:
  1. `G2PAweWebhookService` executes `approve_submission_with_session()`.
  2. Invokes `process_submission_register_ingest(submission_id)`:
     - Copies intake rows to live register tables:
       - Parent: `g2p_register_livestocks`
       - Children: `g2p_register_animals`, `g2p_register_health_events`, `g2p_register_vaccinations`, `g2p_register_vital_events`, `g2p_register_breedings`.
     - Writes immutable history snapshots to `g2p_register_history_*`.
     - Marks submission `register_ingest_process_status = 'PROCESSED'`.

---

## 5. Connector Pipeline Configuration

The Livestock Registry requires **1 comprehensive pipeline** in the Connector service:

```sql
INSERT INTO connector_definitions (
    connector_id,
    name,
    platform,
    auth_type,
    source_config_json,
    target_url,
    target_headers,
    data_model_mnemonic,
    g2p_sender_id,
    g2p_register_mnemonic
) VALUES (
    'livestock-registry-pipeline',
    'Livestock Registry ODK Pipeline',
    'odk_central',
    'odk_session',
    '{
      "base_url": "https://odk.13.207.43.8.nip.io",
      "project_id": 14,
      "form_id": "livestock_registry",
      "resolve_nav_links": true,
      "strict_incremental": false,
      "page_size": 100
    }',
    'http://partner-api:8000/partner/ingest_data',
    '{"partner-id": "livestock-partner", "Content-Type": "application/json"}',
    'MY_DATA_MODEL',
    'livestock-partner',
    'Livestock'
);
```

---

## 6. Database Verification & SQL Monitoring Queries

Connect to the PostgreSQL database container (`docker exec -it <postgres_container> psql -U postgres -d livestock`):

### 6.1 Check Ingestion Queue Status
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
*Expected: `transformation_status = 'PROCESSED'`, `ingestion_status = 'PROCESSED'`, `intake_form_submission_id` is populated.*

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
-- Total Parent Livestock Registrations
SELECT count(*) AS total_livestock_farms FROM g2p_register_livestocks;

-- Total Animals Registered
SELECT count(*) AS total_live_animals FROM g2p_register_animals;

-- Veterinary Event Counts
SELECT count(*) AS total_health_events FROM g2p_register_health_events;
SELECT count(*) AS total_vaccinations FROM g2p_register_vaccinations;
SELECT count(*) AS total_vital_events FROM g2p_register_vital_events;
SELECT count(*) AS total_breedings FROM g2p_register_breedings;
```

---

## 7. Known Issues, Mitigations & Troubleshooting

| Issue / Error | Root Cause | Implemented Code Mitigation |
| :--- | :--- | :--- |
| `ConnectionRefusedError: master_data DB` | Celery worker container missing `REGISTRY_STAFF_PORTAL_API_MASTER_DATA_DB_HOSTNAME`, defaulting to `postgres` or `localhost`. | Fallback ladder in `odk_ingest_hooks.py:L222-L230` inspecting all worker and partner master data host environment variables. |
| `403 Forbidden: CSRF token missing` | Server-to-server calls (`/livestock/approver-resolver` and `/awe/webhooks/decision`) lack browser CSRF session tokens. | Added routes to `REGISTRY_STAFF_CSRF_EXCLUDED_PATHS` in `apply_patches.py:L1245-L1268`. |
| `AWE rejects valid approvals` | AWE `required` approver rule compared token `name` claim ("Registry Admin") against `preferred_username` ("admin"). | Configured `required = FALSE` across all stages in `30_approver_rule.sql`, delegating authorization to the HTTP resolver. |
| `TypeError: Object of type date is not JSON serializable` | Celery worker attempted to serialize Python `datetime.date` objects in ODK repeat groups. | Implemented recursive serializer `_make_json_serializable()` in `odk_ingest_hooks.py:L58-L67`. |
| `Application Reference unique collision` | High concurrency submissions created colliding application references. | Patched `generate_application_reference()` to append 4 random hex characters (`base-XXXX`). |
