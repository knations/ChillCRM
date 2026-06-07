# Design Pipeline

## Visual Direction

After the functional CRM and archive design is stable, redesign the local CRM to feel like a native Apple app: elegant, quiet, simple on the surface, and powerful underneath.

## Pipeline Status

This is intentionally queued after the functional CRM, archive, cleanup, reporting, export, and daily operating workflows are complete. While those workflows continue to evolve, new features should be designed so they can later collapse into a calmer native-style surface without losing capability.

The live planning artifact is now generated at `reports/apple_style_redesign_pipeline.md` with CSV export at `reports/apple_style_redesign_pipeline.csv`. It tracks the current timing decision, gates, phases, and preservation contract without changing CRM data.

## Principles

- Keep the CRM operational first; visual polish should not hide incomplete workflows.
- Reduce visual noise in navigation, filters, and detail panels.
- Preserve all current power: search, filtering, archive access, cleanup review, exports, saved views, and record editing.
- Make record detail feel calmer and more spatial, with clearer sections for contact data, owner, activity, archive, links, notes, and tasks.
- Use the Archive and Cleanup surfaces as proof points for progressive disclosure: dense capability, simple first impression.
- Preserve the current data and workflow depth under native-feeling inspectors, toolbars, menus, and focused review surfaces.

## Candidate Passes

- Replace the dark utility sidebar with a lighter native-style navigation rail.
- Move high-frequency filters into compact toolbar controls.
- Give the right detail panel a more Apple-style inspector layout.
- Simplify metrics and status cards into quieter system-like panels.
- Turn Status into a native-feeling command center: Next Action, Daily Operating Guide, decisions, cleanup state, and export readiness should feel simple at first glance while keeping drill-down power close.
- Refine typography, spacing, focus states, and table density for long working sessions.

## Timing

Do this after the recovered optional archive and core CRM workflows are complete enough that the visual system can organize the full product rather than chase changing structure.

## Current Gates

- Save the Apple-style visual redesign timing decision in Project Decisions.
- Settle duplicate people, duplicate leads, lead/person overlap, and duplicate tag policies.
- Preserve the Archive association model, including linked document files, searchable unlinked calls/texts, manual review statuses, backup-first linking, and audit logging.
- Keep export packages, backups, restore, saved views, and daily operating workflows available in the final interface.
