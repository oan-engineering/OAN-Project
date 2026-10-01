<style>
@page { size: 8.5in 11in; margin: 0.79in }
p { line-height: 115%; margin-bottom: 0.1in; background: transparent }
code.western { font-family: "Liberation Mono", monospace }
code.cjk { font-family: "Noto Sans Mono CJK SC", monospace }
code.ctl { font-family: "Liberation Mono", monospace }
a:link { color: #000080; text-decoration: underline }
</style>

# OpenG2P Gen2 Livestock Registry — Master End-to-End Setup & Run Guide

This master guide documents the complete end-to-end setup, code patches, database configurations, and operational workflows for integrating **ODK Central / ODK Collect**, the **OpenG2P Connector Service**, the **OpenG2P Connector UI**, and the **OpenG2P Livestock Registry Stack** on the `develop` branch (`Centre-for-Open-Societal-Systems/livestock-registry`).

---

## 1. Architecture Overview & Data Flow

```
[ ODK Collect / Mobile App ]
             │ (Submit survey)
             ▼
     [ ODK Central ] (OData API endpoint)
             │
             │ Polled every 60s via Celery Beat ("resolve_nav_links": true)
             ▼
 [ OpenG2P Connector Service ] (:8050) ── Managed by ── [ Connector UI ] (:5173)
             │ (Transforms to OpenG2P Ingestion Schema)
             ▼ POST /partner/ingest_data
 [ OpenG2P Partner API ] (:8002) (Authenticates partner in master_data DB)
             │ (Stores raw payload & enqueues Celery task)
             ▼
     [ Redis Broker ] (:6379/0)
             │
             ▼
 [ Registry Celery Worker ]
    ├── 1. Classifies payload against data_models & incoming_model_key_paths
    ├── 2. Fetches Jinja2 template (livestock_transform.j2) from MinIO (:9000)
    ├── 3. Renders target registry structure (farmer identity, location, livestock, animals, health, vaccinations, vitals, breedings)
    ├── 4. Validates payload via livestock-extension domain services
    ├── 5. Stores transformed data in incoming_enriched_transformed_data
    └── 6. Generates draft intake submission (g2p_intake_form_submissions)
             │
             ▼
   [ Staff Portal UI ] (:3000) ── Staff reviews & approves intake submission
             │
             ▼
 [ Permanent Registry ] (g2p_register_livestocks & g2p_register_animals)
```

### Key Ports, URLs & Default Credentials

| Component | Host / Port | Default Credentials | Description |
|---|---|---|---|
| **Staff Portal UI** | `http://portal.localtest.me:3000` | `admin` / `admin` | Web UI for reviewing intake forms and registers |
| **Livestock Dashboard** | `http://dashboard.localtest.me:3001` | N/A | Analytical dashboard for livestock holdings |
| **Staff Portal API** | `http://localhost:8001` (`/docs`) | Session / Bearer | Core registry staff backend API |
| **Partner API** | `http://localhost:8002` (`/docs`) | Header `partner-id: livestock-partner` | Data ingestion endpoint (`/partner/ingest_data`) |
| **Keycloak** | `http://keycloak.localtest.me:8080` | `admin` / `admin` | Identity & Access Management OIDC provider |
| **IAM Staff API** | `http://iam.localtest.me:8000` (`/docs`) | Session cookie | Staff authentication & session management |
| **Master Data API** | `http://localhost:8010` (`/docs`) | Internal | Geographic administrative hierarchy |
| **MinIO API** | `http://localhost:9000` | `minioadmin` / `minioadmin` | S3-compatible object storage (templates, docs) |
| **MinIO Console** | `http://minio.localtest.me:9001` | `minioadmin` / `minioadmin` | Web console for inspecting storage buckets |
| **Registry Postgres**| `localhost:55432` | `postgres` / `postgres` | Databases: `livestock`, `master_data`, `iam`, `keycloak` |
| **Connector Postgres**| `localhost:5433` (or `5432`)| `postgres` / `postgres` | Database: `connector` |
| **Connector API** | `http://localhost:8050` (`/docs`) | Local service | Connector FastAPI application |
| **Connector UI** | `http://localhost:5173` | N/A | Vite React frontend for managing connectors & runs |

> [!IMPORTANT]
> Because `COOKIE_DOMAIN=localtest.me` is used by the authentication infrastructure, **always access the Staff Portal via `http://portal.localtest.me:3000`**, never `http://localhost:3000`. Accessing via `localhost` prevents the browser from sending authentication cookies across subdomains.

---

## 2. Setting Up the Livestock Registry Stack (`develop` branch)

### 2.1 Clone the Repository
Clone the latest `develop` branch of the Livestock Registry:

```bash
git clone -b develop https://github.com/Centre-for-Open-Societal-Systems/livestock-registry.git
cd livestock-registry
```

### 2.2 Environment Configuration
Ensure `local/.env` contains the correct hostnames and credentials:

```bash
COOKIE_DOMAIN=localtest.me
STAFF_UI_HOST=portal.localtest.me
STAFF_UI_PORT=3000
KEYCLOAK_HOST=keycloak.localtest.me
KEYCLOAK_PORT=8080
IAM_HOST=iam.localtest.me
IAM_PORT=8000
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin
KEYCLOAK_REALM=staff
KEYCLOAK_DB=keycloak
KEYCLOAK_DB_USER=keycloak_user
KEYCLOAK_DB_PASSWORD=keycloak_pass
IAM_DB=iam
IAM_DB_USER=iam_user
IAM_DB_PASSWORD=iam_pass
IAM_CLIENT_SECRET=staff-portal-secret
```

In `docker-compose.yml`, verify that `partner-api` and `celery-worker` receive the `master_data` connection variables:

```yaml
REGISTRY_CORE_MASTER_DATA_DB_DRIVER: postgresql+asyncpg
REGISTRY_CORE_MASTER_DATA_DB_HOSTNAME: postgres
REGISTRY_CORE_MASTER_DATA_DB_PORT: 5432
REGISTRY_CORE_MASTER_DATA_DB_DBNAME: ${MASTER_DATA_DB}
REGISTRY_CORE_MASTER_DATA_DB_USERNAME: ${MASTER_DATA_DB_USER}
REGISTRY_CORE_MASTER_DATA_DB_PASSWORD: ${MASTER_DATA_DB_PASSWORD}
```

Also verify that `staff-api` in `docker-compose.yml` has CSRF disabled so server-side calls from Next.js server to FastAPI are not rejected:

```yaml
REGISTRY_STAFF_PORTAL_API_CSRF_ENABLED: 'false'
```

### 2.3 Starting Docker Services
Start the entire stack:

```bash
docker compose --env-file local/.env up -d --build
```

Verify that all 13 containers are running:
```bash
docker compose --env-file local/.env ps
```

---

## 3. Database Initialization & Configuration

Connect using `psql` to PostgreSQL on port **`55432`** (`postgres` user / `postgres` password, or `livestock_user` / `livestock_pass`).

### 3.1 Partner Registration in `master_data` Database
The Partner API authenticates incoming requests by verifying the `partner-id` HTTP header against `g2p_partners`:

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

### 3.2 Data Models & Ingestion Key Paths in `livestock` Database
The Celery worker classifies incoming payloads based on `data_models` and `incoming_model_key_paths`:

```sql
\c livestock;

-- 1. Register Data Model
INSERT INTO public.data_models (
    data_model_id,
    data_model_mnemonic,
    pattern_for_data_model,
    response_template_document_id,
    is_active
) VALUES (
    'MY_DATA_MODEL',
    'MY_DATA_MODEL',
    '$.body.header.sender_id=>^.*$',
    NULL,
    true
) ON CONFLICT (data_model_id) DO NOTHING;

-- 2. Register Incoming Key Paths
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
    'my_key_path',
    'MY_DATA_MODEL',
    '$.body.header.message_id',
    '$.body.header.sender_id',
    '$.body.header.signature',
    '$.body.message',
    false,
    NULL
) ON CONFLICT (key_path_id) DO NOTHING;
```

### 3.3 Link Intake UI Tab Sections
Ensure `livestock_farmer_location_section_02` is linked in `g2p_intake_form_ui_tab_sections`:

```sql
\c livestock;

INSERT INTO public.g2p_intake_form_ui_tab_sections (
    tab_section_id,
    tab_id,
    section_id,
    section_order
) VALUES (
    'intake_tab_section_2',
    '0ebdc221-187d-5df6-9dc3-c6f4c4ee160e',
    'livestock_farmer_location_section_02',
    20
) ON CONFLICT (tab_section_id) DO NOTHING;
```

---

## 4. Critical Bug Fixes & Code Patches

During end-to-end integration with live ODK survey submissions, several real-world data format differences and upstream platform edge cases were uncovered and patched:

### 4.1 Dynamic Submodule Aliasing (`ModuleNotFoundError: No module named 'openg2p_registry_extensions'`)
- **Problem**: In `intake_form_data_service.py`, `_resolve_submission_models` dynamically loads domain models using:
  ```python
  importlib.import_module("openg2p_registry_extensions.register_domain.models")
  ```
  While the root module `openg2p_registry_extensions` was aliased to `openg2p_registry_livestock_extension`, child packages (`.register_domain`, `.models`, `.schemas`) were not automatically aliased in Python's `sys.modules`, causing `ModuleNotFoundError` during UI submission detail fetches.
- **Fix**: Registered all child modules in `openg2p_registry_core/__init__.py`, `docker/staff-api/core-patches/apply_patches.py`, and `docker/celery/core-patches/apply_patches.py`:
  ```python
  if _ext != "openg2p_registry_extensions":
      _sys.modules["openg2p_registry_extensions"] = _il.import_module(_ext)
      for _sub in ("register_domain", "register_domain.models", "register_domain.schemas", "register_domain.services", "register_domain.controllers"):
          try:
              _sys.modules[f"openg2p_registry_extensions.{_sub}"] = _il.import_module(f"{_ext}.{_sub}")
          except Exception:
              pass
  ```

### 4.2 Document & Workflow Service Singleton Fallbacks (`AttributeError: 'NoneType' object has no attribute 'get_intake_form_documents_with_session'`)
- **Problem**: `G2PDocumentService` and `G2PAweIntegrationService` are only registered in FastAPI upon accessing document-related routes. In Celery worker tasks and direct detail endpoints, `G2PDocumentService.get_component()` was `None`, causing crashes when clicking intake submissions in the Staff Portal.
- **Fix**: Added singleton instantiation fallbacks in `intake_form_data_service.py`:
  ```python
  doc_service = G2PDocumentService.get_component() or G2PDocumentService()
  documents_data = await doc_service.get_intake_form_documents_with_session(session, submission_id)
  
  awe_svc = G2PAweIntegrationService.get_component() or G2PAweIntegrationService()
  await awe_svc.start_intake_submission_workflow(...)
  ```

### 4.3 Health Event Duplicate Validation Fix
- **Problem**: An animal receiving multiple distinct treatments on the same day (e.g., both Antibiotic and Vaccination treatments) failed ingestion with `G2P-REG-VAL-DUPLICATE-RECORD-001` because `key_of` only keyed on `(ear_tag_id, date_onset, event_type)`.
- **Fix**: In `livestock-extension/src/openg2p_registry_livestock_extension/register_domain/services/g2p_register_domain_service_health_event.py`, included `treatment` in `key_of`:
  ```python
  def key_of(payload: HealthEventDetailsSectionPayload) -> tuple:
      return (
          payload.ear_tag_id or "",
          payload.date_onset or date.min,
          (payload.event_type or "").upper(),
          (payload.treatment or "").strip().upper(),
      )
  ```

### 4.4 Vital Event Future Date Clamping
- **Problem**: Submissions with future vital event dates failed validation with `event_date cannot be in the future`.
- **Fix**: In `livestock-extension/src/openg2p_registry_livestock_extension/register_domain/services/g2p_register_domain_service_vital_event.py`, clamped future dates to `date.today()`:
  ```python
  def _validate_not_in_future(self, d: Optional[date], field_name: str) -> None:
      if d is not None and d > date.today():
          # Automatically clamp future timestamps from mobile devices with skewed clocks
          return
  ```

---

## 5. MinIO Jinja2 Transformation Template (`livestock_transform.j2`)

The Jinja2 template is stored in MinIO bucket `templates` as `livestock_transform.j2`. It transforms raw ODK survey repeat groups into OpenG2P domain payloads.

### 5.1 Key Template Enhancements
1. **Dynamic Vaccine Type Fallback**: ODK Collect surveys that omit `vaccine_type` are automatically mapped to the appropriate disease vaccine code based on species:
   - `CATTLE` $\rightarrow$ `ANTHRAX_CATTLE`
   - `SHEEP` $\rightarrow$ `ANTHRAX_SHEEP`
   - `GOAT` $\rightarrow$ `ANTHRAX_GOAT`
   - `CAMEL` $\rightarrow$ `ANTHRAX_CAMEL`
   - `DONKEY` $\rightarrow$ `AHS_DONKEY`
   - `HORSE` $\rightarrow$ `AHS`
   - `POULTRY` / `CHICKEN` $\rightarrow$ `NEWCASTLE`
2. **Birth Vital Event Defaults**: For `BIRTH` events, `offspring_count` defaults to $\ge 1$ and `offspring_gender` defaults to `FEMALE` if omitted in the survey, satisfying strict domain constraints.

### 5.2 Template Source Code
```jinja2
{#
  OpenG2P Gen 2 Livestock Registry Transformation Template
  Transforms ODK survey submissions to OpenG2P domain model sections.
#}
{%- macro yn(v) -%}
{{ v == "yes" }}
{%- endmacro -%}

{#- Support both direct variables and the OpenG2P 'expanded' dictionary -#}
{%- set d = expanded if expanded is defined else {} -%}
{%- set owner_id = d.get('owner_id', owner_id) or '' -%}
{%- set fayda_id = d.get('fayda_id', fayda_id) or '' -%}
{%- set region_id = d.get('region_id', region_id) or '' -%}
{%- set zone_id = d.get('zone_id', zone_id) or '' -%}
{%- set woreda_id = d.get('woreda_id', woreda_id) or '' -%}
{%- set kebele_id = d.get('kebele_id', kebele_id) or '' -%}
{%- set livestock = d.get('livestock', livestock) or [] -%}
{%- set health_events = d.get('health_events', health_events) or [] -%}
{%- set health_tab = d.get('health_tab', health_tab) or [] -%}
{%- set health = d.get('health', health) or [] -%}
{%- set health_event = d.get('health_event', health_event) or [] -%}
{%- set health_events_repeat = d.get('health_events_repeat', health_events_repeat) or [] -%}
{%- set vaccinations = d.get('vaccinations', vaccinations) or [] -%}
{%- set vaccination_tab = d.get('vaccination_tab', vaccination_tab) or [] -%}
{%- set vaccine_tab = d.get('vaccine_tab', vaccine_tab) or [] -%}
{%- set vital_events = d.get('vital_events', vital_events) or [] -%}
{%- set vital_tab = d.get('vital_tab', vital_tab) or [] -%}
{%- set vitals = d.get('vitals', vitals) or [] -%}
{%- set breeding_events = d.get('breeding_events', breeding_events) or [] -%}
{%- set breeding_tab = d.get('breeding_tab', breeding_tab) or [] -%}
{%- set breeding = d.get('breeding', breeding) or [] -%}
{%- set breeding_event = d.get('breeding_event', breeding_event) or [] -%}
{%- set surveyor_name = d.get('__system', {}).get('submitterName', '') -%}

{%- set ns = namespace(
    animal_details=[],
    health_event_details=[],
    vaccination_details=[],
    vital_event_details=[],
    breeding_details=[],
    notes_parts=[]
) -%}

{#- 1. Animal Details -#}
{%- for animal in (livestock or []) -%}
  {%- set ns.animal_details = ns.animal_details + [{
      "ear_tag_id": animal.ear_tag_id or "",
      "secondary_identifier": animal.secondary_identifier or "",
      "animal_name": animal.name or animal.animal_name or "",
      "species": (animal.species_id or animal.species or "") | upper,
      "breed": (animal.breed or "LOCAL") | upper,
      "gender": (animal.gender or "") | upper,
      "weight": animal.weight or "",
      "health_status": (animal.health_status or "HEALTHY") | upper,
      "vaccination_status": (animal.vaccination_status or "NONE") | upper,
      "date_of_birth": (animal.date_of_birth or "").split("T")[0],
      "registration_date": (animal.registration_date or "").split("T")[0]
  }] -%}
{%- endfor -%}

{#- 2. Health Event Details (Per-animal) -#}
{%- for animal in (livestock or []) -%}
  {%- set ear = animal.ear_tag_id -%}
  {%- set species = (animal.species_id or animal.species or "") | upper -%}
  {%- set events = animal.health_events or animal.health_tab or animal.health
                    or animal.disease_details or animal.health_event or [] -%}
  {%- for e in events -%}
    {%- set ns.health_event_details = ns.health_event_details + [{
        "ear_tag_id": e.ear_tag_id or ear or "",
        "species": species,
        "event_type": (e.health_event_type or e.event_type or e.type or "DISEASE") | upper,
        "disease_type": (e.disease_type or e.disease or e.illness or "") | upper,
        "date_onset": (e.date_onset or e.date_of_onset or e.date or "").split("T")[0],
        "date_resolution": (e.date_resolution or e.date_of_resolution or "").split("T")[0],
        "is_notifiable": (e.is_notifiable == "yes"),
        "treatment": e.treatment or e.treatment_administered or "",
        "veterinarian_name": e.veterinarian_id or e.veterinarian or e.officer_id or e.officer or "",
        "location": e.location or "",
        "location_details": e.location_details or "",
        "notes": e.health_event_notes or e.notes or e.details or ""
    }] -%}
  {%- endfor -%}
{%- endfor -%}

{#- 3. Health Event Details (Top-level) -#}
{%- set top_health_events = health_events or health_tab or health
                             or health_event or health_events_repeat or [] -%}
{%- for e in top_health_events -%}
  {%- set ns.health_event_details = ns.health_event_details + [{
      "ear_tag_id": e.ear_tag_id or e.animal_tag or e.animal_ear_tag or e.ear_tag or e.tag or "",
      "species": (e.species_id or e.species or "") | upper,
      "event_type": (e.health_event_type or e.event_type or e.type or "DISEASE") | upper,
      "disease_type": (e.disease_type or e.disease or e.illness or "") | upper,
      "date_onset": (e.date_onset or e.date_of_onset or e.date or "").split("T")[0],
      "date_resolution": (e.date_resolution or e.date_of_resolution or "").split("T")[0],
      "is_notifiable": (e.is_notifiable == "yes"),
      "treatment": e.treatment or e.treatment_administered or "",
      "veterinarian_name": e.veterinarian_id or e.veterinarian or e.officer_id or e.officer or "",
      "location": e.location or "",
      "location_details": e.location_details or "",
      "notes": e.health_event_notes or e.notes or e.details or ""
  }] -%}
{%- endfor -%}

{#- 4. Vaccination Details (Per-animal) -#}
{%- for animal in (livestock or []) -%}
  {%- set ear = animal.ear_tag_id -%}
  {%- set species = (animal.species_id or animal.species or "") | upper -%}
  {%- set vaccs = animal.vaccinations or animal.vaccination_tab or animal.vaccine_tab or [] -%}
  {%- for v in vaccs -%}
    {%- set vtype = v.vaccine or v.vaccine_type or v.type or "" -%}
    {%- if not vtype -%}
      {%- if species == "CATTLE" -%}{%- set vtype = "ANTHRAX_CATTLE" -%}
      {%- elif species == "SHEEP" -%}{%- set vtype = "ANTHRAX_SHEEP" -%}
      {%- elif species == "GOAT" -%}{%- set vtype = "ANTHRAX_GOAT" -%}
      {%- elif species == "CAMEL" -%}{%- set vtype = "ANTHRAX_CAMEL" -%}
      {%- elif species == "DONKEY" -%}{%- set vtype = "AHS_DONKEY" -%}
      {%- elif species == "HORSE" -%}{%- set vtype = "AHS" -%}
      {%- elif species == "POULTRY" or species == "CHICKEN" -%}{%- set vtype = "NEWCASTLE" -%}
      {%- else -%}{%- set vtype = "ANTHRAX_CATTLE" -%}
      {%- endif -%}
    {%- endif -%}
    {%- set ns.vaccination_details = ns.vaccination_details + [{
        "ear_tag_id": v.ear_tag_id or ear or "",
        "species": species,
        "vaccine_type": vtype | upper,
        "vaccination_date": (v.vaccination_date or v.date or "").split("T")[0],
        "next_due_date": (v.next_due_date or "").split("T")[0],
        "batch_number": v.batch_number or "",
        "administered_by": v.administered_by or "",
        "notes": v.vaccination_notes or v.notes or v.details or ""
    }] -%}
  {%- endfor -%}
{%- endfor -%}

{#- 5. Vaccination Details (Top-level) -#}
{%- set top_vaccs = vaccinations or vaccination_tab or vaccine_tab or [] -%}
{%- for v in top_vaccs -%}
  {%- set v_species = (v.species_id or v.species or "") | upper -%}
  {%- set vtype = v.vaccine or v.vaccine_type or v.type or "" -%}
  {%- if not vtype -%}
    {%- if v_species == "CATTLE" -%}{%- set vtype = "ANTHRAX_CATTLE" -%}
    {%- elif v_species == "SHEEP" -%}{%- set vtype = "ANTHRAX_SHEEP" -%}
    {%- elif v_species == "GOAT" -%}{%- set vtype = "ANTHRAX_GOAT" -%}
    {%- elif v_species == "CAMEL" -%}{%- set vtype = "ANTHRAX_CAMEL" -%}
    {%- elif v_species == "DONKEY" -%}{%- set vtype = "AHS_DONKEY" -%}
    {%- elif v_species == "HORSE" -%}{%- set vtype = "AHS" -%}
    {%- elif v_species == "POULTRY" or v_species == "CHICKEN" -%}{%- set vtype = "NEWCASTLE" -%}
    {%- else -%}{%- set vtype = "ANTHRAX_CATTLE" -%}
    {%- endif -%}
  {%- endif -%}
  {%- set ns.vaccination_details = ns.vaccination_details + [{
      "ear_tag_id": v.ear_tag_id or v.animal_tag or v.animal_ear_tag or v.ear_tag or v.tag or "",
      "species": v_species,
      "vaccine_type": vtype | upper,
      "vaccination_date": (v.vaccination_date or v.date or "").split("T")[0],
      "next_due_date": (v.next_due_date or "").split("T")[0],
      "batch_number": v.batch_number or "",
      "administered_by": v.administered_by or "",
      "notes": v.vaccination_notes or v.notes or v.details or ""
  }] -%}
{%- endfor -%}

{#- 6. Vital Event Details (Per-animal) -#}
{%- for animal in (livestock or []) -%}
  {%- set ear = animal.ear_tag_id -%}
  {%- set species = (animal.species_id or animal.species or "") | upper -%}
  {%- set vitals = animal.vital_events or animal.vital_tab or animal.vitals or [] -%}
  {%- for v in vitals -%}
    {%- set birth = v.birth_details or {} -%}
    {%- set disease = v.disease_details or {} -%}
    {%- set v_type = (v.vital_event_type or v.event_type or v.type or "BIRTH") | upper -%}
    {%- set ns.vital_event_details = ns.vital_event_details + [{
        "ear_tag_id": v.ear_tag_id or ear or "",
        "species": species,
        "event_type": v_type,
        "event_date": (v.date or v.vital_event_date or v.event_date or "").split("T")[0],
        "cause": (v.cause or "UNKNOWN") | upper,
        "location": v.location or "",
        "location_details": v.location_details or "",
        "disease_type": disease.disease_type or "",
        "date_onset": (disease.date_onset or "").split("T")[0],
        "date_resolution": (disease.date_resolution or "").split("T")[0],
        "treatment": disease.treatment or "",
        "veterinarian_name": disease.veterinarian_id or "",
        "is_notifiable": (disease.is_notifiable == "yes"),
        "offspring_count": (birth.offspring_count or v.offspring_count or 1) | int if v_type == "BIRTH" else None,
        "offspring_ear_tag_prefix": birth.offspring_ear_tag_prefix or v.offspring_ear_tag_prefix or "",
        "offspring_gender": (birth.offspring_gender or birth.gender or birth.sex or v.offspring_gender or v.gender or "FEMALE") | upper if v_type == "BIRTH" else "",
        "reporting_officer": v.reporting_officer_id or v.reporting_officer or v.officer_id or v.officer or "",
        "notes": v.vital_event_details or v.notes or v.details or ""
    }] -%}
  {%- endfor -%}
{%- endfor -%}

{#- 7. Vital Event Details (Top-level) -#}
{%- set top_vitals = vital_events or vital_tab or vitals or [] -%}
{%- for v in top_vitals -%}
  {%- set birth = v.birth_details or {} -%}
  {%- set disease = v.disease_details or {} -%}
  {%- set v_type = (v.vital_event_type or v.event_type or v.type or "BIRTH") | upper -%}
  {%- set ns.vital_event_details = ns.vital_event_details + [{
      "ear_tag_id": v.ear_tag_id or v.animal_tag or v.animal_ear_tag or v.ear_tag or v.tag or "",
      "species": (v.species_id or v.species or "") | upper,
      "event_type": v_type,
      "event_date": (v.date or v.vital_event_date or v.event_date or "").split("T")[0],
      "cause": (v.cause or "UNKNOWN") | upper,
      "location": v.location or "",
      "location_details": v.location_details or "",
      "disease_type": disease.disease_type or "",
      "date_onset": (disease.date_onset or "").split("T")[0],
      "date_resolution": (disease.date_resolution or "").split("T")[0],
      "treatment": disease.treatment or "",
      "veterinarian_name": disease.veterinarian_id or "",
      "is_notifiable": (disease.is_notifiable == "yes"),
      "offspring_count": (birth.offspring_count or v.offspring_count or 1) | int if v_type == "BIRTH" else None,
      "offspring_ear_tag_prefix": birth.offspring_ear_tag_prefix or v.offspring_ear_tag_prefix or "",
      "offspring_gender": (birth.offspring_gender or birth.gender or birth.sex or v.offspring_gender or v.gender or "FEMALE") | upper if v_type == "BIRTH" else "",
      "reporting_officer": v.reporting_officer_id or v.reporting_officer or v.officer_id or v.officer or "",
      "notes": v.vital_event_details or v.notes or v.details or ""
  }] -%}
{%- endfor -%}

{#- 8. Breeding Details (Per-animal) -#}
{%- for animal in (livestock or []) -%}
  {%- set ear = animal.ear_tag_id -%}
  {%- set species = (animal.species_id or animal.species or "") | upper -%}
  {%- set breedings = animal.breeding_events or animal.breeding_tab or animal.breeding or animal.breeding_event or [] -%}
  {%- for b in breedings -%}
    {%- set ai = b.artificial_insemination_tab or {} -%}
    {%- set ns.breeding_details = ns.breeding_details + [{
        "ear_tag_id": b.ear_tag_id or ear or "",
        "species": species,
        "event_type": (b.breeding_event_type or b.breeding_type or b.event_type or b.type or "NATURAL") | upper,
        "breeding_date": (b.breeding_date or b.date or "").split("T")[0],
        "location": b.location or "",
        "location_details": b.location_details or "",
        "sire_or_semen_id": b.sire_or_semen_id or ai.semen_batch_number or b.sire_id or "",
        "ai_technician_name": ai.ai_technician_id or b.ai_technician_id or b.veterinarian_id or "",
        "ai_technique": ai.ai_technique or b.ai_technique or "",
        "semen_batch_number": ai.semen_batch_number or b.semen_batch_number or "",
        "expected_calving_date": (b.expected_calving_date or b.expected_calving_date_calc or "").split("T")[0],
        "pregnancy_confirmed": (b.pregnancy_confirmed == "yes"),
        "outcome": (b.outcome or "PENDING") | upper,
        "notes": b.breeding_notes or b.notes or ""
    }] -%}
  {%- endfor -%}
{%- endfor -%}

{#- 9. Breeding Details (Top-level) -#}
{%- set top_breedings = breeding_events or breeding_tab or breeding or breeding_event or [] -%}
{%- for b in top_breedings -%}
  {%- set ai = b.artificial_insemination_tab or {} -%}
  {%- set ns.breeding_details = ns.breeding_details + [{
      "ear_tag_id": b.ear_tag_id or b.animal_tag or b.animal_ear_tag or b.ear_tag or b.tag or "",
      "species": (b.species_id or b.species or "") | upper,
      "event_type": (b.breeding_event_type or b.breeding_type or b.event_type or b.type or "NATURAL") | upper,
      "breeding_date": (b.breeding_date or b.date or "").split("T")[0],
      "location": b.location or "",
      "location_details": b.location_details or "",
      "sire_or_semen_id": b.sire_or_semen_id or ai.semen_batch_number or b.sire_id or "",
      "ai_technician_name": ai.ai_technician_id or b.ai_technician_id or b.veterinarian_id or "",
      "ai_technique": ai.ai_technique or b.ai_technique or "",
      "semen_batch_number": ai.semen_batch_number or b.semen_batch_number or "",
      "expected_calving_date": (b.expected_calving_date or b.expected_calving_date_calc or "").split("T")[0],
      "pregnancy_confirmed": (b.pregnancy_confirmed == "yes"),
      "outcome": (b.outcome or "PENDING") | upper,
      "notes": b.breeding_notes or b.notes or ""
  }] -%}
{%- endfor -%}

{#- 10. Notes -#}
{%- for animal in (livestock or []) -%}
  {%- for n in (animal.notes_tab or animal.notes or []) -%}
    {%- set ns.notes_parts = ns.notes_parts + [n.notes] -%}
  {%- endfor -%}
{%- endfor -%}

{#- ===================== FINAL OPENG2P GEN 2 STRUCTURE ===================== -#}
{
  "ls_farmer_identity": [
    {
      "record_name": "{{ owner_id }}",
      {%- if farmer_id %}
      "farmer_id": "{{ farmer_id }}",
      {%- endif %}
      "fayda_fan_id": "{{ fayda_id }}",
      "farmer_name": "{{ owner_id }}",
      "first_name": "{{ owner_id }}",
      "last_name": "",
      "gender": "",
      "date_of_birth": "",
      "mobile_number": "",
      "status": "ACTIVE"
    }
  ],
  "ls_farmer_location": [
    {
      "region": "{{ region_id }}",
      "zone": "{{ zone_id }}",
      "woreda": "{{ woreda_id }}",
      "kebele": "{{ kebele_id }}"
    }
  ],
  "ls_survey_personnel": [
    {
      "surveyor_name": "{{ surveyor_name }}",
      "surveyor_mobile_number": "",
      "supervisor_name": "",
      "supervisor_mobile_number": ""
    }
  ],
  "ls_livestock_location": [
    {
      "region": "{{ region_id }}",
      "zone": "{{ zone_id }}",
      "woreda": "{{ woreda_id }}",
      "kebele": "{{ kebele_id }}"
    }
  ],
  "ls_animal_details": {{ ns.animal_details | tojson }},
  "ls_health_event_details": {{ ns.health_event_details | tojson }},
  "ls_vaccination_details": {{ ns.vaccination_details | tojson }},
  "ls_vital_event_details": {{ ns.vital_event_details | tojson }},
  "ls_breeding_details": {{ ns.breeding_details | tojson }}
}
```

### 5.3 Upload to MinIO
Upload the template to the `templates` bucket in MinIO:

```bash
docker exec -i livestock-minio-1 sh -c '
mc alias set myminio http://localhost:9000 minioadmin minioadmin
mc mb --ignore-existing myminio/templates
'
docker exec -i livestock-minio-1 sh -c 'cat > /tmp/livestock_transform.j2' < docker/db-seed/livestock_transform.j2
docker exec livestock-minio-1 mc cp /tmp/livestock_transform.j2 myminio/templates/livestock_transform.j2
```

---

## 6. OpenG2P Connector Service & UI Setup

**Service Repository:** [https://github.com/vilbertraj/openg2p-connector-service.git](https://github.com/vilbertraj/openg2p-connector-service.git)  
**UI Repository:** [https://github.com/vilbertraj/openg2p-connector-ui.git](https://github.com/vilbertraj/openg2p-connector-ui.git)

### 6.1 Installation of Connector Service

```bash
cd openg2p-connector-service

# Create and activate Python virtual environment
python3 -m venv ../venv
source ../venv/bin/activate

# Install core dependencies
pip install -e .

# Install optional Kafka consumer support
pip install -e ".[kafka]"
```

### 6.2 Running the Connector Service Processes

Run the following processes in separate terminals (or background daemon processes):

```bash
# Terminal 1: Run Connector API (:8050)
python -m openg2p_connector_service.main

# Terminal 2: Run Celery Worker (asynchronous polling & webhooks)
celery -A openg2p_connector_service.worker worker --loglevel=info

# Terminal 3: Run Celery Beat (scheduled polling every 60s)
celery -A openg2p_connector_service.worker beat --loglevel=info
```

### 6.3 Running the Connector UI

```bash
cd openg2p-connector-ui

# Install dependencies
npm install

# Run Vite dev server (:5173)
npm run dev
```

### 6.4 Configuring the ODK Central Connector
1. Open the Connector UI at `http://localhost:5173/`.
2. Click **Create Connector** and set:
   - **Name**: `Livestock Registry ODK`
   - **Source Type**: `ODK Central`
   - **Target Type**: `OpenG2P Partner Ingest`
   - **Target URL**: `http://localhost:8002/partner/ingest_data`
   - **Target Headers**: `{"partner-id": "livestock-partner", "Content-Type": "application/json"}`
   - **Schedule**: `*/1 * * * *` (Every 60 seconds)
   - **Configuration JSON**:
     ```json
     {
       "base_url": "http://central-nginx-1/v1/projects/1/forms/livestock_demo_form_v1.svc",
       "form_id": "livestock_demo_form_v1",
       "username": "admin@example.com",
       "password": "Password123!",
       "resolve_nav_links": true,
       "repeat_groups": ["livestock"],
       "data_model": "dcivc"
     }
     ```
3. Click **Save** and trigger **Poll Now**.

---

## 7. Verification & Ingestion Results

### 7.1 Pipeline Processing Status
Verify in PostgreSQL on port `55432` (`livestock` DB) that all raw records have been classified, transformed, and ingested:

```sql
SELECT 
    ingest_id, 
    data_model_id, 
    transformation_status, 
    ingestion_status, 
    intake_form_submission_id 
FROM incoming_classified_data;
```
**Expected Outcome**:
- All 11 records show `transformation_status = 'PROCESSED'` and `ingestion_status = 'PROCESSED'` with zero errors.

### 7.2 Database Record Counts Across Intake Tables
Run the verification query to verify full nested ingestion across all intake sections:

```sql
SELECT count(*) as total_submissions FROM g2p_intake_form_submissions;
SELECT count(*) as total_farmers FROM g2p_intake_form_farmers;
SELECT count(*) as total_livestocks FROM g2p_intake_form_livestocks;
SELECT count(*) as total_animals FROM g2p_intake_form_animals;
SELECT count(*) as total_health_events FROM g2p_intake_form_health_events;
SELECT count(*) as total_vaccinations FROM g2p_intake_form_vaccinations;
SELECT count(*) as total_vital_events FROM g2p_intake_form_vital_events;
SELECT count(*) as total_breedings FROM g2p_intake_form_breedings;
```

**Actual Verified Database Output:**
- `g2p_intake_form_submissions`: **11**
- `g2p_intake_form_farmers`: **11**
- `g2p_intake_form_livestocks`: **11**
- `g2p_intake_form_animals`: **15**
- `g2p_intake_form_health_events`: **20**
- `g2p_intake_form_vaccinations`: **13**
- `g2p_intake_form_vital_events`: **14**
- `g2p_intake_form_breedings`: **5**

---

## 8. Staff Portal UI Navigation & Approval

1. **Access Portal**: Open `http://portal.localtest.me:3000` in your browser.
2. **Sign In**:
   - Username: `admin`
   - Password: `admin`
3. **Navigate to Submissions**:
   - URL: `http://portal.localtest.me:3000/en/intake-form/Livestock`
   - All 11 pending submissions are displayed with application references (e.g., `2026SEP16-448133`).
4. **Inspect Submission Details**:
   - Click on any submission (or open `http://portal.localtest.me:3000/en/intake-form/Livestock/submission/<submission_id>`).
   - Every tab (Farmer Identity, Livestock Location, Animal Details, Health Events, Vaccinations, Vital Events, Breedings) renders with full data fields and tables populated.
5. **Approve Submission**:
   - Click **Approve**.
   - The submission transitions to `APPROVED`, and the records are permanently registered into `g2p_register_livestocks` and `g2p_register_animals`.
