# Portal Config Map

The current portal foundation is intentionally conservative. It gives future
work stable names and an internal staff preview without turning on client
access.

## Confirmed Files

- `crm_app/portal_config.py`: route prefix, nav items, feature flags,
  portal roles, permission actions, and forbidden internal scopes.
- `config/chillportal.env.example`: placeholder environment names only.
- `docs/CHILLPORTAL.md`: product and approval boundary.
- `docs/ACCESS.md`: access model boundary.
- `docs/PROJECT_MAP.md`: system ownership map.
- `docs/PORTAL_SCHEMA_PLAN.md`: Person-first table blueprint.

## Route Constants

- `PORTAL_ROUTE_PREFIX`: `/portal`
- `PORTAL_DEFAULT_ROUTE`: `/portal`
- `PORTAL_PRIMARY_RECORD_TYPE`: `people`
- `PORTAL_OPTIONAL_CONTEXT_RECORD_TYPES`: `companies`

`/portal?person_id=<id>` is wired as a disabled-by-default staff preview route.
It returns 404 unless `CHILLPORTAL_ENABLED=true` is set in a local or approved
staging environment.

## Feature Flags

All portal feature flags default to `false`.

- `CHILLPORTAL_ENABLED`
- `CHILLPORTAL_FEATURE_DASHBOARD`
- `CHILLPORTAL_FEATURE_DOCUMENTS`
- `CHILLPORTAL_FEATURE_NEXT_STEPS`
- `CHILLPORTAL_FEATURE_CLIENT_NOTES`

## Configuration Rule

Use placeholder values in committed files. Real values belong only in the
approved deployment provider or local private environment files.

## Schema Plan

`PORTAL_SCHEMA_PLAN` defines four Person-first portal table concepts now
reflected by runtime schema helpers:

- `portal_profiles`
- `portal_shared_documents`
- `portal_next_steps`
- `portal_client_notes`

No production migration or client-access backfill has been applied by this
foundation work.

## Rollback

Rollback for this foundation is still simple because no client access is
enabled by default:

- remove `crm_app/portal_config.py`
- remove `config/chillportal.env.example`
- remove the ChillPortal docs
- remove the README pointer
- remove the `/portal` preview route and portal helper methods from
  `crm_app/server.py`

No production data, DNS, provider, or client-access rollback is required.
