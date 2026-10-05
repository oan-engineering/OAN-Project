# Livestock Registry — Setup & Prerequisites Guide

This document provides step-by-step instructions to set up the **OpenG2P Gen2 Livestock Registry** from scratch, including all prerequisites, infrastructure dependencies, database configuration, and verification steps.

---

## 1. Prerequisites

### 1.1 System Requirements

| Requirement | Minimum Specification |
| :--- | :--- |
| **Operating System** | Linux (Ubuntu 22.04+), macOS, or WSL2 on Windows |
| **Docker** | Docker Engine 24.x+ with Docker Compose v2 |
| **RAM** | 8 GB minimum (16 GB recommended) |
| **Disk Space** | 10 GB free for images and volumes |
| **Git** | Git 2.30+ |
| **Python** | Python 3.10+ (for Connector Service) |
| **Node.js** | Node.js 20+ and npm 10+ (for Connector UI) |
| **Browser** | Chrome or Firefox (for Staff Portal and Connector UI) |

### 1.2 Infrastructure Services (Auto-provisioned by Docker Compose)

The following services are automatically started by the Livestock Registry `docker-compose.yml`:

| Service | Version | Purpose |
| :--- | :--- | :--- |
| **PostgreSQL** | `postgres:16` | Primary database for `livestock`, `master_data`, `iam`, `keycloak`, `awe` |
| **Redis** | `redis:7-alpine` | Celery message broker for background task processing |
| **MinIO** | `minio/minio:latest` | S3-compatible storage for Jinja2 templates and documents |
| **Keycloak** | `keycloak:24.0.4` | OIDC Identity Provider for staff authentication |
| **IAM Staff API** | `openg2p/iam-staff-portal-api:1.4.0` | Staff authentication gateway |
| **Master Data API** | `openg2p/master-data-api:1.1.0` | Geographic hierarchy (Region → Zone → Woreda → Kebele) |
| **ID Generator** | `openg2p/openg2p-id-generator:1.1.2` | Generates functional IDs for ear tags and registration IDs |
| **AWE (Optional)** | `openg2p/openg2p-awe:1.2.2` | Approval Workflow Engine for multi-tier approvals |

### 1.3 External Dependencies

| Dependency | Required For | How to Obtain |
| :--- | :--- | :--- |
| **ODK Central** | Collecting livestock survey data from ODK Collect | Self-hosted or cloud-hosted ODK Central instance |
| **ODK Collect** | Mobile data collection (animal registrations, health events, etc.) | Google Play Store (Android) |
| **OpenG2P Connector Service** | Polling ODK Central and ingesting data into the registry | Cloned from repository |
| **OpenG2P Connector UI** | Managing and monitoring connector pipelines | Cloned from repository |

### 1.4 Network & Domain Requirements

The authentication system uses **cookie-based sessions** across subdomains. You must access all services via `*.localtest.me` (which resolves to `127.0.0.1`):

| Service | URL |
| :--- | :--- |
| Staff Portal | `http://portal.localtest.me:3000` |
| Dashboard | `http://dashboard.localtest.me:3001` |
| Keycloak Admin | `http://keycloak.localtest.me:8080/admin` |
| IAM API | `http://iam.localtest.me:8000/docs` |
| MinIO Console | `http://minio.localtest.me:9001` |

> [!WARNING]
> **Never use `localhost` to access the Staff Portal.** Keycloak cookies are scoped to `localtest.me`. Using `localhost` will prevent authentication cookies from being sent across subdomains.

---

## 2. Repository Setup

### 2.1 Clone the Repository

```bash
git clone -b develop <repository-url>
cd livestock-registry
```

### 2.2 Environment Configuration

Create or verify `local/.env` with the following configuration:

```bash
RELEASE_NAME=livestock
COOKIE_DOMAIN=localtest.me

# Host & Ports
STAFF_UI_HOST=portal.localtest.me
STAFF_UI_PORT=3000
DASHBOARD_UI_HOST=dashboard.localtest.me
DASHBOARD_UI_PORT=3001
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
REGISTRY_DB=livestock
REGISTRY_DB_USER=livestock_user
REGISTRY_DB_PASSWORD=livestock_pass
MASTER_DATA_DB=master_data
MASTER_DATA_DB_USER=master_data_user
MASTER_DATA_DB_PASSWORD=master_data_pass
KEYCLOAK_DB=keycloak
KEYCLOAK_DB_USER=keycloak_user
KEYCLOAK_DB_PASSWORD=keycloak_pass
IAM_DB=iam
IAM_DB_USER=iam_user
IAM_DB_PASSWORD=iam_pass
IDGEN_DB=livestock_idgenerator
IDGEN_DB_USER=livestock_idgenerator_user
IDGEN_DB_PASSWORD=livestock_idgenerator_pass

# Keycloak & IAM
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin
KEYCLOAK_REALM=staff
AUTH_CLIENT_ID=livestock-staff-portal
AUTH_CLIENT_SECRET=livestock-staff-portal-secret
IAM_CLIENT_SECRET=staff-portal-secret

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
DEFAULT_BUCKET=default
TEMPLATE_BUCKET=templates
DOCUMENTS_BUCKET=documents

# Seeding & Features
LOAD_GEO_DATA=true
LOAD_SAMPLE_DATA=false
LOAD_IMAGES=true
LOAD_TEMPLATES=true
LOAD_ATTRIBUTES=true
SYNC_GEO_WIDGETS=true
AUDIT_ENABLED=false
AWE_ENABLED=false
PARTNER_SIGNATURE_VALIDATION_ENABLED=false
CONSENT_ENFORCEMENT_ENABLED=false
CRYPTO_BACKEND=NONE
KEYMANAGER_AUTH_ENABLED=false
RP_VERSION=0.0.0-develop.296
```

### 2.3 Verify docker-compose.yml Settings

Ensure these critical settings are present in `docker-compose.yml`:

1. **Master Data DB connection** on `partner-api` and `celery-worker`:
   ```yaml
   REGISTRY_CORE_MASTER_DATA_DB_DRIVER: postgresql+asyncpg
   REGISTRY_CORE_MASTER_DATA_DB_HOSTNAME: postgres
   REGISTRY_CORE_MASTER_DATA_DB_PORT: 5432
   REGISTRY_CORE_MASTER_DATA_DB_DBNAME: ${MASTER_DATA_DB}
   REGISTRY_CORE_MASTER_DATA_DB_USERNAME: ${MASTER_DATA_DB_USER}
   REGISTRY_CORE_MASTER_DATA_DB_PASSWORD: ${MASTER_DATA_DB_PASSWORD}
   ```

2. **CSRF disabled** on `staff-api` (required for internal server-to-server calls):
   ```yaml
   REGISTRY_STAFF_PORTAL_API_CSRF_ENABLED: 'false'
   ```

3. **PostgreSQL max connections** set to 200:
   ```yaml
   command: ["postgres", "-c", "max_connections=200"]
   ```

---

## 3. Starting the Stack

### 3.1 Build and Start All Services

```bash
docker compose --env-file local/.env up -d --build
```

### 3.2 Verify All Containers Are Running

```bash
docker compose --env-file local/.env ps
```

Expect ~13 containers to be running. Wait 2–3 minutes for `db-seed` to complete database initialization and migrations.

### 3.3 Verify Service Health

```bash
# Staff Portal API
curl -s http://localhost:8001/ping
# Expected: "pong"

# Master Data API
curl -s http://localhost:8010/ping
# Expected: "pong"
```

---

## 4. Database Configuration

Connect to PostgreSQL:
```bash
psql -h localhost -p 55432 -U postgres
```

### 4.1 Register the Ingestion Partner

```sql
\c master_data;

CREATE TABLE IF NOT EXISTS public.g2p_partners (
    partner_id character varying NOT NULL PRIMARY KEY,
    partner_mnemonic character varying NOT NULL UNIQUE,
    keymanager_reference_id character varying NOT NULL UNIQUE,
    is_active boolean DEFAULT true NOT NULL
);

INSERT INTO public.g2p_partners (partner_id, partner_mnemonic, keymanager_reference_id, is_active)
VALUES ('livestock-partner', 'Livestock', 'livestock-key-ref', true)
ON CONFLICT (partner_id) DO NOTHING;
```

### 4.2 Register Data Model & Ingestion Key Paths

```sql
\c livestock;

-- Data Model
INSERT INTO public.data_models (
    data_model_id, data_model_mnemonic, pattern_for_data_model,
    response_template_document_id, is_active
) VALUES (
    'MY_DATA_MODEL', 'MY_DATA_MODEL', '$.body.header.sender_id=>^.*$', NULL, true
) ON CONFLICT (data_model_id) DO NOTHING;

-- Ingestion Key Paths
INSERT INTO public.incoming_model_key_paths (
    key_path_id, data_model_id, key_path_for_message_id, key_path_for_sender,
    key_path_for_signature, key_path_for_signature_payload, is_list, key_path_for_list_elements
) VALUES (
    'my_key_path', 'MY_DATA_MODEL', '$.body.header.message_id', '$.body.header.sender_id',
    '$.body.header.signature', '$.body.message', false, NULL
) ON CONFLICT (key_path_id) DO NOTHING;
```

### 4.3 Link Intake UI Tab Sections

Ensure the livestock farmer location section is linked:

```sql
\c livestock;

INSERT INTO public.g2p_intake_form_ui_tab_sections (
    tab_section_id, tab_id, section_id, section_order
) VALUES (
    'intake_tab_section_2',
    '0ebdc221-187d-5df6-9dc3-c6f4c4ee160e',
    'livestock_farmer_location_section_02',
    20
) ON CONFLICT (tab_section_id) DO NOTHING;
```

---

## 5. MinIO Template Setup

Upload the Jinja2 transformation template to MinIO:

```bash
# Upload livestock_transform.j2 to the templates bucket
docker exec -i livestock-minio-1 sh -c '
mc alias set myminio http://localhost:9000 minioadmin minioadmin
mc mb --ignore-existing myminio/templates
'
docker exec -i livestock-minio-1 sh -c 'cat > /tmp/livestock_transform.j2' < docker/db-seed/livestock_transform.j2
docker exec livestock-minio-1 mc cp /tmp/livestock_transform.j2 myminio/templates/livestock_transform.j2
```

The template transforms raw ODK survey repeat groups into OpenG2P domain structures including:
- **Farmer Identity** — owner ID, Fayda FAN ID, name
- **Location** — region, zone, woreda, kebele
- **Animal Details** — ear tag, species, breed, gender, weight
- **Health Events** — disease type, treatment, veterinarian
- **Vaccinations** — vaccine type (with species-based auto-fallback), batch number
- **Vital Events** — birth/death events with offspring details
- **Breeding Events** — natural/AI breeding, sire details, expected calving

---

## 6. Connector Service & UI Setup

### 6.1 Install and Start the Connector Service

```bash
# Install (first time only)
cd openg2p-connector-service
python3 -m venv ../venv
source ../venv/bin/activate
pip install -e .

# Terminal 1: Connector API (:8050)
python -m openg2p_connector_service.main

# Terminal 2: Connector Celery Worker
celery -A openg2p_connector_service.worker worker --loglevel=info

# Terminal 3: Connector Celery Beat
celery -A openg2p_connector_service.worker beat --loglevel=info

# Terminal 4: Connector UI (:5173)
cd openg2p-connector-ui
npm install  # first time only
npm run dev
```

### 6.2 Create the Livestock Connector Pipeline

Open the Connector UI at `http://localhost:5173` and create a pipeline:

- **Name**: `Livestock Registry ODK`
- **Source Type**: `ODK Central`
- **Base URL**: `https://<your-odk-central-host>`
- **Project ID**: `<your-odk-project-id>`
- **Form ID**: `<your-livestock-form-id>`
- **Resolve Nav Links**: `true`
- **Target URL**: `http://localhost:8002/partner/ingest_data`
- **Target Headers**: `{"partner-id": "livestock-partner", "Content-Type": "application/json"}`
- **Data Model**: `MY_DATA_MODEL`
- **Schedule**: `*/1 * * * *` (Every 60 seconds)

---

## 7. Ports & Credentials Quick Reference

| Component | URL | Credentials |
| :--- | :--- | :--- |
| Staff Portal UI | `http://portal.localtest.me:3000` | `admin` / `admin` |
| Livestock Dashboard | `http://dashboard.localtest.me:3001` | N/A |
| Staff Portal API | `http://localhost:8001/docs` | Session / Bearer |
| Partner API | `http://localhost:8002/docs` | Header: `partner-id: livestock-partner` |
| Keycloak Admin | `http://keycloak.localtest.me:8080` | `admin` / `admin` |
| IAM API | `http://iam.localtest.me:8000/docs` | Session cookie |
| Master Data API | `http://localhost:8010/docs` | Internal |
| MinIO Console | `http://minio.localtest.me:9001` | `minioadmin` / `minioadmin` |
| PostgreSQL | `localhost:55432` | `postgres` / `postgres` |
| Connector API | `http://localhost:8050/docs` | N/A |
| Connector UI | `http://localhost:5173` | N/A |

---

## 8. Verification Checklist

After setup is complete, verify each item:

- [ ] **All Docker containers are running** — `docker compose ps` shows no exited containers
- [ ] **Staff Portal accessible** — `http://portal.localtest.me:3000` loads the login page
- [ ] **Keycloak login works** — Login with `admin`/`admin` succeeds
- [ ] **Master Data API responds** — `curl http://localhost:8010/ping` returns `pong`
- [ ] **Partner registered** — Query `master_data.g2p_partners` returns `livestock-partner`
- [ ] **Data model registered** — Query `livestock.data_models` returns `MY_DATA_MODEL`
- [ ] **Geographic dropdowns populate** — Region → Zone → Woreda → Kebele cascades in Staff Portal
- [ ] **MinIO templates uploaded** — Templates bucket contains `livestock_transform.j2`
- [ ] **Connector UI accessible** — `http://localhost:5173` loads the pipeline list
- [ ] **Pipeline created and polling** — Pipeline runs show in the Connector UI
- [ ] **Location tab section linked** — Query confirms `livestock_farmer_location_section_02` exists in `g2p_intake_form_ui_tab_sections`

---

## 9. Enabling Approval Workflow Engine (AWE) — Optional

For multi-tier approval workflows (Kebele → Woreda → Zone → Region):

1. Set `AWE_ENABLED=true` in `local/.env`
2. Start the stack with the AWE profile:
   ```bash
   docker compose --env-file local/.env --profile awe up -d --build
   ```
3. Configure approval stages, rules, and approver mappings in the AWE database
4. Map Keycloak users to geographic level groups (`kebele_users`, `woreda_users`, `zone_users`, `region_users`)

> [!IMPORTANT]
> Without AWE enabled, submissions are approved directly in the Staff Portal without a multi-tier workflow. For production deployments, AWE must be enabled and fully configured.

---

## 10. Troubleshooting

| Issue | Cause | Fix |
| :--- | :--- | :--- |
| Staff Portal shows blank page | Containers still initializing | Wait 2–3 minutes for `db-seed` to finish |
| Login redirect fails | Using `localhost` instead of `localtest.me` | Access via `http://portal.localtest.me:3000` |
| Geographic dropdowns empty | Geo seed not loaded or corrupted parent IDs | Set `LOAD_GEO_DATA=true` and restart; verify parent IDs in `g2p_geo_level_values` |
| `partner-id not found` error | Partner not registered in `master_data` | Run partner registration SQL (Section 4.1) |
| `data_model_id not found` | Data model not registered | Run data model SQL (Section 4.2) |
| PostgreSQL `53300` error | Max connections exhausted | Set `max_connections=200` in PostgreSQL |
| Location tab missing in intake | Tab section not linked | Run the tab section SQL (Section 4.3) |
| `ModuleNotFoundError: openg2p_registry_extensions` | Dynamic import aliasing gap | Ensure core patches are applied in Dockerfiles |
| Health event duplicate validation | `key_of` missing `treatment` field | Verify livestock-extension patches include treatment in dedup key |
| Future date validation fails | Docker container timezone is UTC, not local | Dates are validated against UTC; ensure dates are not in the future |
| Connector polling returns empty | ODK Central credentials or URL incorrect | Verify base URL, project ID, and credentials |
