# Branding assets

Source files for the registry's visual identity. Nothing here is read at
runtime — the asset is base64-embedded into the seed SQL, which is what
`db-seed` actually applies:

| Asset | Embedded into | Column |
|---|---|---|
| `ati-logo.png` | `meta_data/registry-configurations/g2p_registry_configuration.sql` | `registry_logo`, `registry_favicon` |

It is kept in the repo so the embedded base64 can be regenerated or swapped
without hunting for the original.

## No dashboard image

The ATI themes deliberately set no `dashboard_image`. The staff portal renders
that attribute as an `<img class="w-full h-auto">` pinned to the bottom of the
dashboard — not as a page background — so any image placed there scales to the
full width and keeps its aspect ratio, dominating the page. With the attribute
absent the portal falls back to its own default illustration.
