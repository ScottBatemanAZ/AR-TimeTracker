# Master resin library + Formlabs tank compatibility

Date: 2026-07-20
Status: Approved, not yet implemented

## Problem

`resin-library.json` currently holds 12 generic, brand-agnostic resin
families (Standard, Tough, Flexible, etc.) with only `name`/`full`/
`densityGPerMl`/`tags`/`typicalCostPerKg`. This is fine for rough cost
estimation but doesn't reflect what users actually buy: named, branded
products (Formlabs Tough 2000 Resin V2, Elegoo Standard, Siraya Tech
Tenacious...) with real mechanical properties.

Formlabs specifically hardware-locks materials to resin tanks/trays per
printer generation (Form 2 / Form 3 family / Form 4 family each have
distinct, non-interchangeable tank types, and some materials require a
*specific* tank even within a compatible printer generation — e.g. Castable
Wax 40 requires the Form 3 Resin Tank V2.1). A user can own a compatible
printer and still be unable to print a resin they have in hand because the
installed tank is wrong — this already happened with a Tough 2000 order that
turned out to need a tank the shop doesn't have. Nothing in the tracker
today surfaces this before the material gets logged.

This tracker is a public, self-hosted repo aimed at professional users
generally (not just this shop), so the resin library should be broadly
useful — not a personal cheat sheet for one printer's TDS values.

## Goals

- Replace the 12-entry generic library with a brand-tagged master library:
  full ~48-material Formlabs catalog (including dental/orthodontic/BioMed
  lines) with real per-SKU mechanical specs and printer/tank compatibility,
  plus family-level entries for Anycubic, Elegoo, Siraya Tech, Phrozen, and
  HeyGears.
- Surface Formlabs tank incompatibility as a non-blocking warning in the
  material modal, driven by a new "installed tank" setting per Formlabs
  printer.
- Replace the flat `<select>` resin picker with a searchable/filterable
  library browser so ~48+ Formlabs entries (plus other brands) stay usable.
- No change to the underlying cost formula (`densityGPerMl` ×
  `typicalCostPerKg` still drives resin material cost) or to how a resin,
  once picked into `settings.resinTypes`, flows through the material modal,
  session log, invoices, or ODS/XLSX export.

## Non-goals

- No SQLite / database backend. The app is explicitly no-database,
  no-build-step; a static JSON file fetched once by the frontend (same
  pattern as `filament-library.json`) is simpler and consistent.
- No owned-tank *inventory* tracking (a list of every tank you own, spares
  included). Only "what's installed right now" per printer is tracked —
  enough to catch the mistake, not a warehouse management system.
- No hard-blocking of session saves on a compatibility mismatch. Warning
  only, matching the app's existing non-blocking data-entry philosophy
  (notes, failed-print logging).
- No compatibility logic for non-Formlabs brands — no other brand in scope
  hardware-locks resins to trays, so `printerCompatibility`/
  `tankCompatibility` stay empty arrays for them (present in the schema for
  consistency, unused in practice).
- No changes to the filament library or its picker UI — smaller catalog,
  not brand/compatibility-sensitive, out of scope here.
- No `printerModel`/`tankType` auto-detection from the Formlabs API — set
  manually in Settings (the Dashboard Cloud API poll doesn't expose a
  reliable machine-type field per `poll_formlabs()` today).

## Design

### 1. `resin-library.json` schema

```json
{
  "materials": [
    {
      "name": "Tough 2000 Resin V2",
      "brand": "Formlabs",
      "full": "Formlabs Tough 2000 Resin V2",
      "densityGPerMl": 1.06,
      "typicalCostPerKg": 149,
      "tags": ["engineering", "impact-resistant"],
      "mechanical": {
        "tensileStrengthMPa": 40.4,
        "elongationPct": 79.0,
        "flexuralModulusMPa": 1701,
        "shoreHardness": null
      },
      "printerCompatibility": ["Form 4", "Form 4L", "Form 4B"],
      "tankCompatibility": ["Form 4 Resin Tank"]
    },
    {
      "name": "Standard",
      "brand": "Elegoo",
      "full": "Elegoo Standard Photopolymer Resin",
      "densityGPerMl": 1.10,
      "typicalCostPerKg": 22,
      "tags": ["beginner", "common"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    }
  ]
}
```

- `mechanical`, `printerCompatibility`, `tankCompatibility` are optional —
  `{}`/`[]` where unknown or not applicable, never required by any code
  path. Cost calc only ever reads `densityGPerMl` and the saved
  `costPerKg` on the user's `settings.resinTypes` entry (unchanged).
- Formlabs coverage: all ~48 materials Formlabs currently lists in their
  data-sheet catalog (engineering/prototyping line + dental/orthodontic/
  BioMed lines), each with real specs sourced from Formlabs' product pages
  and technical data sheets. Some fields (e.g. density) may be `null` where
  Formlabs doesn't publish a given number publicly for a specific material.
- Other brands: family/line-level entries (not full per-SKU precision),
  `brand`-tagged, same shape as today's generic list, `printerCompatibility`/
  `tankCompatibility` left empty.
- `_comment` field (matching `filament-library.json` convention) documents
  sourcing and the "some values approximate/unpublished" caveat.

### 2. Formlabs printer settings — installed tank

`settings.resinPrinters[i]` gains two fields, only shown/editable in
`formlabsModal` when the printer's URL is `formlabs://...`:

- `printerModel` — dropdown: Form 2, Form 3, Form 3B, Form 3+, Form 3B+,
  Form 3L, Form 3BL, Form 4, Form 4B, Form 4L.
- `tankType` — dropdown scoped to valid tanks for the selected
  `printerModel` (e.g. Form 4 family → "Form 4 Resin Tank"; Form 3 family →
  "Form 3 Resin Tank V2.1"; Form 2 → "Standard Tank" / "Tank LT").
  Represents what's physically installed *right now* — user updates it
  whenever they swap tanks.

Both fields are optional; a Formlabs printer added before this change (or a
user who skips the fields) simply never triggers the compatibility warning
for that printer, same as non-Formlabs printers.

### 3. Compatibility warning in the material modal

When the resin material modal opens for a session linked to a Formlabs
printer (`printerId` resolves to a `resinPrinters` entry with a `formlabs://`
URL) that has a `tankType` set, and the selected resin's `tankCompatibility`
list is non-empty and doesn't include that `tankType`:

Show an amber banner (visual language matching the existing FDM "Resume
Tracking" bar):

> ⚠ Tough 2000 Resin V2 requires the Form 4 Resin Tank — this printer is
> set to Form 3 Resin Tank V2.1.

Saving is never blocked. The banner only evaluates when both sides of the
comparison have data (resin has compatibility data *and* printer has a
`tankType` set) — otherwise no banner, no false positives.

### 4. Resin library browser

Replace the current flat `<select id="resinLibraryPicker">` (Settings →
Resin Types) with a modal:

- Text search box (matches `name`/`full`/`tags`).
- Brand filter (Formlabs / Elegoo / Siraya Tech / Phrozen / Anycubic /
  HeyGears / Generic).
- Each row: name, density, cost, and — for entries with `mechanical`/
  compatibility data — a compact spec line (tensile strength, compatible
  printer(s)/tank).
- "Use this resin" button adds the entry to `settings.resinTypes` exactly
  as the current picker does today; downstream behavior (material modal,
  cost calc, session log, invoices, ODS/XLSX export) is unchanged.

Existing `settings.resinTypes` entries and the migration logic already in
place for string→object resin types are untouched.

## Open implementation questions

- Exact per-material Formlabs specs (mechanical properties, tank
  requirements) need to be gathered from Formlabs' product/data-sheet pages
  for all ~48 materials — a substantial data-collection pass, best done as
  a batch research effort during implementation rather than by hand here.
  Where Formlabs doesn't publish a number (e.g. density on some SKUs),
  the field is `null` rather than guessed.
