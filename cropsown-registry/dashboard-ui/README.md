# Crop Sown Registry Dashboard

The analytics view behind the Staff Portal's **Dashboard** header button. It is
a trimmed copy of the crop-sown screen from `oan_dashboards` — the other
registry / catalogue / A2C / DevOps dashboards from that repo are not included.

The Staff Portal ships as a prebuilt image, so this app runs as its own service
rather than as a portal route. `docker/staff-ui/assets/patch-dashboard-nav.js`
injects the header button that navigates here; the header's **Back** control
returns via the `?returnUrl=` the button appends.

## Where the numbers come from

Every panel reads the **registry database this stack runs** — the same one the
Staff Portal's API writes to — over a read-only connection. There is no fixture,
sample dataset or hardcoded fallback anywhere in the data path, so a registry
with no records renders empty panels rather than filler.

| What | Table |
| --- | --- |
| Registrations (farmer, address, season, status) | `g2p_register_crop_sowns` |
| Sowing lines (crop, area sown, ownership) | `g2p_register_sowings` |
| Labels and P-codes for geography / ownership / status | `g2p_attribute_values` |

Two code systems meet here. A record stores a lookup key (`REGION_ET07`), while
the sidebar and the choropleth both speak the bare boundary P-code (`ET07`).
`g2p_attribute_values` holds both, so it is what the API translates through —
`value_code` for the map, `value_display` for labels, and `parent_value_id` for
the region → zone → woreda → kebele cascade.

Where a lookup has no row the stored key is shown as-is. The crop commodity
catalogue is served externally and is not seeded locally, so crops currently
render as `CROP_COMMODITY_n` until those values are present.

The filters are the columns a crop sown record can actually be narrowed by:
region, zone, woreda, kebele and record status. Record status is offered from the
states present on live records, so a filter can never select nothing.

## Local development

```bash
cp .env.example .env   # DB_* -> the registry database, plus NEXT_PUBLIC_PORTAL_URL
npm ci
npm run dev
```

Against the compose stack that is `DB_HOST=localhost`, `DB_PORT=55432` (see
`POSTGRES_PORT` in `../local/.env`) and the `REGISTRY_DB*` credentials.

### An empty dashboard

If every panel reads zero, the registry has no crop sown records — create one in
the Staff Portal and reload. To confirm from the database directly:

```bash
docker compose --env-file local/.env exec postgres \
  psql -U postgres -d cropsown -c \
  'SELECT COUNT(*) FROM g2p_register_crop_sowns'
```

If that errors with `relation ... does not exist`, the platform migrations did
not complete. They abort partway unless `pg_trgm` exists in the registry database
— the register tables carry a GIN trigram index on `search_text`. It is created
by `local/postgres/init.sql`, which only runs on a fresh volume.

## Docker

Built from the repo root:

```bash
docker compose --env-file local/.env up -d --build dashboard-ui
```

`package-lock.json` must be regenerated under Linux whenever dependencies
change — a macOS-resolved lockfile is rejected by `npm ci` inside the image:

```bash
docker run --rm -v "$PWD":/w -w /w node:24-slim npm install --package-lock-only
```
