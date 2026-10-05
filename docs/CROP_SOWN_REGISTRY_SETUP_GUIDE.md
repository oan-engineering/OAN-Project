# Crop Sown Registry — Setup & Prerequisites Guide

This document provides step-by-step instructions to set up the **OpenG2P Gen2 Crop Sown Registry** from scratch, including all prerequisites, infrastructure dependencies, database configuration, and verification steps.

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

The following services are automatically started by the Crop Sown Registry `docker-compose.yml`:

| Service | Version | Purpose |
| :--- | :--- | :--- |
| **PostgreSQL** | `postgres:16` | Primary database for `cropsown`, `master_data`, `iam`, `keycloak` |
| **Redis** | `redis:7-alpine` | Celery message broker for background task processing |
| **MinIO** | `minio/minio:latest` | S3-compatible storage for transformation templates and documents |
| **Keycloak** | `keycloak:24.0.4` | OIDC Identity Provider for staff authentication |
| **IAM Staff API** | `openg2p/iam-staff-portal-api:1.4.0` | Staff authentication gateway |
| **Master Data API** | `openg2p/master-data-api:1.1.0` | Geographic hierarchy (Region → Zone → Woreda → Kebele) |

### 1.3 External Dependencies

| Dependency | Required For | How to Obtain |
| :--- | :--- | :--- |
| **ODK Central** | Collecting field survey data from ODK Collect | Self-hosted or cloud-hosted ODK Central instance |
| **ODK Collect** | Mobile data collection in the field | Google Play Store (Android) |
| **OpenG2P Connector Service** | Polling ODK Central and ingesting data into the registry | Cloned from repository |
| **OpenG2P Connector UI** | Managing and monitoring connector pipelines | Cloned from repository |

### 1.4 Network & Domain Requirements

The authentication system uses **cookie-based sessions** across subdomains. You must access all services via `*.localtest.me` (which resolves to `127.0.0.1`):

| Service | URL |
| :--- | :--- |
| Staff Portal | `http://portal.localtest.me:3020` |
| Dashboard | `http://dashboard.localtest.me:3021` |
| Keycloak Admin | `http://keycloak.localtest.me:8080/admin` |
| IAM API | `http://iam.localtest.me:8000/docs` |
| MinIO Console | `http://minio.localtest.me:9001` |

> [!WARNING]
> **Never use `localhost` to access the Staff Portal.** Keycloak cookies are scoped to `localtest.me`. Using `localhost` will result in authentication failures.

---

## 2. Repository Setup

### 2.1 Clone the Repository

```bash
git clone -b develop <repository-url>
cd cropsown-regsitry
```

### 2.2 Bootstrap Local Configuration

The `local/` directory is gitignored. Create it with the required environment configuration:

```bash
# Create the local directory structure
mkdir -p local/postgres local/keycloak

# Create the environment file
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

### 2.3 Initialize PostgreSQL User & Database

Create `local/postgres/init.sql`:

```sql
CREATE USER cropsown_user WITH PASSWORD 'cropsown_pass';
CREATE DATABASE cropsown OWNER cropsown_user;
GRANT ALL PRIVILEGES ON DATABASE cropsown TO cropsown_user;
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

All containers should show `healthy` or `running` status. Wait 2–3 minutes for the database seeder (`db-seed`) to complete initialization.

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
VALUES ('crop-partner', 'CropSown', 'crop-key-ref', true)
ON CONFLICT (partner_id) DO NOTHING;
```

### 4.2 Register Data Model & Ingestion Key Paths

```sql
\c cropsown;

-- Data Model
INSERT INTO public.data_models (
    data_model_id, data_model_mnemonic, pattern_for_data_model,
    response_template_document_id, is_active
) VALUES (
    'CSR_DATA_MODEL', 'CSR_DATA_MODEL', '$.body.header.sender_id=>^.*$', NULL, true
) ON CONFLICT (data_model_id) DO NOTHING;

-- Ingestion Key Paths
INSERT INTO public.incoming_model_key_paths (
    key_path_id, data_model_id, key_path_for_message_id, key_path_for_sender,
    key_path_for_signature, key_path_for_signature_payload, is_list, key_path_for_list_elements
) VALUES (
    'csr_key_path', 'CSR_DATA_MODEL', '$.body.header.message_id', '$.body.header.sender_id',
    '$.body.header.signature', '$.body.message', false, NULL
) ON CONFLICT (key_path_id) DO NOTHING;
```

---

## 5. Connector Service & UI Setup

### 5.1 Install and Start the Connector Service

```bash
# Terminal 1: Connector API (:8050)
cd openg2p-connector-service
source ../venv/bin/activate  # or create: python3 -m venv ../venv && source ../venv/bin/activate && pip install -e .
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

### 5.2 Create the 4 Connector Pipelines

Open the Connector UI at `http://localhost:5173` and create 4 pipelines:

| Pipeline | ODK Form ID | Intake Form UUID |
| :--- | :--- | :--- |
| **CSR 1 — Planning** | `crop_sown_registry_plan` | `5bf0068c-ce19-46f8-874c-7147997f793b` |
| **CSR 2 — Cultivation & Land** | `crop_sown_registry_prep` | `6be15ab9-0f1b-4c38-995f-395d52a1b17a` |
| **CSR 3 — Sowing** | `crop_sown_registry_sown` | `4a7c2c98-0ffb-41d8-8fea-f22349823675` |
| **CSR 4 — Harvesting** | `crop_sown_registry_harvest` | `52150a37-153d-496d-9cd9-2a3815d6e13b` |

**Common pipeline settings:**
- **Source Type**: ODK Central
- **Base URL**: `https://<your-odk-central-host>`
- **Project ID**: `<your-odk-project-id>`
- **Resolve Nav Links**: `true`
- **Target URL**: `http://localhost:8002/partner/ingest_data`
- **Target Headers**: `{"partner-id": "crop-partner", "Content-Type": "application/json"}`
- **Data Model**: `CSR_DATA_MODEL`

---

## 6. Ports & Credentials Quick Reference

| Component | URL | Credentials |
| :--- | :--- | :--- |
| Staff Portal UI | `http://portal.localtest.me:3020` | `admin` / `admin` |
| Dashboard UI | `http://dashboard.localtest.me:3021` | N/A |
| Staff Portal API | `http://localhost:8001/docs` | Session / Bearer |
| Partner API | `http://localhost:8002/docs` | Header: `partner-id: crop-partner` |
| Keycloak Admin | `http://keycloak.localtest.me:8080` | `admin` / `admin` |
| IAM API | `http://iam.localtest.me:8000/docs` | Session cookie |
| Master Data API | `http://localhost:8010/docs` | Internal |
| MinIO Console | `http://minio.localtest.me:9001` | `minioadmin` / `minioadmin` |
| PostgreSQL | `localhost:55432` | `postgres` / `postgres` |
| Connector API | `http://localhost:8050/docs` | N/A |
| Connector UI | `http://localhost:5173` | N/A |

---

## 7. Verification Checklist

After setup is complete, verify each item:

- [ ] **All Docker containers are running** — `docker compose ps` shows no exited containers
- [ ] **Staff Portal accessible** — `http://portal.localtest.me:3020` loads the login page
- [ ] **Keycloak login works** — Login with `admin`/`admin` succeeds
- [ ] **Master Data API responds** — `curl http://localhost:8010/ping` returns `pong`
- [ ] **Partner registered** — Query `master_data.g2p_partners` returns `crop-partner`
- [ ] **Data model registered** — Query `cropsown.data_models` returns `CSR_DATA_MODEL`
- [ ] **Geographic dropdowns populate** — Region → Zone → Woreda → Kebele cascades in the Staff Portal
- [ ] **Connector UI accessible** — `http://localhost:5173` loads the pipeline list
- [ ] **4 pipelines created** — All 4 CSR pipelines appear in the Connector UI
- [ ] **MinIO templates uploaded** — Templates bucket contains the Jinja2 transformation templates

---

## 8. Troubleshooting

| Issue | Cause | Fix |
| :--- | :--- | :--- |
| Staff Portal shows blank page | Containers still initializing | Wait 2–3 minutes for `db-seed` to finish |
| Login redirect fails | Using `localhost` instead of `localtest.me` | Access via `http://portal.localtest.me:3020` |
| Geographic dropdowns empty | Geo seed data not loaded or corrupted parent IDs | Set `LOAD_GEO_DATA=true` in `.env` and restart, or manually seed geo data |
| `partner-id not found` error in ingestion | Partner not registered in `master_data` | Run the partner registration SQL (Section 4.1) |
| `data_model_id not found` during ingestion | Data model not registered | Run the data model SQL (Section 4.2) |
| PostgreSQL connection refused | Max connections exceeded | Set `max_connections=200` in PostgreSQL config |
| Connector polling returns empty | ODK Central credentials or URL incorrect | Verify base URL, project ID, and credentials in the pipeline config |
