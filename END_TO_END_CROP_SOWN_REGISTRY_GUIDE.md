# OpenG2P Gen2 Crop Sown Registry — Master End-to-End Setup & ODK Integration Guide

This master guide documents the complete end-to-end setup, code architecture, database configurations, and operational workflows for integrating **ODK Central / ODK Collect**, the **OpenG2P Connector Service**, the **OpenG2P Connector UI**, and the **OpenG2P Crop Sown Registry Stack** (`cropsown-regsitry`) on OpenG2P Gen 2 (`develop` branch).

---

## 1. Architecture Overview & 4-Stage Lifecycle Data Flow

In OpenG2P Gen 2, the Crop Sown Registry is modeled with `CropSown` as the core hub record. Land details sit flat on the record, while crop lines are tracked across 4 lifecycle stages corresponding to **4 ODK Forms** and **4 OpenG2P Intake Forms**:

```
                  ┌────────────────────────────────────────────────────────┐
                  │              ODK Central (Project ID: 9)               │
                  │  1. CSR – 1. Planning         (crop_sown_registry_plan)│
                  │  2. CSR – 2. Cultivation&Land (crop_sown_registry_prep)│
                  │  3. CSR – 3. Sowing           (crop_sown_registry_sown)│
                  │  4. CSR – 4. Harvesting     (crop_sown_registry_harvest)│
                  └──────────────────────────┬─────────────────────────────┘
                                             │ Polled via OData / Webhook
                                             ▼
                 ┌────────────────────────────────────────────────────────┐
                 │          OpenG2P Connector Service (:8050)             │
                 │             Managed via Connector UI (:5173)           │
                 │  - Pipeline 1: Planning       -> /partner/ingest_data  │
                 │  - Pipeline 2: Cultivation    -> /partner/ingest_data  │
                 │  - Pipeline 3: Sowing         -> /partner/ingest_data  │
                 │  - Pipeline 4: Harvesting     -> /partner/ingest_data  │
                 └──────────────────────────┬─────────────────────────────┘
                                             │ HTTP POST (partner-id: crop-partner)
                                             ▼
                 ┌────────────────────────────────────────────────────────┐
                 │             Crop Sown Partner API (:8002)              │
                 │          Authenticates partner & enqueues to Redis     │
                 └──────────────────────────┬─────────────────────────────┘
                                             │
                                             ▼
                 ┌────────────────────────────────────────────────────────┐
                 │             Crop Sown Celery Worker                    │
                 │  1. Classifies payload via data_models                 │
                 │  2. Renders target Jinja2 template from MinIO          │
                 │  3. Validates domain attributes & cross-references     │
                 │  4. Intercepted by odk_ingest_hooks.py (Zero git diff) │
                 │  5. Creates Draft Intake Form Submissions              │
                 └──────────────────────────┬─────────────────────────────┘
                                             │
      ┌──────────────────┬───────────────────┴───────────────────┬──────────────────┐
      ▼                  ▼                                       ▼                  ▼
┌──────────────┐   ┌──────────────┐                        ┌──────────────┐   ┌──────────────┐
│  Intake 1:   │   │  Intake 2:   │                        │  Intake 3:   │   │  Intake 4:   │
│   PLANNING   │   │ CULTIVATION  │                        │    SOWING    │   │  HARVESTING  │
└──────┬───────┘   └──────┬───────┘                        └──────┬───────┘   └──────┬───────┘
       │                  │                                       │                  │
       └──────────────────┴───────────────────┬───────────────────┴──────────────────┘
                                             ▼
                              ┌──────────────────────────────┐
                              │    Staff Portal UI (:3020)   │
                              │  Staff reviews and approves: │
                              │  http://portal.localtest.me:3020 │
                              └──────────────┬───────────────┘
                                             ▼
                              ┌──────────────────────────────┐
                              │    Permanent Crop Register   │
                              │    g2p_register_crop_sowns   │
                              └──────────────────────────────┘
```

---

## 2. Ports, URLs & Default Credentials

Because the Livestock Registry stack has been stopped, the default ports defined in `cropsown-regsitry/docker-compose.yml` can be used cleanly:

| Component | Host / Port | Default Credentials | Description |
| :--- | :--- | :--- | :--- |
| **Staff Portal UI** | `http://portal.localtest.me:3020` | `admin` / `admin` | Web UI for reviewing intake forms and registers |
| **Dashboard UI** | `http://dashboard.localtest.me:3021` | N/A | Analytical dashboard for Crop Sown holdings |
| **Staff Portal API** | `http://localhost:8001` (`/docs`) | Session / Bearer | Core registry staff backend API |
| **Partner API** | `http://localhost:8002` (`/docs`) | Header `partner-id: crop-partner` | Data ingestion endpoint (`/partner/ingest_data`) |
| **Keycloak** | `http://keycloak.localtest.me:8080` | `admin` / `admin` | Identity & Access Management OIDC provider |
| **IAM Staff API** | `http://iam.localtest.me:8000` (`/docs`) | Session cookie | Staff authentication & session management |
| **Master Data API** | `http://localhost:8010` (`/docs`) | Internal | Geographic administrative hierarchy |
| **MinIO API / Console** | `http://localhost:9000` / `http://minio.localtest.me:9001` | `minioadmin` / `minioadmin` | S3 storage (templates, documents) |
| **Registry Postgres**| `localhost:55432` | `postgres` / `postgres` | Databases: `cropsown`, `master_data`, `iam`, `keycloak` |
| **Connector API** | `http://localhost:8050` (`/docs`) | Local service | OpenG2P Connector FastAPI application |
| **Connector UI** | `http://localhost:5173` | N/A | Vite React frontend for managing pipelines & runs |

> [!IMPORTANT]
> The Staff Portal is published on port **`3020`** (`http://portal.localtest.me:3020`). Always access it with the `localtest.me` domain so Keycloak cookies work across subdomains.

---

## 3. Directory Structure & Local Config Bootstrap

The repository is cloned at:
`/home/vilbertraj/work/OAN/gen2-livestock registry/cropsown-regsitry`

Because the `local/` configuration folder is in `.gitignore`, bootstrap it from the existing livestock configuration:

```bash
cd "/home/vilbertraj/work/OAN/gen2-livestock registry/cropsown-regsitry"

# 1. Copy the local bootstrap configs from livestock-registry
cp -r "../livestock-registry/local" ./local

# 2. Update local/.env for Crop Sown Registry
cat << 'EOF' > local/.env
RELEASE_NAME=cropsown
COOKIE_DOMAIN=localtest.me

# Host & Ports
STAFF_UI_HOST=portal.localtest.me
STAFF_UI_PORT=3020
DASHBOARD_UI_HOST=dashboard.localtest.me
DASHBOARD_UI_PORT=3021
STAFF_API_PORT=8001
PARTNER_API_PORT=8002
MASTER_DATA_PORT=8010
POSTGRES_PORT=55432
KEYCLOAK_HOST=keycloak.localtest.me
KEYCLOAK_PORT=8080
IAM_HOST=iam.localtest.me
IAM_PORT=8000
MINIO_HOST=minio.localtest.me
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001

# Postgres Databases
POSTGRES_PASSWORD=postgres
REGISTRY_DB=cropsown
REGISTRY_DB_USER=cropsown_user
REGISTRY_DB_PASSWORD=cropsown_pass
MASTER_DATA_DB=master_data
MASTER_DATA_DB_USER=master_data_user
MASTER_DATA_DB_PASSWORD=master_data_pass
KEYCLOAK_DB=keycloak
KEYCLOAK_DB_USER=keycloak_user
KEYCLOAK_DB_PASSWORD=keycloak_pass
IAM_DB=iam
IAM_DB_USER=iam_user
IAM_DB_PASSWORD=iam_pass
IDGEN_DB=idgenerator
IDGEN_DB_USER=idgen_user
IDGEN_DB_PASSWORD=idgen_pass

# Keycloak & IAM
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin
KEYCLOAK_REALM=staff
AUTH_CLIENT_ID=cropsown-registry-staff-portal
AUTH_CLIENT_SECRET=staff-portal-secret
IAM_CLIENT_SECRET=staff-portal-secret

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
DEFAULT_BUCKET=crop-default
TEMPLATE_BUCKET=templates
DOCUMENTS_BUCKET=documents

# Seeding & Features
LOAD_GEO_DATA=false
LOAD_SAMPLE_DATA=false
LOAD_CROPSOWN_SAMPLE_DATA=true
LOAD_IMAGES=true
LOAD_TEMPLATES=true
LOAD_ATTRIBUTES=true
SYNC_GEO_WIDGETS=true
ATTRIBUTE_DOMAINS=CROP_COMMODITY,CROP_VARIETY,CROP_SEASON,PLOT_CATEGORY,SOIL_FERTILITY,FERTILIZER_TYPE
AUDIT_ENABLED=false
AWE_ENABLED=false
PARTNER_SIGNATURE_VALIDATION_ENABLED=false
CONSENT_ENFORCEMENT_ENABLED=false
CRYPTO_BACKEND=NONE
KEYMANAGER_AUTH_ENABLED=false
RP_VERSION=0.0.0-develop.296
EOF
```

### Update `local/postgres/init.sql`
Ensure `local/postgres/init.sql` creates the `cropsown` database and user:
```sql
CREATE USER cropsown_user WITH PASSWORD 'cropsown_pass';
CREATE DATABASE cropsown OWNER cropsown_user;
GRANT ALL PRIVILEGES ON DATABASE cropsown TO cropsown_user;
```

---

## 4. The 4 ODK Forms $\leftrightarrow$ 4 Intake Forms Specification

From the ODK Central instance (`https://odk.13.207.43.8.nip.io`, Project ID `9`) and OpenG2P metadata:

| Stage # | ODK Form Name | ODK XML Form ID | Intake Form Name | Exact Intake `form_id` UUID | Target Section Names |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **`CSR – 1. Planning`** | `crop_sown_registry_plan` | **Crop Sown Planning Intake** | `5bf0068c-ce19-46f8-874c-7147997f793b` | `cropsown_intake_record_section_01`<br>`cropsown_cropsown_location_section_03`<br>`cropsown_planning_details_section_01`<br>`cropsown_cluster_details_section_01` |
| **2** | **`CSR – 2. Cultivation & Land`** | `crop_sown_registry_prep` | **Crop Sown Cultivation Intake** | `6be15ab9-0f1b-4c38-995f-395d52a1b17a` | `cropsown_common_intake_record_section_01`<br>`cropsown_cultivation_details_section_01`<br>`cropsown_cultivation_cluster_details_section_01` |
| **3** | **`CSR – 3. Sowing`** | `crop_sown_registry_sown` | **Crop Sown Sowing Intake** | `4a7c2c98-0ffb-41d8-8fea-f22349823675` | `cropsown_common_intake_record_section_01`<br>`cropsown_sowing_details_section_01`<br>`cropsown_infestation_details_section_01` |
| **4** | **`CSR – 4. Harvesting`** | `crop_sown_registry_harvest` | **Crop Sown Harvesting Intake** | `52150a37-153d-496d-9cd9-2a3815d6e13b` | `cropsown_common_intake_record_section_01`<br>`cropsown_harvest_details_section_01` |

- **Register ID**: `6b06a95a-9a6c-5a33-a33d-c1625716c59c`
- **Full Intake Form (All Sections)**: `852cf76a-a691-5572-9dd2-9bbca6fa5c78` (`Crop Sown Intake`)

---

## 5. Starting the Docker Services

```bash
cd "/home/vilbertraj/work/OAN/gen2-livestock registry/cropsown-regsitry"

# Build and start the stack
docker compose --env-file local/.env up -d --build

# Verify all containers are healthy
docker compose --env-file local/.env ps
```

---

## 6. Database Initialization & Ingestion Metadata

Connect to PostgreSQL on port **`55432`**:

### 6.1 Register Partner in `master_data` Database
```sql
\c master_data;

CREATE TABLE IF NOT EXISTS public.g2p_partners (
    partner_id character varying NOT NULL PRIMARY KEY,
    partner_mnemonic character varying NOT NULL UNIQUE,
    keymanager_reference_id character varying NOT NULL UNIQUE,
    is_active boolean DEFAULT true NOT NULL
);

INSERT INTO public.g2p_partners (partner_id, partner_mnemonic, keymanager_reference_id, is_active)
VALUES ('crop-partner', 'CropSown', 'crop-key-ref', true)
ON CONFLICT (partner_id) DO NOTHING;
```

### 6.2 Data Model & Ingestion Key Paths in `cropsown` Database
The Celery worker classifies incoming payloads using `data_models` and `incoming_model_key_paths`:

```sql
\c cropsown;

-- 1. Register Data Model
INSERT INTO public.data_models (
    data_model_id,
    data_model_mnemonic,
    pattern_for_data_model,
    response_template_document_id,
    is_active
) VALUES (
    'CSR_DATA_MODEL',
    'CSR_DATA_MODEL',
    '$.body.header.sender_id=>^.*$',
    NULL,
    true
) ON CONFLICT (data_model_id) DO NOTHING;

-- 2. Register Key Paths
INSERT INTO public.incoming_model_key_paths (
    key_path_id,
    data_model_id,
    key_path_for_message_id,
    key_path_for_sender,
    key_path_for_signature,
    key_path_for_signature_payload,
    is_list,
    key_path_for_list_elements
) VALUES (
    'csr_key_path',
    'CSR_DATA_MODEL',
    '$.body.header.message_id',
    '$.body.header.sender_id',
    '$.body.header.signature',
    '$.body.message',
    false,
    NULL
) ON CONFLICT (key_path_id) DO NOTHING;
```

---

## 7. OpenG2P Connector Service Setup (4 Pipelines)

The Connector Service runs locally from `/home/vilbertraj/work/OAN/gen2-livestock registry/openg2p-connector-service`.

### 7.1 Start Connector Service & UI
```bash
# Terminal 1: Connector API (:8050)
cd "/home/vilbertraj/work/OAN/gen2-livestock registry/openg2p-connector-service"
source ../venv/bin/activate
python -m openg2p_connector_service.main

# Terminal 2: Connector Celery Worker
celery -A openg2p_connector_service.worker worker --loglevel=info

# Terminal 3: Connector Celery Beat
celery -A openg2p_connector_service.worker beat --loglevel=info

# Terminal 4: Connector UI (:5173)
cd "/home/vilbertraj/work/OAN/gen2-livestock registry/openg2p-connector-ui"
npm run dev
```

### 7.2 Create the 4 Pipelines in Connector UI (`http://localhost:5173`)

#### Pipeline 1: Planning
- **Name**: `CSR 1 - Planning Pipeline`
- **Source Type**: `ODK Central`
- **Base URL**: `https://odk.13.207.43.8.nip.io`
- **Project ID**: `9`
- **Form ID**: `crop_sown_registry_plan`
- **Resolve Nav Links**: `true`
- **Target URL**: `http://localhost:8002/partner/ingest_data`
- **Target Headers**: `{"partner-id": "crop-partner", "Content-Type": "application/json"}`
- **Data Model**: `CSR_DATA_MODEL`

#### Pipeline 2: Cultivation & Land
- **Name**: `CSR 2 - Cultivation & Land Pipeline`
- **Form ID**: `crop_sown_registry_prep`
- (All other settings identical to Pipeline 1)

#### Pipeline 3: Sowing
- **Name**: `CSR 3 - Sowing Pipeline`
- **Form ID**: `crop_sown_registry_sown`
- (All other settings identical to Pipeline 1)

#### Pipeline 4: Harvesting
- **Name**: `CSR 4 - Harvesting Pipeline`
- **Form ID**: `crop_sown_registry_harvest`
- (All other settings identical to Pipeline 1)

---

## 8. Transformation Templates in MinIO

Upload the transformation templates into MinIO bucket `templates`:
1. `csr_planning_transform.j2`
2. `csr_cultivation_transform.j2`
3. `csr_sowing_transform.j2`
4. `csr_harvesting_transform.j2`

### Template Output Schema Example (`csr_planning_transform.j2`):
```jinja2
{
  "submission_source": "ODK",
  "application_reference": "{{ message.__system.submission_date | strftime('%Y%b%d') | upper }}-{{ 999999 | random }}",
  "draft_status": "FINAL",
  "created_by": "system",
  "form_id": "5bf0068c-ce19-46f8-874c-7147997f793b",
  "sections": [
    {
      "section_id": "cropsown_intake_record_section_01",
      "data": [
        {
          "farmer_id": "{{ message.farmer_id }}",
          "farmer_name": "{{ message.farmer_name }}",
          "fayda_fan_id": "{{ message.fayda_fan_id }}",
          "crop_year": "{{ message.crop_year }}",
          "production_season": "{{ message.production_season | upper }}"
        }
      ]
    },
    {
      "section_id": "cropsown_planning_details_section_01",
      "data": [
        {
          "land_id": "{{ message.land_id }}",
          "season": "{{ message.production_season | upper }}",
          "commodity": "{{ message.commodity }}",
          "planned_area": "{{ message.planned_area }}"
        }
      ]
    }
  ]
}
```

### Stages 2, 3, 4 Template Output Schema:
Stages 2, 3, and 4 use `cropsown_common_intake_record_section_01` as their record header section:
```jinja2
{
  "submission_source": "ODK",
  "application_reference": "{{ message.__system.submission_date | strftime('%Y%b%d') | upper }}-{{ 999999 | random }}",
  "draft_status": "FINAL",
  "created_by": "system",
  "form_id": "<STAGE_INTAKE_FORM_UUID>",
  "sections": [
    {
      "section_id": "cropsown_common_intake_record_section_01",
      "data": [
        {
          "fayda_fan_id": "{{ message.fayda_fan_id }}",
          "crop_year": "{{ message.crop_year }}",
          "production_season": "{{ message.production_season | upper }}"
        }
      ]
    },
    {
      "section_id": "<STAGE_SPECIFIC_SECTION_ID>",
      "data": [ ... ]
    }
  ]
}
```

---

## 9. Zero-Diff Runtime Hook Architecture (`odk_ingest_hooks.py`)

To follow **Option 1 (clean git status, 0 changes to tracked files)**:

1. Create untracked file:
   `cropsown-extension/src/openg2p_registry_cropsown_extension/odk_ingest_hooks.py`
2. Auto-load via Python `.pth` file in `staff-api` and `celery`:
   ```bash
   echo "import openg2p_registry_cropsown_extension.odk_ingest_hooks" > /usr/local/lib/python3.12/site-packages/odk_ingest_hooks.pth
   ```
3. **What `odk_ingest_hooks.py` intercepts**:
   - Reuses the active Celery worker database `AsyncSession` to eliminate `dbengine.get()` null connection failures.
   - Intercepts `_validate_fayda_season_and_year` so that incoming Cultivation, Sowing, and Harvesting submissions resolve against the drafted Planning submission in the active database transaction.
   - Enforces pattern matches for `farmer_id` (`FR-XXXXXXXXXX`) and `fayda_fan_id` (`FAN-XXXXXXXXXXXXXXXX`).

---

## 10. Verification & Staff Approval Workflow

1. **Trigger Polling**:
   In the Connector UI (`http://localhost:5173`), click **Poll Now** for each pipeline.
2. **Verify Ingestion in Postgres**:
   ```sql
   \c cropsown;
   SELECT ingest_id, data_model_id, transformation_status, ingestion_status, intake_form_submission_id 
   FROM incoming_classified_data 
   ORDER BY created_at DESC LIMIT 10;
   ```
3. **Verify Intake Submissions**:
   ```sql
   SELECT submission_id, application_reference, form_id, draft_status, approval_status 
   FROM g2p_intake_form_submissions 
   ORDER BY first_created_at DESC;
   ```
4. **Staff Review & Approval**:
   - Open **`http://portal.localtest.me:3020/en/intake-form`**
   - Click on each stage's submission (Planning, Cultivation, Sowing, Harvesting).
   - Verify that all data fields, plots, and crop details are displayed.
   - Click **Approve** to commit the records into `g2p_register_crop_sowns`!
