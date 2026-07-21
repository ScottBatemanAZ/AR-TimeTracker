# Master Resin Library + Formlabs Tank Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 12-entry generic `resin-library.json` with an 84-material brand-tagged catalog (48 real-spec Formlabs SLA resins + 5 other brand families + the original 12 kept as "Generic"), add a Formlabs printer-model/tank-type setting, warn (non-blocking) in the material modal when a picked resin doesn't match the installed tank, and replace the flat resin picker with a searchable library browser.

**Architecture:** One new data file (`resin-library.json`, fully replaced) plus `index.html`-only changes — no `server.py` changes. Four mostly-independent slices, in dependency order: (1) the data file itself, (2) Formlabs printer settings gain `printerModel`/`tankType`, (3) a compatibility-warning banner in the material modal that reads what (2) stores, (4) the library browser modal that replaces the flat `<select>` picker. A final docs/version-bump task closes out the plan per this project's standing convention.

**Tech Stack:** Vanilla HTML/CSS/JS (single inline `<script>` block in `index.html`, no build step, no framework, no test runner) + one static JSON file served by the existing Python stdlib server.

## Global Constraints

- Every material's real-world data (Formlabs mechanical specs, tank/printer compatibility, pricing) was already researched and validated during the design phase — Task 1 embeds that exact, final content. Do not re-derive or re-fetch it.
- This project has no automated test suite. Each task's verification does two things, in order: (1) a Node.js syntax check of the inline `<script>` block, (2) a live check against the running dev server (`python server.py`, port 5757) using the Playwright MCP browser tools.
- Only `index.html` and `resin-library.json` are touched across this entire plan. No `server.py` changes.
- Follow existing code density/style inside the `<script>` block (compact, minimal whitespace, `const`/arrow functions) — don't reformat surrounding code you're not touching.
- New CSS rules go near the existing related rules they extend (e.g. new `.rlib-*` classes go next to `.type-add-row`/`.col-header` around `index.html:276-283`), not in a new isolated block.
- Modal dismiss-ability follows the existing two allow-lists:
  - `index.html:2511` — array of modal IDs closed by the `Escape` key.
  - `index.html:2515` — array of modal IDs closed by clicking the backdrop.
  - Both `resinLibraryModal` (Task 4) and `formlabsModal` (already present) are normal, non-blocking modals — add `resinLibraryModal` to both lists, matching `resinSourcesModal`'s precedent exactly.
- `settings.resinTypes` entries keep their existing shape (`{name, costPerKg, densityGPerMl}`) — nothing about how a resin type is stored, selected in the material modal, or flows into invoices/ODS/XLSX export changes. Only *how new entries get added* (Task 4) changes.
- Line numbers below were captured against the current file state at the start of this plan (most recent commit: `9517bf5`). If an earlier task in this plan shifts a later task's target lines, re-`grep` the anchor text quoted in that step before editing.

---

### Task 1: Replace `resin-library.json` with the master catalog

**Files:**
- Modify (full replace): `resin-library.json`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the `materials` array every later task reads via the existing `resinLibrary` global (populated by the existing `loadResinLibrary()` at `index.html:2865-2881`, unchanged in this task). Every material object has the shape: `{name, brand, full, densityGPerMl, typicalCostPerKg, tags, mechanical:{tensileStrengthMPa, elongationPct, flexuralModulusMPa, shoreHardness}, printerCompatibility:[], tankCompatibility:[]}`.

- [ ] **Step 1: Replace the file contents**

Overwrite `resin-library.json` (currently 89 lines, 12 materials) with the following (84 materials — 48 Formlabs with real per-SKU specs sourced from Formlabs' product pages/technical data sheets, 24 across Anycubic/Elegoo/Siraya Tech/Phrozen/HeyGears as family-level entries, and the original 12 generic entries kept under `brand: "Generic"` for backward compatibility with existing installs):

```json
{
  "_comment": "Resin reference library. densityGPerMl is the liquid (uncured) density used in cost calculations. Formlabs entries (brand: 'Formlabs') carry real per-SKU specs sourced from Formlabs' product pages and technical data sheets as of July 2026, including printerCompatibility (which Form-series printers run the material) and tankCompatibility (which resin tank/tray is required or recommended) -- Formlabs hardware-locks some materials to specific tanks per printer generation, so a compatible printer alone doesn't guarantee a compatible tank. Fields are null where Formlabs doesn't publish a number publicly for a given material -- never guessed. Other brands (Anycubic, Elegoo, Siraya Tech, Phrozen, HeyGears, and legacy 'Generic' entries) are family/line-level estimates only -- these printers aren't tank-locked, so mechanical/compatibility fields are intentionally empty for them. Costs are USD market prices/estimates -- override with your actual purchase price.",
  "materials": [
    {
      "name": "Alumina 4N Resin",
      "brand": "Formlabs",
      "full": "Formlabs Alumina 4N Resin",
      "densityGPerMl": 2.56,
      "typicalCostPerKg": 649.5,
      "tags": ["ceramic-filled", "engineering", "high-temperature"],
      "mechanical": { "tensileStrengthMPa": null, "elongationPct": null, "flexuralModulusMPa": null, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 3", "Form 3B"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 3 Resin Tank V2.1"]
    },
    {
      "name": "BEGO Varseo Smile TriniQ Resin",
      "brand": "Formlabs",
      "full": "Formlabs BEGO VarseoSmile TriniQ Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": 799,
      "tags": ["dental", "crown", "biocompatible"],
      "mechanical": { "tensileStrengthMPa": null, "elongationPct": null, "flexuralModulusMPa": 3600, "shoreHardness": null },
      "printerCompatibility": ["Form 4B"],
      "tankCompatibility": ["Form 4 Resin Tank"]
    },
    {
      "name": "BioMed Amber Resin",
      "brand": "Formlabs",
      "full": "Formlabs BioMed Amber Resin",
      "densityGPerMl": 1.09,
      "typicalCostPerKg": 228.44,
      "tags": ["biocompatible", "medical"],
      "mechanical": { "tensileStrengthMPa": 73, "elongationPct": 12, "flexuralModulusMPa": 2500, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL", "Form 3B", "Form 3BL", "Form 2"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank", "Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "BioMed Black Resin",
      "brand": "Formlabs",
      "full": "Formlabs BioMed Black Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["biocompatible", "medical"],
      "mechanical": { "tensileStrengthMPa": 36, "elongationPct": 14, "flexuralModulusMPa": 1668.53, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL", "Form 3B", "Form 3BL", "Form 2"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 2 Resin Tank (PDMS)", "Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "BioMed Clear Resin",
      "brand": "Formlabs",
      "full": "Formlabs BioMed Clear Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 317.27,
      "tags": ["biocompatible", "medical"],
      "mechanical": { "tensileStrengthMPa": 52, "elongationPct": 12, "flexuralModulusMPa": 2300, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL", "Form 3B", "Form 3BL", "Form 2"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank", "Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "BioMed Durable Resin",
      "brand": "Formlabs",
      "full": "Formlabs BioMed Durable Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["biocompatible", "medical", "engineering"],
      "mechanical": { "tensileStrengthMPa": 29.1, "elongationPct": 33, "flexuralModulusMPa": 643, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4BL", "Form 3", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "BioMed Flex 50A Resin",
      "brand": "Formlabs",
      "full": "Formlabs BioMed Flex 50A Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["biocompatible", "medical", "flexible"],
      "mechanical": { "tensileStrengthMPa": 2.3, "elongationPct": 150, "flexuralModulusMPa": null, "shoreHardness": "50A" },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4BL", "Form 3", "Form 3B", "Form 3BL", "Form 3L", "Form 4L"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "BioMed Flex 80A Resin",
      "brand": "Formlabs",
      "full": "Formlabs BioMed Flex 80A Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["biocompatible", "medical", "flexible"],
      "mechanical": { "tensileStrengthMPa": 7.2, "elongationPct": 135, "flexuralModulusMPa": null, "shoreHardness": "80A" },
      "printerCompatibility": ["Form 4B", "Form 4BL", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "BioMed White Resin",
      "brand": "Formlabs",
      "full": "Formlabs BioMed White Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["biocompatible", "medical"],
      "mechanical": { "tensileStrengthMPa": 45.78, "elongationPct": 10, "flexuralModulusMPa": 2020.16, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL", "Form 3B", "Form 3BL", "Form 2"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 2 Resin Tank (PDMS)", "Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "Black Resin V5",
      "brand": "Formlabs",
      "full": "Formlabs Black Resin V5",
      "densityGPerMl": 1.11,
      "typicalCostPerKg": 71.17,
      "tags": ["general-purpose", "common", "rigid", "beginner"],
      "mechanical": { "tensileStrengthMPa": 61, "elongationPct": 10, "flexuralModulusMPa": 2750, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Castable Wax 40 Resin",
      "brand": "Formlabs",
      "full": "Formlabs Castable Wax 40 Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["casting", "jewelry", "wax"],
      "mechanical": { "tensileStrengthMPa": null, "elongationPct": null, "flexuralModulusMPa": null, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 3", "Form 3B", "Form 3+", "Form 3B+", "Form 2"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 3 Resin Tank V2.1", "Form 2 Resin Tank (PDMS)"]
    },
    {
      "name": "Castable Wax Resin",
      "brand": "Formlabs",
      "full": "Formlabs Castable Wax Resin",
      "densityGPerMl": 1.11,
      "typicalCostPerKg": 269,
      "tags": ["casting", "jewelry", "wax"],
      "mechanical": { "tensileStrengthMPa": 11.6, "elongationPct": 13, "flexuralModulusMPa": null, "shoreHardness": null },
      "printerCompatibility": ["Form 2", "Form 3", "Form 3B", "Form 3L", "Form 3BL", "Form 4", "Form 4B"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 2 Resin Tank (PDMS)", "Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "Ceramic Resin",
      "brand": "Formlabs",
      "full": "Formlabs Ceramic Resin",
      "densityGPerMl": 1.7,
      "typicalCostPerKg": 88,
      "tags": ["ceramic", "specialty", "experimental"],
      "mechanical": { "tensileStrengthMPa": 5.1, "elongationPct": 1.4, "flexuralModulusMPa": 995, "shoreHardness": null },
      "printerCompatibility": ["Form 2"],
      "tankCompatibility": ["Form 2 Resin Tank (PDMS)"]
    },
    {
      "name": "Clear Cast Resin",
      "brand": "Formlabs",
      "full": "Formlabs Clear Cast Resin",
      "densityGPerMl": 1.09,
      "typicalCostPerKg": 137,
      "tags": ["casting", "investment-casting", "rigid"],
      "mechanical": { "tensileStrengthMPa": 65, "elongationPct": 6, "flexuralModulusMPa": 2200, "shoreHardness": null },
      "printerCompatibility": ["Form 2", "Form 3", "Form 3B", "Form 3+", "Form 3B+", "Form 3L", "Form 3BL", "Form 4", "Form 4B", "Form 4L", "Form 4BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "Clear Resin V5",
      "brand": "Formlabs",
      "full": "Formlabs Clear Resin V5",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["transparent", "high-detail", "common", "optical"],
      "mechanical": { "tensileStrengthMPa": 60, "elongationPct": 8, "flexuralModulusMPa": 2700, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Color Base Resin",
      "brand": "Formlabs",
      "full": "Formlabs Color Base Resin",
      "densityGPerMl": 1.08,
      "typicalCostPerKg": 91,
      "tags": ["general-purpose", "colorable", "rigid"],
      "mechanical": { "tensileStrengthMPa": 65, "elongationPct": 6, "flexuralModulusMPa": 2200, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL", "Form 3", "Form 3L", "Form 3B", "Form 3BL", "Form 2"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 2 Resin Tank (PDMS)", "Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "Color Resin",
      "brand": "Formlabs",
      "full": "Formlabs Color Resin",
      "densityGPerMl": 1.11,
      "typicalCostPerKg": 89,
      "tags": ["general-purpose", "colorable", "rigid"],
      "mechanical": { "tensileStrengthMPa": 54, "elongationPct": 15, "flexuralModulusMPa": 2450, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4L"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Custom Tray Resin",
      "brand": "Formlabs",
      "full": "Formlabs Custom Tray Resin",
      "densityGPerMl": 1.09,
      "typicalCostPerKg": 228.44,
      "tags": ["biocompatible", "dental", "engineering"],
      "mechanical": { "tensileStrengthMPa": 70, "elongationPct": 3, "flexuralModulusMPa": 2600, "shoreHardness": null },
      "printerCompatibility": ["Form 2", "Form 4B", "Form 4BL", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3", "Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Dental LT Clear Resin",
      "brand": "Formlabs",
      "full": "Formlabs Dental LT Clear Resin V2",
      "densityGPerMl": 1.09,
      "typicalCostPerKg": 320,
      "tags": ["dental", "biocompatible", "clear"],
      "mechanical": { "tensileStrengthMPa": 52, "elongationPct": 12, "flexuralModulusMPa": 2300, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3", "Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Dental LT Comfort Resin",
      "brand": "Formlabs",
      "full": "Formlabs Dental LT Comfort Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["dental", "biocompatible", "flexible"],
      "mechanical": { "tensileStrengthMPa": 29.1, "elongationPct": 33, "flexuralModulusMPa": 643, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3", "Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Denture Base Resin",
      "brand": "Formlabs",
      "full": "Formlabs Denture Base Resin V2",
      "densityGPerMl": 1.15,
      "typicalCostPerKg": 477,
      "tags": ["dental", "denture", "biocompatible"],
      "mechanical": { "tensileStrengthMPa": 57, "elongationPct": null, "flexuralModulusMPa": 2200, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL"],
      "tankCompatibility": ["Form 4 Resin Tank"]
    },
    {
      "name": "Draft Resin",
      "brand": "Formlabs",
      "full": "Formlabs Draft Resin V2",
      "densityGPerMl": 1.12,
      "typicalCostPerKg": 133.04,
      "tags": ["rapid-prototyping", "fast-print", "draft"],
      "mechanical": { "tensileStrengthMPa": 52, "elongationPct": 4, "flexuralModulusMPa": 2300, "shoreHardness": null },
      "printerCompatibility": ["Form 2", "Form 3", "Form 3+", "Form 3B", "Form 3B+", "Form 3L", "Form 3BL"],
      "tankCompatibility": ["Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3", "Form 2 LT Tank"]
    },
    {
      "name": "Durable Resin",
      "brand": "Formlabs",
      "full": "Formlabs Durable Resin V2",
      "densityGPerMl": 1.06,
      "typicalCostPerKg": 140.57,
      "tags": ["impact-resistant", "pliable", "low-friction"],
      "mechanical": { "tensileStrengthMPa": 28, "elongationPct": 55, "flexuralModulusMPa": 660, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL", "Form 3", "Form 3L", "Form 3B", "Form 3BL", "Form 2"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 3 Resin Tank V2.1", "Form 2 Resin Tank (PDMS)", "Form 2 LT Tank"]
    },
    {
      "name": "Elastic 50A Resin V1",
      "brand": "Formlabs",
      "full": "Formlabs Elastic 50A Resin V1",
      "densityGPerMl": 1,
      "typicalCostPerKg": 199,
      "tags": ["flexible", "elastomer", "discontinued"],
      "mechanical": { "tensileStrengthMPa": 3.23, "elongationPct": 160, "flexuralModulusMPa": null, "shoreHardness": "50A" },
      "printerCompatibility": ["Form 2", "Form 3", "Form 3B", "Form 3+", "Form 3B+", "Form 3L", "Form 3BL"],
      "tankCompatibility": ["Form 2 Resin Tank (PDMS)", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "ESD Resin",
      "brand": "Formlabs",
      "full": "Formlabs ESD Resin",
      "densityGPerMl": 1.116,
      "typicalCostPerKg": 205,
      "tags": ["specialty", "electronics", "rigid"],
      "mechanical": { "tensileStrengthMPa": 44.2, "elongationPct": 12, "flexuralModulusMPa": 1841, "shoreHardness": "90D" },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL", "Form 3", "Form 3L", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "Fast Model Resin",
      "brand": "Formlabs",
      "full": "Formlabs Fast Model Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["dental", "model"],
      "mechanical": { "tensileStrengthMPa": 62, "elongationPct": 11, "flexuralModulusMPa": 2740, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Flame Retardant Resin",
      "brand": "Formlabs",
      "full": "Formlabs Flame Retardant Resin",
      "densityGPerMl": 1.25,
      "typicalCostPerKg": 249,
      "tags": ["specialty", "flame-retardant", "rigid"],
      "mechanical": { "tensileStrengthMPa": 41, "elongationPct": 7.1, "flexuralModulusMPa": 2700, "shoreHardness": "80D" },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL", "Form 3", "Form 3L", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "Flexible 50A Resin",
      "brand": "Formlabs",
      "full": "Formlabs Flexible 50A Resin",
      "densityGPerMl": 1.01,
      "typicalCostPerKg": 197,
      "tags": ["flexible", "elastomer"],
      "mechanical": { "tensileStrengthMPa": 3.4, "elongationPct": 160, "flexuralModulusMPa": null, "shoreHardness": "55A" },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL", "Form 3", "Form 3L", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "Flexible 80A Resin V2",
      "brand": "Formlabs",
      "full": "Formlabs Flexible 80A Resin V2",
      "densityGPerMl": 1.12,
      "typicalCostPerKg": 178,
      "tags": ["flexible", "elastomer", "engineering"],
      "mechanical": { "tensileStrengthMPa": 10.9, "elongationPct": 230, "flexuralModulusMPa": null, "shoreHardness": "80A" },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Grey Pro Resin",
      "brand": "Formlabs",
      "full": "Formlabs Grey Pro Resin",
      "densityGPerMl": 1.07,
      "typicalCostPerKg": 195.33,
      "tags": ["engineering", "precision", "low-creep"],
      "mechanical": { "tensileStrengthMPa": 61, "elongationPct": 13, "flexuralModulusMPa": 2200, "shoreHardness": null },
      "printerCompatibility": ["Form 3", "Form 3L", "Form 3B", "Form 3BL", "Form 2"],
      "tankCompatibility": ["Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3", "Form 2 LT Tank"]
    },
    {
      "name": "Grey Resin V5",
      "brand": "Formlabs",
      "full": "Formlabs Grey Resin V5",
      "densityGPerMl": 1.11,
      "typicalCostPerKg": 71.17,
      "tags": ["general-purpose", "common", "rigid", "beginner"],
      "mechanical": { "tensileStrengthMPa": 62, "elongationPct": 13, "flexuralModulusMPa": 2750, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "High Temp Resin",
      "brand": "Formlabs",
      "full": "Formlabs High Temp Resin",
      "densityGPerMl": 1.14,
      "typicalCostPerKg": 175,
      "tags": ["high-temp", "engineering", "rigid"],
      "mechanical": { "tensileStrengthMPa": 58.3, "elongationPct": 3.3, "flexuralModulusMPa": 2620, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL", "Form 3", "Form 3L", "Form 3B", "Form 3BL", "Form 2"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 2 Resin Tank (PDMS)", "Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "IBT Flex Resin",
      "brand": "Formlabs",
      "full": "Formlabs IBT Flex Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["dental", "orthodontic", "flexible", "biocompatible"],
      "mechanical": { "tensileStrengthMPa": 7.2, "elongationPct": 135, "flexuralModulusMPa": null, "shoreHardness": "80A" },
      "printerCompatibility": ["Form 4B", "Form 4BL", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3", "Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Model V2 Resin",
      "brand": "Formlabs",
      "full": "Formlabs Model Resin V2",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["dental", "model", "legacy"],
      "mechanical": { "tensileStrengthMPa": 61, "elongationPct": 5, "flexuralModulusMPa": 2500, "shoreHardness": null },
      "printerCompatibility": ["Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "Model V3 Resin",
      "brand": "Formlabs",
      "full": "Formlabs Model Resin V3",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["dental", "model"],
      "mechanical": { "tensileStrengthMPa": 48, "elongationPct": 4.8, "flexuralModulusMPa": 2200, "shoreHardness": null },
      "printerCompatibility": ["Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3"]
    },
    {
      "name": "Permanent Crown Resin",
      "brand": "Formlabs",
      "full": "Formlabs Permanent Crown Resin V1",
      "densityGPerMl": 1.45,
      "typicalCostPerKg": null,
      "tags": ["dental", "crown", "biocompatible", "discontinued"],
      "mechanical": { "tensileStrengthMPa": null, "elongationPct": null, "flexuralModulusMPa": 4090, "shoreHardness": null },
      "printerCompatibility": ["Form 3B"],
      "tankCompatibility": ["Form 3 Resin Tank V2.1"]
    },
    {
      "name": "Precision Model Resin",
      "brand": "Formlabs",
      "full": "Formlabs Precision Model Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["dental", "model"],
      "mechanical": { "tensileStrengthMPa": 50, "elongationPct": 8.6, "flexuralModulusMPa": 2300, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Premium Teeth Resin",
      "brand": "Formlabs",
      "full": "Formlabs Premium Teeth Resin",
      "densityGPerMl": 1.23,
      "typicalCostPerKg": 559,
      "tags": ["dental", "denture", "biocompatible"],
      "mechanical": { "tensileStrengthMPa": null, "elongationPct": null, "flexuralModulusMPa": 4300, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3", "Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Rigid 10K Resin",
      "brand": "Formlabs",
      "full": "Formlabs Rigid 10K Resin",
      "densityGPerMl": 1.6,
      "typicalCostPerKg": 186.88,
      "tags": ["engineering", "rigid", "industrial", "heat-resistant"],
      "mechanical": { "tensileStrengthMPa": 65, "elongationPct": 1, "flexuralModulusMPa": 9000, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL", "Form 3", "Form 3L", "Form 3B", "Form 3BL", "Form 2"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3", "Form 2 LT Tank"]
    },
    {
      "name": "Rigid 4000 Resin",
      "brand": "Formlabs",
      "full": "Formlabs Rigid 4000 Resin",
      "densityGPerMl": 1.25,
      "typicalCostPerKg": 183.2,
      "tags": ["engineering", "rigid", "stiff"],
      "mechanical": { "tensileStrengthMPa": 69, "elongationPct": 5.3, "flexuralModulusMPa": 3400, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL", "Form 3", "Form 3L", "Form 3B", "Form 3BL", "Form 2"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3", "Form 2 LT Tank"]
    },
    {
      "name": "Silicone 40A Resin",
      "brand": "Formlabs",
      "full": "Formlabs Silicone 40A Resin",
      "densityGPerMl": 1.04,
      "typicalCostPerKg": 336,
      "tags": ["silicone", "flexible", "elastomer", "specialty"],
      "mechanical": { "tensileStrengthMPa": 5, "elongationPct": 230, "flexuralModulusMPa": null, "shoreHardness": "40A" },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 3", "Form 3B"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 3 Resin Tank V2.1"]
    },
    {
      "name": "Surgical Guide Resin",
      "brand": "Formlabs",
      "full": "Formlabs Surgical Guide Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["dental", "surgical", "biocompatible"],
      "mechanical": { "tensileStrengthMPa": null, "elongationPct": 12, "flexuralModulusMPa": 2400, "shoreHardness": null },
      "printerCompatibility": ["Form 4B", "Form 4BL", "Form 3B", "Form 3BL"],
      "tankCompatibility": ["Form 2 LT Tank", "Form 3 Resin Tank V2.1", "Form 3L Resin Tank V3", "Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Temporary CB Resin",
      "brand": "Formlabs",
      "full": "Formlabs Temporary CB Resin V1",
      "densityGPerMl": 1.45,
      "typicalCostPerKg": 572,
      "tags": ["dental", "temporary", "biocompatible", "discontinued"],
      "mechanical": { "tensileStrengthMPa": null, "elongationPct": null, "flexuralModulusMPa": null, "shoreHardness": null },
      "printerCompatibility": ["Form 3B", "Form 2"],
      "tankCompatibility": ["Form 3 Resin Tank V2.1", "Form 2 LT Tank"]
    },
    {
      "name": "Tough 1000 Resin",
      "brand": "Formlabs",
      "full": "Formlabs Tough 1000 Resin",
      "densityGPerMl": 1.01,
      "typicalCostPerKg": 147.52,
      "tags": ["engineering", "impact-resistant", "ductile"],
      "mechanical": { "tensileStrengthMPa": 26.3, "elongationPct": 180, "flexuralModulusMPa": 761, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Tough 1500 Resin V2",
      "brand": "Formlabs",
      "full": "Formlabs Tough 1500 Resin V2",
      "densityGPerMl": 1.02,
      "typicalCostPerKg": 146.08,
      "tags": ["engineering", "impact-resistant", "resilient"],
      "mechanical": { "tensileStrengthMPa": 34, "elongationPct": 155, "flexuralModulusMPa": 1370, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4L"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "Tough 2000 Resin V2",
      "brand": "Formlabs",
      "full": "Formlabs Tough 2000 Resin V2",
      "densityGPerMl": 1.03,
      "typicalCostPerKg": 144.66,
      "tags": ["engineering", "impact-resistant", "common"],
      "mechanical": { "tensileStrengthMPa": 40.4, "elongationPct": 79, "flexuralModulusMPa": 1701, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4L"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "True Cast Resin",
      "brand": "Formlabs",
      "full": "Formlabs True Cast Resin",
      "densityGPerMl": null,
      "typicalCostPerKg": null,
      "tags": ["casting", "jewelry", "wax"],
      "mechanical": { "tensileStrengthMPa": null, "elongationPct": null, "flexuralModulusMPa": null, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B"],
      "tankCompatibility": ["Form 4 Resin Tank"]
    },
    {
      "name": "White Resin V5",
      "brand": "Formlabs",
      "full": "Formlabs White Resin V5",
      "densityGPerMl": 1.11,
      "typicalCostPerKg": 71.17,
      "tags": ["general-purpose", "common", "rigid", "beginner"],
      "mechanical": { "tensileStrengthMPa": 62, "elongationPct": 13, "flexuralModulusMPa": 2750, "shoreHardness": null },
      "printerCompatibility": ["Form 4", "Form 4B", "Form 4L", "Form 4BL"],
      "tankCompatibility": ["Form 4 Resin Tank", "Form 4L Resin Tank"]
    },
    {
      "name": "ABS-Like Resin",
      "brand": "Anycubic",
      "full": "Anycubic ABS-Like Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 30,
      "tags": ["durable", "matte-finish", "functional-parts"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Plant-Based UV Eco-Resin",
      "brand": "Anycubic",
      "full": "Anycubic Plant-Based UV Eco-Resin",
      "densityGPerMl": 1.05,
      "typicalCostPerKg": 30,
      "tags": ["eco", "plant-based", "low-odor"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Standard Resin",
      "brand": "Anycubic",
      "full": "Anycubic Standard Photopolymer Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 25,
      "tags": ["beginner", "common", "affordable"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Water-Wash ABS-Like Resin 3.0",
      "brand": "Anycubic",
      "full": "Anycubic Water-Wash ABS-Like Resin 3.0",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 28,
      "tags": ["water-washable", "durable", "functional-parts"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Water-Wash Resin+",
      "brand": "Anycubic",
      "full": "Anycubic Water-Wash Resin+ / 2.0",
      "densityGPerMl": 1.08,
      "typicalCostPerKg": 20,
      "tags": ["water-washable", "low-odor", "eco"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "8K Standard Resin",
      "brand": "Elegoo",
      "full": "Elegoo 8K Standard Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 17,
      "tags": ["high-detail", "value", "large-format"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "8K Water-Washable ABS-Like Resin",
      "brand": "Elegoo",
      "full": "Elegoo 8K Water-Washable ABS-Like Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 28,
      "tags": ["high-detail", "water-washable", "durable", "impact-resistant"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Standard Resin",
      "brand": "Elegoo",
      "full": "Elegoo Standard Photopolymer Resin V2.0",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 20,
      "tags": ["beginner", "common", "affordable"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Water-Washable ABS-Like Resin",
      "brand": "Elegoo",
      "full": "Elegoo Water-Washable ABS-Like Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 25,
      "tags": ["water-washable", "durable", "functional-parts"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Water-Washable Resin V2.0",
      "brand": "Elegoo",
      "full": "Elegoo Water-Washable Resin V2.0",
      "densityGPerMl": 1.08,
      "typicalCostPerKg": 22,
      "tags": ["water-washable", "low-odor", "common"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "ABS-Like Resin",
      "brand": "HeyGears",
      "full": "HeyGears ABS-Like Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 44,
      "tags": ["durable", "functional-parts", "engineering"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Clear Resin",
      "brand": "HeyGears",
      "full": "HeyGears Clear Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 50,
      "tags": ["transparent", "anti-yellowing", "specialty"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Flexible Resin",
      "brand": "HeyGears",
      "full": "HeyGears UltraPrint-Production PAF10 Flexible Resin",
      "densityGPerMl": 1.05,
      "typicalCostPerKg": 38,
      "tags": ["flexible", "durable", "prototyping"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Modeling Resin",
      "brand": "HeyGears",
      "full": "HeyGears UltraPrint-Modeling Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 45,
      "tags": ["high-detail", "figurines", "matte-finish"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "ABS-Like Resin (Beige/Creamy White)",
      "brand": "Phrozen",
      "full": "Phrozen ABS-Like Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 15,
      "tags": ["durable", "functional-parts", "matte-finish"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Aqua 8K Resin",
      "brand": "Phrozen",
      "full": "Phrozen Aqua 8K Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 24,
      "tags": ["high-detail", "common"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Aqua Resin",
      "brand": "Phrozen",
      "full": "Phrozen Aqua 3D Printing Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 22,
      "tags": ["standard", "common", "affordable"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Speed Resin",
      "brand": "Phrozen",
      "full": "Phrozen Speed Resin (high-speed line)",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 40,
      "tags": ["high-speed", "large-format", "prototyping"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Water-Washable Resin",
      "brand": "Phrozen",
      "full": "Phrozen Standard Water-Washable Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 20,
      "tags": ["water-washable", "low-odor", "common"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Blu",
      "brand": "Siraya Tech",
      "full": "Siraya Tech Blu Resin",
      "densityGPerMl": 1.09,
      "typicalCostPerKg": 28,
      "tags": ["standard", "beginner", "affordable"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Fast",
      "brand": "Siraya Tech",
      "full": "Siraya Tech Fast Resin (ABS-Like)",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 33,
      "tags": ["fast-curing", "abs-like", "common"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Sculpt",
      "brand": "Siraya Tech",
      "full": "Siraya Tech Sculpt Resin",
      "densityGPerMl": 1.4,
      "typicalCostPerKg": 35,
      "tags": ["high-detail", "low-shrinkage", "engineering"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Tenacious",
      "brand": "Siraya Tech",
      "full": "Siraya Tech Tenacious Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 40,
      "tags": ["engineering", "impact-resistant", "tough"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Tenacious 65D Flexible",
      "brand": "Siraya Tech",
      "full": "Siraya Tech Tenacious 65D Flexible Resin",
      "densityGPerMl": 1.08,
      "typicalCostPerKg": 38,
      "tags": ["flexible", "tough", "engineering"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "8K / High-Detail",
      "brand": "Generic",
      "full": "8K High-Resolution Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 35,
      "tags": ["detail", "precision"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "ABS-Like",
      "brand": "Generic",
      "full": "ABS-Like Photopolymer Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 28,
      "tags": ["common", "durable"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Castable / Wax",
      "brand": "Generic",
      "full": "Castable Wax Resin (Jewelry / Burnout)",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 65,
      "tags": ["specialty", "jewelry", "casting"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Ceramic / Engineering",
      "brand": "Generic",
      "full": "Ceramic-Filled or Mineral-Filled Engineering Resin",
      "densityGPerMl": 1.4,
      "typicalCostPerKg": 90,
      "tags": ["engineering", "specialty", "heavy"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Dental Model",
      "brand": "Generic",
      "full": "Dental Model / Biocompatible Resin",
      "densityGPerMl": 1.15,
      "typicalCostPerKg": 110,
      "tags": ["dental", "specialty", "biocompatible"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Flexible",
      "brand": "Generic",
      "full": "Flexible / Rubber-Like Resin (65D)",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 42,
      "tags": ["flexible", "specialty"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "High-Temp",
      "brand": "Generic",
      "full": "High-Temperature Engineering Resin",
      "densityGPerMl": 1.12,
      "typicalCostPerKg": 80,
      "tags": ["engineering", "specialty"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Plant-Based",
      "brand": "Generic",
      "full": "Plant-Based / Bio-Resin",
      "densityGPerMl": 1.08,
      "typicalCostPerKg": 28,
      "tags": ["eco", "low-odor"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Standard",
      "brand": "Generic",
      "full": "Standard Photopolymer Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 22,
      "tags": ["beginner", "common"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Tough",
      "brand": "Generic",
      "full": "Tough / Impact-Resistant Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 45,
      "tags": ["durable", "engineering"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Water-Washable",
      "brand": "Generic",
      "full": "Water-Washable Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 28,
      "tags": ["common", "eco"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    },
    {
      "name": "Water-Washable ABS-Like",
      "brand": "Generic",
      "full": "Water-Washable ABS-Like Resin",
      "densityGPerMl": 1.1,
      "typicalCostPerKg": 32,
      "tags": ["common", "durable", "eco"],
      "mechanical": {},
      "printerCompatibility": [],
      "tankCompatibility": []
    }
  ]
}
```

- [ ] **Step 2: Validate the JSON and material counts**

```bash
cd "r:/Azazel's Razer/timetracker"
node -e "
const d = JSON.parse(require('fs').readFileSync('resin-library.json','utf8'));
const byBrand = {};
d.materials.forEach(m => byBrand[m.brand] = (byBrand[m.brand]||0)+1);
console.log('total:', d.materials.length);
console.log('by brand:', JSON.stringify(byBrand));
const dupes = new Set(); const seen = new Set();
d.materials.forEach(m => { const k = m.brand+'::'+m.name; if (seen.has(k)) dupes.add(k); seen.add(k); });
console.log('duplicate brand::name pairs:', [...dupes]);
"
```
Expected: `total: 84`, `by brand: {"Formlabs":48,"Anycubic":5,"Elegoo":5,"HeyGears":4,"Phrozen":5,"Siraya Tech":5,"Generic":12}`, `duplicate brand::name pairs: []`.

- [ ] **Step 3: Commit**

```bash
cd "r:/Azazel's Razer/timetracker"
git add resin-library.json
git commit -m "$(cat <<'EOF'
feat: expand resin-library.json to a brand-tagged master catalog

The 12-entry generic library didn't reflect what people actually buy —
named, branded resins with real mechanical specs. Adds the full ~48-
material Formlabs catalog (engineering/prototyping + dental/ortho/
BioMed lines) with real per-SKU density/tensile/elongation/flexural-
modulus/shore-hardness plus printer and resin-tank compatibility
(Formlabs hardware-locks some materials to specific tanks per printer
generation), and family-level entries for Anycubic, Elegoo, Siraya
Tech, Phrozen, and HeyGears. Original 12 generic entries kept under
brand: "Generic" for backward compatibility with existing installs.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Formlabs printer model + installed tank setting

**Files:**
- Modify: `index.html:786-815` (`formlabsModal` HTML — add two new fields)
- Modify: `index.html:1273-1332` (`_flParseUrl`, `_flBuildUrl`, `openFormlabsModal`, `saveFormlabsPrinter`)

**Interfaces:**
- Consumes: nothing from Task 1 directly (this task is settings-only; Task 3 is what reads the library data alongside this task's output).
- Produces: `_flParseUrl(url)` now also returns `printerModel` and `tankType` (empty string if unset). `_flBuildUrl(serial, clientId, clientSecret, printerModel, tankType)` — two new trailing params, both optional (omitted from the URL's query string when falsy, so old-format URLs without them keep working). New `FORMLABS_TANK_OPTIONS` object (keyed by printer model, value = array of valid tank name strings) and `FORMLABS_PRINTER_MODELS` array (its keys) — Task 3 reads `FORMLABS_TANK_OPTIONS` implicitly through the parsed `tankType` string, no direct dependency. New `populateFlTankOptions(model, selectedTank)` function.

- [ ] **Step 1: Add the tank/model lookup table**

Find (`index.html:1273`, right before `_flParseUrl`):
```js
function _flParseUrl(url) {
```

Insert immediately before it:
```js
const FORMLABS_TANK_OPTIONS = {
  'Form 2':   ['Form 2 Resin Tank (PDMS)', 'Form 2 LT Tank'],
  'Form 3':   ['Form 3 Resin Tank V2.1'],
  'Form 3B':  ['Form 3 Resin Tank V2.1'],
  'Form 3+':  ['Form 3 Resin Tank V2.1'],
  'Form 3B+': ['Form 3 Resin Tank V2.1'],
  'Form 3L':  ['Form 3L Resin Tank V3'],
  'Form 3BL': ['Form 3L Resin Tank V3'],
  'Form 4':   ['Form 4 Resin Tank'],
  'Form 4B':  ['Form 4 Resin Tank'],
  'Form 4L':  ['Form 4L Resin Tank'],
  'Form 4BL': ['Form 4L Resin Tank'],
};
const FORMLABS_PRINTER_MODELS = Object.keys(FORMLABS_TANK_OPTIONS);
function populateFlTankOptions(model, selectedTank) {
  const sel = document.getElementById('flTankType');
  const options = FORMLABS_TANK_OPTIONS[model] || [];
  sel.innerHTML = '<option value="">— not set —</option>' +
    options.map(t => `<option value="${esc(t)}"${t===selectedTank?' selected':''}>${esc(t)}</option>`).join('');
}
```

- [ ] **Step 2: Extend `_flParseUrl` and `_flBuildUrl` with the two new fields**

Find (`index.html:1273-1282`):
```js
function _flParseUrl(url) {
  try {
    const u = new URL(url);
    const serial = u.hostname || u.pathname.replace(/^\/+/, '');
    return { serial, clientId: u.searchParams.get('client_id')||'', clientSecret: u.searchParams.get('client_secret')||'' };
  } catch { return { serial:'', clientId:'', clientSecret:'' }; }
}
function _flBuildUrl(serial, clientId, clientSecret) {
  return `formlabs://${encodeURIComponent(serial)}?client_id=${encodeURIComponent(clientId)}&client_secret=${encodeURIComponent(clientSecret)}`;
}
```

Replace with:
```js
function _flParseUrl(url) {
  try {
    const u = new URL(url);
    const serial = u.hostname || u.pathname.replace(/^\/+/, '');
    return {
      serial, clientId: u.searchParams.get('client_id')||'', clientSecret: u.searchParams.get('client_secret')||'',
      printerModel: u.searchParams.get('printer_model')||'', tankType: u.searchParams.get('tank_type')||''
    };
  } catch { return { serial:'', clientId:'', clientSecret:'', printerModel:'', tankType:'' }; }
}
function _flBuildUrl(serial, clientId, clientSecret, printerModel, tankType) {
  let url = `formlabs://${encodeURIComponent(serial)}?client_id=${encodeURIComponent(clientId)}&client_secret=${encodeURIComponent(clientSecret)}`;
  if (printerModel) url += `&printer_model=${encodeURIComponent(printerModel)}`;
  if (tankType) url += `&tank_type=${encodeURIComponent(tankType)}`;
  return url;
}
```

- [ ] **Step 3: Add the two fields to `formlabsModal`**

Find (`index.html:806-809`):
```html
    <div class="form-row" style="margin-bottom:0;">
      <label class="form-label">⚡ Watts (optional)</label>
      <input type="number" id="flWatts" placeholder="W" min="0" step="10" />
    </div>
```

Replace with:
```html
    <div class="form-row">
      <label class="form-label">⚡ Watts (optional)</label>
      <input type="number" id="flWatts" placeholder="W" min="0" step="10" />
    </div>
    <div class="form-row">
      <label class="form-label">Printer Model (optional)</label>
      <select id="flPrinterModel" style="font-family:var(--mono);font-size:11px;background:var(--surface2);border:1px solid var(--border2);color:var(--text);border-radius:4px;padding:5px 8px;" onchange="populateFlTankOptions(this.value,'')">
        <option value="">— not set —</option>
      </select>
    </div>
    <div class="form-row" style="margin-bottom:0;">
      <label class="form-label">Installed Tank (optional)</label>
      <select id="flTankType" style="font-family:var(--mono);font-size:11px;background:var(--surface2);border:1px solid var(--border2);color:var(--text);border-radius:4px;padding:5px 8px;">
        <option value="">— not set —</option>
      </select>
      <div class="form-hint">Used to warn if a picked resin doesn't match what's loaded — set both to enable.</div>
    </div>
```

- [ ] **Step 4: Populate the model dropdown once at load, and wire `openFormlabsModal`/`saveFormlabsPrinter`**

Find (`index.html:1284-1311`):
```js
function openFormlabsModal(idx) {
  editingFormlabsIdx = (typeof idx === 'number') ? idx : null;
  const hint = document.getElementById('flSecretHint');
  const secretEl = document.getElementById('flClientSecret');
  if (editingFormlabsIdx !== null) {
    const p = settings.resinPrinters[editingFormlabsIdx];
    const parsed = _flParseUrl(p.moonrakerUrl);
    document.getElementById('formlabsModalTitle').textContent = 'Edit Formlabs Printer';
    document.getElementById('flName').value = p.name;
    document.getElementById('flSerial').value = parsed.serial;
    document.getElementById('flClientId').value = parsed.clientId;
    secretEl.value = ''; secretEl.placeholder = '••••••••';
    document.getElementById('flWatts').value = p.wattage||'';
    document.getElementById('flSaveBtn').textContent = 'Save Changes';
    hint.style.display = '';
  } else {
    document.getElementById('formlabsModalTitle').textContent = 'Add Formlabs Printer';
    document.getElementById('flName').value = '';
    document.getElementById('flSerial').value = '';
    document.getElementById('flClientId').value = '';
    secretEl.value = ''; secretEl.placeholder = '';
    document.getElementById('flWatts').value = '';
    document.getElementById('flSaveBtn').textContent = 'Add Printer';
    hint.style.display = 'none';
  }
  document.getElementById('formlabsModal').classList.add('open');
  setTimeout(()=>document.getElementById('flName').focus(),50);
}
```

Replace with:
```js
function openFormlabsModal(idx) {
  editingFormlabsIdx = (typeof idx === 'number') ? idx : null;
  const hint = document.getElementById('flSecretHint');
  const secretEl = document.getElementById('flClientSecret');
  const modelSel = document.getElementById('flPrinterModel');
  if (!modelSel.options.length || modelSel.options.length === 1) {
    modelSel.innerHTML = '<option value="">— not set —</option>' +
      FORMLABS_PRINTER_MODELS.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
  }
  if (editingFormlabsIdx !== null) {
    const p = settings.resinPrinters[editingFormlabsIdx];
    const parsed = _flParseUrl(p.moonrakerUrl);
    document.getElementById('formlabsModalTitle').textContent = 'Edit Formlabs Printer';
    document.getElementById('flName').value = p.name;
    document.getElementById('flSerial').value = parsed.serial;
    document.getElementById('flClientId').value = parsed.clientId;
    secretEl.value = ''; secretEl.placeholder = '••••••••';
    document.getElementById('flWatts').value = p.wattage||'';
    modelSel.value = parsed.printerModel;
    populateFlTankOptions(parsed.printerModel, parsed.tankType);
    document.getElementById('flSaveBtn').textContent = 'Save Changes';
    hint.style.display = '';
  } else {
    document.getElementById('formlabsModalTitle').textContent = 'Add Formlabs Printer';
    document.getElementById('flName').value = '';
    document.getElementById('flSerial').value = '';
    document.getElementById('flClientId').value = '';
    secretEl.value = ''; secretEl.placeholder = '';
    document.getElementById('flWatts').value = '';
    modelSel.value = '';
    populateFlTankOptions('', '');
    document.getElementById('flSaveBtn').textContent = 'Add Printer';
    hint.style.display = 'none';
  }
  document.getElementById('formlabsModal').classList.add('open');
  setTimeout(()=>document.getElementById('flName').focus(),50);
}
```

Then find (`index.html:1312-1333`):
```js
function saveFormlabsPrinter() {
  const name = document.getElementById('flName').value.trim();
  const serial = document.getElementById('flSerial').value.trim();
  const clientId = document.getElementById('flClientId').value.trim();
  const secretInput = document.getElementById('flClientSecret').value.trim();
  const watts = parseFloat(document.getElementById('flWatts').value) || 0;
  if (!name || !serial || !clientId) return;
  let clientSecret = secretInput;
  if (editingFormlabsIdx !== null && !secretInput) {
    clientSecret = _flParseUrl(settings.resinPrinters[editingFormlabsIdx].moonrakerUrl).clientSecret;
  }
  if (!clientSecret) return;
  const url = _flBuildUrl(serial, clientId, clientSecret);
  if (editingFormlabsIdx !== null) {
    const p = settings.resinPrinters[editingFormlabsIdx];
    p.name = name; p.moonrakerUrl = url; p.wattage = watts;
  } else {
    settings.resinPrinters.push({id:'resin-'+Date.now(), name, moonrakerUrl:url, wattage:watts});
  }
  closeModal('formlabsModal');
  renderResinPrintersList();
}
```

Replace with:
```js
function saveFormlabsPrinter() {
  const name = document.getElementById('flName').value.trim();
  const serial = document.getElementById('flSerial').value.trim();
  const clientId = document.getElementById('flClientId').value.trim();
  const secretInput = document.getElementById('flClientSecret').value.trim();
  const watts = parseFloat(document.getElementById('flWatts').value) || 0;
  const printerModel = document.getElementById('flPrinterModel').value;
  const tankType = document.getElementById('flTankType').value;
  if (!name || !serial || !clientId) return;
  let clientSecret = secretInput;
  if (editingFormlabsIdx !== null && !secretInput) {
    clientSecret = _flParseUrl(settings.resinPrinters[editingFormlabsIdx].moonrakerUrl).clientSecret;
  }
  if (!clientSecret) return;
  const url = _flBuildUrl(serial, clientId, clientSecret, printerModel, tankType);
  if (editingFormlabsIdx !== null) {
    const p = settings.resinPrinters[editingFormlabsIdx];
    p.name = name; p.moonrakerUrl = url; p.wattage = watts;
  } else {
    settings.resinPrinters.push({id:'resin-'+Date.now(), name, moonrakerUrl:url, wattage:watts});
  }
  closeModal('formlabsModal');
  renderResinPrintersList();
}
```

- [ ] **Step 5: Syntax check**

```bash
cd "r:/Azazel's Razer/timetracker"
node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');const s=h.indexOf('<script>')+8;const e=h.indexOf('</script>',s);fs.writeFileSync('.tmp-syntax-check.js',h.slice(s,e));"
node --check .tmp-syntax-check.js && echo SYNTAX_OK
rm .tmp-syntax-check.js
```
Expected: `SYNTAX_OK`.

- [ ] **Step 6: Behavioral verification via Playwright**

```bash
cd "r:/Azazel's Razer/timetracker"
AR_NO_BROWSER=1 python server.py &
sleep 2
```

1. `browser_navigate` to `http://127.0.0.1:5757`, pick/create a project via the startup picker, open Settings.
2. Click "+ Formlabs printer (guided setup)" — confirm the modal now shows "Printer Model" and "Installed Tank" dropdowns below Watts, both defaulted to "— not set —".
3. Select "Form 4" in Printer Model — confirm the Installed Tank dropdown repopulates to show only "Form 4 Resin Tank" (via `populateFlTankOptions`, triggered by the `onchange`).
4. Fill Name=`Test Form 4`, Serial=`FLTEST999`, Client ID=`id1`, Client Secret=`secret1`, Tank=`Form 4 Resin Tank`. Save.
5. `browser_evaluate: () => settings.resinPrinters[settings.resinPrinters.length-1].moonrakerUrl` — expected to contain `printer_model=Form%204&tank_type=Form%204%20Resin%20Tank` (URL-encoded).
6. Click the ✎ edit icon on that row — confirm Printer Model shows "Form 4" and Installed Tank shows "Form 4 Resin Tank" (round-trips correctly through `_flParseUrl`).
7. Change Installed Tank to "— not set —", save, re-open edit — confirm it stays unset (and the URL no longer contains `tank_type=`).
8. Delete the test printer row, click Cancel on Settings so nothing persists to `printers.json`.

Stop the background server afterward.

- [ ] **Step 7: Commit**

```bash
cd "r:/Azazel's Razer/timetracker"
git add index.html
git commit -m "$(cat <<'EOF'
feat: printer model + installed tank setting for Formlabs printers

Formlabs hardware-locks some resins to specific tanks per printer
generation (a compatible printer alone doesn't guarantee a compatible
tank — this already cost a wasted Tough 2000 order). Adds optional
Printer Model and Installed Tank dropdowns to the Formlabs guided
setup modal, stored as extra query params on the existing
formlabs:// URL. Both fields are optional and only shown for Formlabs
printers; nothing else about how printers are stored or polled
changes. Sets up the compatibility warning added next.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Tank compatibility warning in the material modal

**Files:**
- Modify: `index.html:899-900` (resin material form — add the warning banner div)
- Modify: `index.html:2252-2260` (`onResinTypeChange()`)
- Modify: `index.html:2335-2351` (`openMaterialModal()`'s resin branch)

**Interfaces:**
- Consumes: `resinLibrary` (existing global, populated by `loadResinLibrary()`, now containing Task 1's 84 materials with `brand`/`full`/`tankCompatibility`), `_flParseUrl` (Task 2), `settings.resinPrinters` (existing global, entries may now carry `printerModel`/`tankType` per Task 2).
- Produces: `getResinLibraryEntry(rtName)` → the matching `resinLibrary` object or `undefined`. `checkTankCompatibility()` — reads the currently-open material modal's state and shows/hides `#resinTankWarning`. No other function's signature changes.

- [ ] **Step 1: Add the warning banner div**

Find (`index.html:899-900`):
```html
      <div class="form-hint preview" id="resinCostPreview"></div>
      <div class="form-hint" id="resinMachineHint" style="margin-top:4px;"></div>
```

Replace with:
```html
      <div class="form-hint preview" id="resinCostPreview"></div>
      <div class="form-hint" id="resinMachineHint" style="margin-top:4px;"></div>
      <div id="resinTankWarning" style="display:none;margin-top:8px;padding:6px 10px;background:rgba(239,159,39,.07);border:1px solid rgba(239,159,39,.35);border-radius:4px;font-family:var(--mono);font-size:10px;color:var(--amber);letter-spacing:.02em;"></div>
```

- [ ] **Step 2: Add `getResinLibraryEntry()` and `checkTankCompatibility()`**

Find (`index.html:2252-2260`):
```js
function onResinTypeChange() {
  const name=document.getElementById('matResinType').value;
  const rt=settings.resinTypes.find(r=>r.name===name);
  if(rt){
    document.getElementById('matResinCostPerKg').value=rt.costPerKg;
    document.getElementById('matResinDensity').value=rt.densityGPerMl;
  }
  updateResinPreview();
}
```

Replace with:
```js
function getResinLibraryEntry(rtName) {
  return resinLibrary.find(m => (m.brand === 'Generic' ? m.name : m.full) === rtName);
}
function checkTankCompatibility() {
  const banner = document.getElementById('resinTankWarning');
  if (!banner) return;
  banner.style.display = 'none';
  if (!pendingMaterial || pendingMaterial.type !== 'resin' || !activeProject) return;
  const s = activeProject.resinSessions[pendingMaterial.sessionIdx];
  if (!s || !s.printerId) return;
  const printer = (settings.resinPrinters||[]).find(p => p.id === s.printerId);
  if (!printer || !(printer.moonrakerUrl||'').startsWith('formlabs://')) return;
  const { tankType } = _flParseUrl(printer.moonrakerUrl);
  if (!tankType) return;
  const rtName = document.getElementById('matResinType').value;
  const entry = getResinLibraryEntry(rtName);
  if (!entry || !entry.tankCompatibility || !entry.tankCompatibility.length) return;
  if (entry.tankCompatibility.includes(tankType)) return;
  banner.textContent = `⚠ ${rtName} requires ${entry.tankCompatibility.join(' or ')} — this printer is set to ${tankType}.`;
  banner.style.display = 'block';
}
function onResinTypeChange() {
  const name=document.getElementById('matResinType').value;
  const rt=settings.resinTypes.find(r=>r.name===name);
  if(rt){
    document.getElementById('matResinCostPerKg').value=rt.costPerKg;
    document.getElementById('matResinDensity').value=rt.densityGPerMl;
  }
  updateResinPreview();
  checkTankCompatibility();
}
```

- [ ] **Step 3: Call the check when the resin material form first opens**

Find (`index.html:2335-2351`, the resin branch of `openMaterialModal`):
```js
  } else {
    titleEl.textContent=isFail?'Resin — Log Failed Print':'Resin — Log Material'; titleEl.className='modal-title '+(isFail?'modal-title-red':'resin-color');
    const s=activeProject.resinSessions[sessionIdx];
    buildResinSelect(s.resinType||'');
    const rt=settings.resinTypes.find(r=>r.name===s.resinType);
    document.getElementById('matResinMl').value=s.resinMl||'';
    document.getElementById('matResinCostPerKg').value=s.resinCostPerKg||(rt?rt.costPerKg:'')||'';
    document.getElementById('matResinDensity').value=s.resinDensity||(rt?rt.densityGPerMl:1.10)||1.10;
    const hrs=s.end?((s.end-s.start)/3600000):0;
    document.getElementById('resinMachineHint').textContent=hrs.toFixed(2)+'h × $'+settings.resinRate+'/hr = '+fmtMoney(hrs*settings.resinRate)+' machine cost';
    document.getElementById('matSaveBtn').textContent='Log Resin';
    updateResinPreview();
    document.getElementById('matSessionStart').value=toDatetimeLocal(s.start);
    document.getElementById('matSessionEnd').value=s.end?toDatetimeLocal(s.end):'';
    document.getElementById('matNote').value=s.note||'';
    setTimeout(()=>document.getElementById('matResinMl').focus(),50);
  }
```

Replace with:
```js
  } else {
    titleEl.textContent=isFail?'Resin — Log Failed Print':'Resin — Log Material'; titleEl.className='modal-title '+(isFail?'modal-title-red':'resin-color');
    const s=activeProject.resinSessions[sessionIdx];
    buildResinSelect(s.resinType||'');
    const rt=settings.resinTypes.find(r=>r.name===s.resinType);
    document.getElementById('matResinMl').value=s.resinMl||'';
    document.getElementById('matResinCostPerKg').value=s.resinCostPerKg||(rt?rt.costPerKg:'')||'';
    document.getElementById('matResinDensity').value=s.resinDensity||(rt?rt.densityGPerMl:1.10)||1.10;
    const hrs=s.end?((s.end-s.start)/3600000):0;
    document.getElementById('resinMachineHint').textContent=hrs.toFixed(2)+'h × $'+settings.resinRate+'/hr = '+fmtMoney(hrs*settings.resinRate)+' machine cost';
    document.getElementById('matSaveBtn').textContent='Log Resin';
    updateResinPreview();
    checkTankCompatibility();
    document.getElementById('matSessionStart').value=toDatetimeLocal(s.start);
    document.getElementById('matSessionEnd').value=s.end?toDatetimeLocal(s.end):'';
    document.getElementById('matNote').value=s.note||'';
    setTimeout(()=>document.getElementById('matResinMl').focus(),50);
  }
```

- [ ] **Step 4: Syntax check**

```bash
cd "r:/Azazel's Razer/timetracker"
node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');const s=h.indexOf('<script>')+8;const e=h.indexOf('</script>',s);fs.writeFileSync('.tmp-syntax-check.js',h.slice(s,e));"
node --check .tmp-syntax-check.js && echo SYNTAX_OK
rm .tmp-syntax-check.js
```
Expected: `SYNTAX_OK`.

- [ ] **Step 5: Behavioral verification via Playwright**

```bash
cd "r:/Azazel's Razer/timetracker"
AR_NO_BROWSER=1 python server.py &
sleep 2
```

1. `browser_navigate` to `http://127.0.0.1:5757`, pick/create a project.
2. Set up the fixture entirely via `browser_evaluate` (faster and more reliable than driving the full Formlabs-modal + punch-in/out UI flow for a one-off test):
   ```js
   () => {
     settings.resinPrinters.push({id:'test-fl-printer', name:'Test Form 4', moonrakerUrl:'formlabs://FLTEST?client_id=x&client_secret=y&printer_model=Form%204&tank_type=Form%203%20Resin%20Tank%20V2.1', wattage:0});
     settings.resinTypes.push({name:'Formlabs Tough 2000 Resin V2', costPerKg:144.66, densityGPerMl:1.03});
     activeProject.resinSessions.push({id:'test-session', start:Date.now()-3600000, end:Date.now(), printerId:'test-fl-printer'});
     return activeProject.resinSessions.length - 1;
   }
   ```
   Note the returned index (call it `IDX`).
3. `browser_evaluate`: `(idx) => { pendingMaterial = {type:'resin', sessionIdx: idx}; openMaterialModal('resin', idx); }` with `IDX`.
4. `browser_evaluate`: `() => { document.getElementById('matResinType').value = 'Formlabs Tough 2000 Resin V2'; onResinTypeChange(); }`.
5. `browser_snapshot` — confirm `#resinTankWarning` is visible and its text reads something like "⚠ Formlabs Tough 2000 Resin V2 requires Form 4 Resin Tank — this printer is set to Form 3 Resin Tank V2.1." (mismatch — the fixture set the printer's tank to a Form 3 tank, but Tough 2000 V2 only lists `Form 4 Resin Tank` in the library).
6. `browser_evaluate`: `() => { settings.resinPrinters.find(p=>p.id==='test-fl-printer').moonrakerUrl = 'formlabs://FLTEST?client_id=x&client_secret=y&printer_model=Form%204&tank_type=Form%204%20Resin%20Tank'; checkTankCompatibility(); return document.getElementById('resinTankWarning').style.display; }` — expected: `"none"` (now compatible, banner hidden).
7. `browser_evaluate`: `() => { document.getElementById('matResinType').value = ''; onResinTypeChange(); return document.getElementById('resinTankWarning').style.display; }` — expected: `"none"` (no resin selected, no false-positive warning).
8. Clean up the fixture: `browser_evaluate: () => { activeProject.resinSessions.pop(); settings.resinTypes.pop(); settings.resinPrinters.pop(); closeModal('materialModal'); }` so nothing pollutes real data (this test never called `saveData()`, so a reload also discards it — the explicit cleanup is belt-and-suspenders).

Stop the background server afterward.

- [ ] **Step 6: Commit**

```bash
cd "r:/Azazel's Razer/timetracker"
git add index.html
git commit -m "$(cat <<'EOF'
feat: warn when a picked resin doesn't match the installed Formlabs tank

Reads the printerModel/tankType added to Formlabs printer settings and
the tankCompatibility data now in resin-library.json. Shows a
non-blocking amber banner in the material modal (same visual language
as the existing FDM "Resume Tracking" bar) when the selected resin's
required tank doesn't match what's set as installed — never blocks
saving, matching how notes and failed-print logging already work.
Silently does nothing when either side lacks data (no printer/tank
set, or a manually-typed resin with no library match), so there are
no false positives.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Resin Library browser modal (replaces the flat picker)

**Files:**
- Modify: `index.html:276-283` (CSS — add `.rlib-*` rules near the existing `.type-add-row`/`.col-header` rules)
- Modify: `index.html:1011-1016` (Settings → Resin Types — replace the flat `<select>` + "+" with a single browse button)
- Modify: `index.html` (new `resinLibraryModal` HTML block, placed after `resinSourcesModal`'s closing, i.e. after `index.html:712`)
- Modify: `index.html:2863-2907` (`loadResinLibrary()`, `populateResinLibraryPicker()`, `addFromResinLibrary()` — replace the latter two)
- Modify: `index.html:2511` (Escape-key close list — add `'resinLibraryModal'`)
- Modify: `index.html:2515` (backdrop-click close list — add `'resinLibraryModal'`)

**Interfaces:**
- Consumes: `resinLibrary` (existing global, Task 1's 84 materials), `settings.resinTypes` (existing global), `renderResinTypesList()` (existing function, unchanged), `esc()` (existing HTML-escaping helper, unchanged).
- Produces: `openResinLibraryModal()`, `renderResinLibraryList()`, `useLibraryResin(idx)` (idx into the module-level `_rlibFiltered` array, not into `resinLibrary` directly — the filtered list changes as search/brand filters change). Display name rule used everywhere a library entry becomes a saved resin type: `mat.brand === 'Generic' ? mat.name : mat.full` (this exact rule is also what `getResinLibraryEntry()` in Task 3 reverses — keep them consistent if either changes later).

- [ ] **Step 1: Add the new CSS rules**

Find (`index.html:282-283`):
```css
  .col-header { font-family: var(--mono); font-size: 9px; color: var(--dim); text-align: right; padding-bottom: 4px; }
  .col-header:first-child { text-align: left; }
```

Insert immediately after:
```css
  .rlib-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .rlib-row:last-child { border-bottom: none; }
  .rlib-name { font-family: var(--mono); font-size: 11px; color: var(--text); }
  .rlib-brand { font-family: var(--mono); font-size: 9px; color: var(--blue-bright); text-transform: uppercase; letter-spacing: .05em; margin-left: 6px; }
  .rlib-meta { font-family: var(--mono); font-size: 10px; color: var(--muted); margin-top: 2px; }
  .rlib-spec { font-family: var(--mono); font-size: 9px; color: var(--dim); margin-top: 2px; }
  .rlib-add-btn { font-family: var(--mono); font-size: 10px; background: var(--surface2); border: 1px solid var(--border2); color: var(--text); border-radius: 3px; padding: 4px 9px; cursor: pointer; white-space: nowrap; align-self: center; }
  .rlib-add-btn:hover { background: var(--surface3); border-color: var(--blue-bright); color: var(--blue-bright); }
```

- [ ] **Step 2: Replace the flat picker with a browse button**

Find (`index.html:1011-1016`):
```html
    <div style="display:flex;gap:6px;margin-bottom:6px;align-items:center;">
      <select id="resinLibraryPicker" style="flex:1;font-family:var(--mono);font-size:11px;background:var(--surface2);border:1px solid var(--border2);color:var(--text);border-radius:4px;padding:4px 6px;" onchange="">
        <option value="">— add from library —</option>
      </select>
      <button class="type-add-btn" onclick="addFromResinLibrary()" title="Add selected resin">+</button>
    </div>
```

Replace with:
```html
    <button class="manual-link" style="margin-bottom:6px;" onclick="openResinLibraryModal()">+ Browse Resin Library ({{RESIN_LIBRARY_COUNT}} materials)</button>
```

(Leave the literal `{{RESIN_LIBRARY_COUNT}}` placeholder text as-is for now — Step 3 below replaces it with the real static count once Task 1's file is confirmed at 84 materials, since this button's label is static markup, not JS-rendered.)

- [ ] **Step 3: Fill in the real material count**

Find the text just inserted in Step 2 and replace `{{RESIN_LIBRARY_COUNT}}` with `84`:
```html
    <button class="manual-link" style="margin-bottom:6px;" onclick="openResinLibraryModal()">+ Browse Resin Library (84 materials)</button>
```

- [ ] **Step 4: Add the `resinLibraryModal` HTML block**

Find (`index.html:708-712`, the end of `resinSourcesModal`):
```html
    <div class="modal-actions">
      <button class="btn" onclick="closeModal('resinSourcesModal')">Close</button>
    </div>
  </div>
</div>
```

Insert immediately after that block's closing `</div>`:
```html

<!-- RESIN LIBRARY BROWSER MODAL -->
<div class="modal-backdrop" id="resinLibraryModal">
  <div class="modal" style="width:560px;">
    <div class="modal-title" style="color:var(--blue-bright);">Resin Library</div>
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <input type="text" id="rlibSearch" placeholder="Search name, brand, tag…" oninput="renderResinLibraryList()" style="flex:1;font-family:var(--mono);font-size:11px;background:var(--surface2);border:1px solid var(--border);color:var(--text);border-radius:4px;padding:6px 8px;outline:none;" />
      <select id="rlibBrandFilter" onchange="renderResinLibraryList()" style="font-family:var(--mono);font-size:11px;background:var(--surface2);border:1px solid var(--border2);color:var(--text);border-radius:4px;padding:6px 8px;">
        <option value="">All Brands</option>
      </select>
    </div>
    <div id="rlibList" style="max-height:420px;overflow-y:auto;"></div>
    <div class="modal-actions">
      <button class="btn" onclick="closeModal('resinLibraryModal')">Close</button>
    </div>
  </div>
</div>
```

- [ ] **Step 5: Replace the library-picker JS with the browser-modal JS**

Find (`index.html:2863-2907`):
```js
let resinLibrary = [];

async function loadResinLibrary() {
  try {
    const res = await fetch('/resin-library.json');
    const data = await res.json();
    resinLibrary = data.materials || [];
    // Backfill density on any saved resin types that lack it
    let changed = false;
    settings.resinTypes.forEach(rt => {
      if (!rt.densityGPerMl) {
        const match = resinLibrary.find(m => m.name.toLowerCase() === rt.name.toLowerCase());
        if (match) { rt.densityGPerMl = match.densityGPerMl; changed = true; }
      }
    });
    if (changed) persistSettings();
    populateResinLibraryPicker();
  } catch(e) { /* library unavailable — no problem */ }
}

function populateResinLibraryPicker() {
  const sel = document.getElementById('resinLibraryPicker');
  if (!sel) return;
  const existing = new Set(settings.resinTypes.map(r => r.name.toLowerCase()));
  sel.innerHTML = '<option value="">— add from library —</option>';
  resinLibrary
    .filter(m => !existing.has(m.name.toLowerCase()))
    .forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.name;
      opt.textContent = m.name + ' — ' + m.full + '  (' + m.densityGPerMl + ' g/mL)';
      sel.appendChild(opt);
    });
}

function addFromResinLibrary() {
  const sel = document.getElementById('resinLibraryPicker');
  if (!sel || !sel.value) return;
  const mat = resinLibrary.find(m => m.name === sel.value);
  if (!mat) return;
  if (settings.resinTypes.find(r => r.name.toLowerCase() === mat.name.toLowerCase())) return;
  settings.resinTypes.push({ name: mat.name, costPerKg: mat.typicalCostPerKg, densityGPerMl: mat.densityGPerMl });
  renderResinTypesList();
  populateResinLibraryPicker();
}
```

Replace with:
```js
let resinLibrary = [];
let _rlibFiltered = [];

async function loadResinLibrary() {
  try {
    const res = await fetch('/resin-library.json');
    const data = await res.json();
    resinLibrary = data.materials || [];
    // Backfill density on any saved resin types that lack it
    let changed = false;
    settings.resinTypes.forEach(rt => {
      if (!rt.densityGPerMl) {
        const match = resinLibrary.find(m => m.name.toLowerCase() === rt.name.toLowerCase());
        if (match) { rt.densityGPerMl = match.densityGPerMl; changed = true; }
      }
    });
    if (changed) persistSettings();
  } catch(e) { /* library unavailable — no problem */ }
}

function libDisplayName(mat) {
  return mat.brand === 'Generic' ? mat.name : mat.full;
}

function openResinLibraryModal() {
  const brandSel = document.getElementById('rlibBrandFilter');
  const brands = [...new Set(resinLibrary.map(m => m.brand))].sort();
  brandSel.innerHTML = '<option value="">All Brands</option>' + brands.map(b => `<option value="${esc(b)}">${esc(b)}</option>`).join('');
  document.getElementById('rlibSearch').value = '';
  renderResinLibraryList();
  document.getElementById('resinLibraryModal').classList.add('open');
  setTimeout(()=>document.getElementById('rlibSearch').focus(),50);
}

function renderResinLibraryList() {
  const search = (document.getElementById('rlibSearch').value||'').toLowerCase();
  const brandFilter = document.getElementById('rlibBrandFilter').value;
  const existing = new Set(settings.resinTypes.map(r => r.name.toLowerCase()));
  _rlibFiltered = resinLibrary.filter(m => {
    if (existing.has(libDisplayName(m).toLowerCase())) return false;
    if (brandFilter && m.brand !== brandFilter) return false;
    if (!search) return true;
    const haystack = (m.name + ' ' + m.brand + ' ' + m.full + ' ' + (m.tags||[]).join(' ')).toLowerCase();
    return haystack.includes(search);
  });
  const el = document.getElementById('rlibList');
  if (!_rlibFiltered.length) { el.innerHTML = '<div class="empty-state">No matches.</div>'; return; }
  el.innerHTML = _rlibFiltered.map((m,i) => {
    const specParts = [];
    if (m.mechanical && m.mechanical.tensileStrengthMPa != null) specParts.push(m.mechanical.tensileStrengthMPa + ' MPa tensile');
    if (m.mechanical && m.mechanical.shoreHardness != null) specParts.push('Shore ' + m.mechanical.shoreHardness);
    if (m.printerCompatibility && m.printerCompatibility.length) specParts.push(m.printerCompatibility.join('/'));
    if (m.tankCompatibility && m.tankCompatibility.length) specParts.push('needs ' + m.tankCompatibility.join(' or '));
    const specLine = specParts.length ? `<div class="rlib-spec">${esc(specParts.join(' · '))}</div>` : '';
    return `<div class="rlib-row">
      <div>
        <span class="rlib-name">${esc(m.name)}</span><span class="rlib-brand">${esc(m.brand)}</span>
        <div class="rlib-meta">$${m.typicalCostPerKg ?? '—'}/kg${m.densityGPerMl != null ? ', ' + m.densityGPerMl + ' g/mL' : ''}</div>
        ${specLine}
      </div>
      <button class="rlib-add-btn" onclick="useLibraryResin(${i})">+ Use</button>
    </div>`;
  }).join('');
}

function useLibraryResin(idx) {
  const mat = _rlibFiltered[idx];
  if (!mat) return;
  const name = libDisplayName(mat);
  if (settings.resinTypes.find(r => r.name.toLowerCase() === name.toLowerCase())) return;
  settings.resinTypes.push({ name, costPerKg: mat.typicalCostPerKg || 0, densityGPerMl: mat.densityGPerMl || 1.10 });
  renderResinTypesList();
  renderResinLibraryList();
}
```

- [ ] **Step 6: Add `resinLibraryModal` to the Escape and backdrop-click close lists**

Find (`index.html:2511`):
```js
  if(e.key==='Escape'){['projectModal','materialModal','settingsModal','manualModal','subtypeModal','editSessionModal','resinSourcesModal','exportModal','archiveModal','formlabsModal'].forEach(closeModal);pendingMaterial=null;manualType=null;editingSession=null;editingFormlabsIdx=null;}
```
Replace with:
```js
  if(e.key==='Escape'){['projectModal','materialModal','settingsModal','manualModal','subtypeModal','editSessionModal','resinSourcesModal','exportModal','archiveModal','formlabsModal','resinLibraryModal'].forEach(closeModal);pendingMaterial=null;manualType=null;editingSession=null;editingFormlabsIdx=null;}
```

Find (`index.html:2515-2517`):
```js
['projectModal','settingsModal','resinSourcesModal'].forEach(id=>
  document.getElementById(id).addEventListener('click',e=>{if(e.target===e.currentTarget)closeModal(id);})
);
```
Replace with:
```js
['projectModal','settingsModal','resinSourcesModal','resinLibraryModal'].forEach(id=>
  document.getElementById(id).addEventListener('click',e=>{if(e.target===e.currentTarget)closeModal(id);})
);
```

- [ ] **Step 7: Syntax check**

```bash
cd "r:/Azazel's Razer/timetracker"
node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');const s=h.indexOf('<script>')+8;const e=h.indexOf('</script>',s);fs.writeFileSync('.tmp-syntax-check.js',h.slice(s,e));"
node --check .tmp-syntax-check.js && echo SYNTAX_OK
rm .tmp-syntax-check.js
```
Expected: `SYNTAX_OK`.

- [ ] **Step 8: Behavioral verification via Playwright**

```bash
cd "r:/Azazel's Razer/timetracker"
AR_NO_BROWSER=1 python server.py &
sleep 2
```

1. `browser_navigate` to `http://127.0.0.1:5757`, pick/create a project, open Settings.
2. Confirm the old flat select is gone and a button reading "+ Browse Resin Library (84 materials)" is present under Resin Types.
3. Click it — confirm `resinLibraryModal` opens (`browser_snapshot`), the brand filter shows options including Formlabs/Anycubic/Elegoo/Siraya Tech/Phrozen/HeyGears/Generic, and the list shows rows (each with a name, brand tag, cost/density line, "+ Use" button).
4. Type `tough 2000` in the search box — confirm the list filters down to the two Tough 2000-named entries (V2 with its spec line showing tensile/printer/tank info).
5. Select "Formlabs" in the brand filter with the search box cleared — confirm all visible rows show "FORMLABS" as the brand tag and the count is 48.
6. Click "+ Use" on "Tough 2000 Resin V2" — confirm the row disappears from the filtered list (already-added), and `browser_evaluate: () => settings.resinTypes.find(r=>r.name==='Formlabs Tough 2000 Resin V2')` returns an object with `costPerKg` ≈ 144.66 and `densityGPerMl` ≈ 1.03.
7. Switch brand filter back to "All Brands", search `standard resin` — confirm both "Standard Resin" (Anycubic) and "Standard Resin" (Elegoo) appear as two distinct rows (proving the earlier bare-name collision is avoided) — click "+ Use" on the Elegoo one, confirm `settings.resinTypes` gains `"Elegoo Standard Photopolymer Resin V2.0"` (its `full`, not a colliding bare `"Standard Resin"`).
8. Press Escape — confirm the modal closes. Reopen, click the backdrop outside the modal box — confirm it also closes.
9. Open Settings' Resin Types list directly (`browser_snapshot`) — confirm the two resins added in steps 6–7 now appear there with correct cost/density, then remove them via their ✕ buttons so they don't pollute real settings, and click Cancel on Settings so nothing persists.

Stop the background server afterward.

- [ ] **Step 9: Commit**

```bash
cd "r:/Azazel's Razer/timetracker"
git add index.html
git commit -m "$(cat <<'EOF'
feat: searchable resin library browser (replaces flat picker)

A single <select> worked for 12 generic entries; it doesn't scale to
84 materials across 7 brands. Replaces it with a modal: text search +
brand filter, each row showing cost/density and, for materials that
have it, a compact spec line (tensile strength, shore hardness,
compatible printers/tanks). Fixes a latent bug the old picker would
have hit once brand-specific entries existed: selecting an <option>
by its bare name broke when two brands share a resin name (e.g.
"Standard Resin" exists for both Anycubic and Elegoo) — the new list
is keyed by array index into the current filtered set instead, and
saved resin type names are disambiguated using each material's
brand-prefixed "full" name.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Docs, data-sources modal entry, and version bump

**Files:**
- Modify: `index.html:679-707` (`resinSourcesModal` — add a Formlabs sources entry)
- Modify: `index.html:509` (footer version string)
- Modify: `CLAUDE.md` (current version line, version history table)

**Interfaces:**
- Consumes: nothing (pure documentation/version-string task).
- Produces: nothing consumed by other tasks — this is the plan's closing task.

- [ ] **Step 1: Add a Formlabs entry to the data-sources modal**

Find (`index.html:696-701`):
```html
      <div style="border-top:1px solid var(--border);padding-top:8px;font-family:var(--mono);font-size:11px;">
        <div style="color:var(--text);margin-bottom:3px;">Anycubic MSDS</div>
        <div style="color:var(--muted);margin-bottom:2px;">Plant-Based · High-Temp</div>
        <a href="https://store.anycubic.com/pages/resin-user-manual" target="_blank" style="color:var(--blue-bright);text-decoration:none;">store.anycubic.com/pages/resin-user-manual</a>
      </div>
```

Insert immediately after that block:
```html
      <div style="border-top:1px solid var(--border);padding-top:8px;font-family:var(--mono);font-size:11px;">
        <div style="color:var(--text);margin-bottom:3px;">Formlabs Product Pages &amp; Technical Data Sheets</div>
        <div style="color:var(--muted);margin-bottom:2px;">Full ~48-material Formlabs catalog — mechanical specs, printer &amp; resin-tank compatibility per material</div>
        <a href="https://formlabs.com/store/materials/" target="_blank" style="color:var(--blue-bright);text-decoration:none;">formlabs.com/store/materials</a>
      </div>
```

- [ ] **Step 2: Bump the footer version string**

Find (`index.html:509`):
```html
        &nbsp;|&nbsp; <span id="footerVersion">Beta 10.9.0</span>
```
Replace with:
```html
        &nbsp;|&nbsp; <span id="footerVersion">Beta 10.10.0</span>
```

- [ ] **Step 3: Syntax check**

```bash
cd "r:/Azazel's Razer/timetracker"
node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');const s=h.indexOf('<script>')+8;const e=h.indexOf('</script>',s);fs.writeFileSync('.tmp-syntax-check.js',h.slice(s,e));"
node --check .tmp-syntax-check.js && echo SYNTAX_OK
rm .tmp-syntax-check.js
```
Expected: `SYNTAX_OK`.

- [ ] **Step 4: Behavioral verification via Playwright**

```bash
cd "r:/Azazel's Razer/timetracker"
AR_NO_BROWSER=1 python server.py &
sleep 2
```

1. `browser_navigate` to `http://127.0.0.1:5757`.
2. Confirm the footer shows "Beta 10.10.0".
3. Click "data sources" in the footer — confirm `resinSourcesModal` opens and now includes the Formlabs entry (`browser_snapshot`), alongside the existing Elegoo/Siraya Tech/Phrozen/Anycubic/Liqcreate entries.

Stop the background server afterward.

- [ ] **Step 5: Update `CLAUDE.md`**

Update the version line near the top:

Find:
```
**Current version:** Beta 10.9.0 | **Server:** v1.10
```
Replace with:
```
**Current version:** Beta 10.10.0 | **Server:** v1.10
```

Add a new row at the bottom of the Version History table:
```
| Beta 10.10.0 | Master resin library — resin-library.json expanded from 12 generic entries to an 84-material brand-tagged catalog (48 Formlabs SLA resins with real per-SKU mechanical specs + printer/tank compatibility sourced from Formlabs' product pages/TDS, plus family-level entries for Anycubic/Elegoo/Siraya Tech/Phrozen/HeyGears, original 12 kept as brand:"Generic"). Formlabs printer settings gain optional Printer Model + Installed Tank fields (guided setup modal); material modal shows a non-blocking amber warning when a picked resin's required tank doesn't match what's set as installed. Flat resin picker replaced with a searchable/brand-filterable library browser modal. No server.py changes. |
```

- [ ] **Step 6: Commit**

```bash
cd "r:/Azazel's Razer/timetracker"
git add index.html CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: bump version to Beta 10.10.0 for master resin library

Adds a Formlabs sources entry to the data-sources modal and records
the resin-library expansion + tank-compatibility feature in CLAUDE.md's
version history, per this project's standing convention of bumping
version after every significant feature.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Plan Self-Review

**Spec coverage** (against `docs/superpowers/specs/2026-07-20-formlabs-resin-library-design.md`):
- Section 1 (schema: full 48-material Formlabs catalog + family-level other brands) → Task 1. ✅
- Section 2 (`printerModel`/`tankType` settings on Formlabs printers, optional, only shown for Formlabs) → Task 2. ✅
- Section 3 (non-blocking amber compatibility banner, silent when data missing on either side) → Task 3. ✅
- Section 4 (searchable/brand-filterable library browser replacing the flat picker) → Task 4. ✅
- Non-goals respected: no SQLite (plain JSON file, Task 1), no owned-tank inventory (only "installed right now," Task 2), no hard-blocking (Task 3 never touches `saveMaterial()`/prevents saving), no compatibility logic for non-Formlabs brands (Task 3's `checkTankCompatibility()` short-circuits unless the linked printer's URL starts with `formlabs://`), no filament-library/picker changes (untouched throughout), no `server.py` changes (confirmed — grep for `server.py` across all tasks' Files sections turns up nothing).

**Placeholder scan:** No TBD/TODO markers. Task 4 Step 2's `{{RESIN_LIBRARY_COUNT}}` is not a plan placeholder — it's a two-step edit (Step 2 introduces literal text, Step 3 immediately replaces it with the real, already-known value `84`) done this way so the search-string in Step 2 stays copy-pasteable without pre-computing the count inline; Step 3 leaves no placeholder text in the file.

**Type/name consistency check:**
- `FORMLABS_TANK_OPTIONS` / `FORMLABS_PRINTER_MODELS` (Task 2) — defined once, referenced by name in `populateFlTankOptions()` (same task) and nowhere else.
- `_flParseUrl()` / `_flBuildUrl()` signatures — Task 2 adds `printerModel`/`tankType` as the 4th/5th params to `_flBuildUrl` and as new return keys on `_flParseUrl`; Task 3's `checkTankCompatibility()` calls `_flParseUrl(printer.moonrakerUrl)` and destructures `{ tankType }`, matching the new return shape exactly.
- `getResinLibraryEntry()` (Task 3) and `libDisplayName()` (Task 4) implement the identical brand-prefix rule (`brand==='Generic' ? name : full`) independently in two places by necessity (Task 3 reverses a name back to a library entry; Task 4 forward-computes the name to save) — flagged in Task 4's Interfaces block as a pairing to keep in sync if either changes later.
- `resinLibrary` global — populated in `loadResinLibrary()` (existing, Task 4 only removes the now-dead `populateResinLibraryPicker()` call from it), read by `checkTankCompatibility()` (Task 3) and `renderResinLibraryList()` (Task 4).
- `resinLibraryModal` — HTML `id` (Task 4 Step 4) matches every `document.getElementById('resinLibraryModal')` / `closeModal('resinLibraryModal')` / array-membership reference in Task 4 Steps 5–6.
- `useLibraryResin(idx)` indexes into `_rlibFiltered`, not `resinLibrary` — consistent between its definition and the `onclick="useLibraryResin(${i})"` call site in `renderResinLibraryList()` (same task, same function's template).

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-20-formlabs-resin-library.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
