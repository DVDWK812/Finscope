# Public showcase visual redesign — 31 October 2026 Sydney

This is presentation work on main only. The local branch, full product,
24 authored records, reviewed fictional topic memberships, exact headline
frequencies and frozen evaluation are preserved. No new dependency, provider
request, model operation or product database is introduced.

## Milestone A — design system, navigation and graph

- Shared `showcase_theme.py` tokens define navy surfaces, readable text, teal
  accents, semantic sentiment colours, radii and spacing. Main's public config
  uses the corresponding native dark theme. Component styles use documented
  container keys plus a small central set of Streamlit layout/button adapters;
  no generated CSS class names or hidden native controls.
- A 232 px sidebar uses native icon buttons with a clear active state, explicit
  current-page text, visible keyboard focus and 44 px minimum targets. Enter
  navigation was checked in the browser. Reduced-motion preferences are respected.
- Consistent headers carry a short synthetic-preview badge. Graph card nodes
  preserve full tooltip evidence, readable sentiment text and all relationships.
  Desktop SVGs fit the panel instead of forcing horizontal scrolling. Mobile
  opens on headlines; native panning exposes company/topic context. A UI-only
  inline resize handler positions that view, without network or storage access.
- A native map-options popover contains source visibility and mobile zoom.
  One concise relationship key replaces duplicate legends. The article inspector
  is a cohesive surface; technical codes remain collapsed. Widget identities are
  scoped to available article IDs to prevent stale labels after company changes.
  The frequency cloud has its own prominent surface; counting is unchanged.

Local checks: 233 tests pass, Python syntax and seven offline previews pass.
At 1440×900 and 1280×800 the graph panel has equal visible/scroll widths
(1095/1095 and 935/935 px). At 768 px and 390 px, the full readable map pans
inside 423 px and 321 px panels; document width stays within the viewport.
Graph text boxes do not overlap or escape node cards. Shared normal-text tokens
pass 4.5:1 contrast against all three dark surfaces; this is a targeted check,
not a claim of a complete accessibility audit or human usability validation.

Before/local-after screenshots and validation logs are retained in ignored
`reports/showcase_premium_20261031/`. Exact pushed-commit CI and deployed checks
are recorded after release; a successful push alone is not hosted acceptance.

Implementation references: [Streamlit container keys](https://docs.streamlit.io/1.50.0/develop/api-reference/layout/st.container),
[native icon buttons](https://docs.streamlit.io/1.50.0/develop/api-reference/widgets/st.button),
[native theme configuration](https://docs.streamlit.io/develop/concepts/configuration/theming),
[W3C minimum text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

## Milestone B — page presentation

Milestone A was released as `412b12bf5e8452e48aff747df6c2fc156de57e7d`.
Both [regression jobs](https://github.com/DVDWK812/Finscope/actions/runs/41068853354)
and [isolation CI](https://github.com/DVDWK812/Finscope/actions/runs/41068853481)
passed for that SHA. The actual public app served the new menu and graph; all six
pages loaded. Hosted measurements at all four requested sizes matched the local
panel widths above, with no overlapping or clipped node text.

Milestone B adds a two-column landing hero with Explore Demo/Get FinScope CTAs.
Its illustrative dashboard is computed from the 24 existing records: six
industries, 11 positive labels (46% rounded) and actual per-sector tone counts.
There are no invented prices, charts or model outputs. A four-card icon guide
describes the separate local workflow.

Dashboard filters sit in a compact disclosure with a visible scope summary.
Equal KPI surfaces, common chart backgrounds/colours, bottom legends and readable
day labels unify sector, mix, time and heatmap views. The underlying raw-report
counts, denominator, date range and empty-cell meanings are unchanged. Phones
use two KPI columns; chart panels stack on narrower screens.

Explorer replaces 24 repeated detail cards with a bounded native list and one
integrated detail panel. Native row selection and a keyboard-accessible headline
picker resolve stable article IDs. Changing the picker clears stale table
highlighting; changing filters discards invalid selections. Clearing a picker
shows an explicit empty state and can recover. Tones use the shared text colours.

Installation is three numbered steps with platform tabs and wrapped, copyable
commands. These are displayed instructions only; no local-branch or install/model
command was executed. Available capabilities and planned integrations are separate.

Before B release: 236 offline tests pass, including existing tests adapted to
list/detail behavior while retaining all-record coverage. New regressions verify
factual landing counts, stale-filter selection and clear/recovery. Syntax and
seven offline previews pass. Local review covers all six pages at 1440×900,
1280×800, 768×1024 and 390×844: no document overflow, clipped controls or tracebacks.
The list's row selection was operated in a real browser. Shared token contrast,
keyboard focus and reduced-motion support remain. These targeted checks are not
a full accessibility certification or completed human usability sessions.

Final B SHA/CI and real hosted before/after images are verified after push and
recorded in the ignored evidence directory. No new dependency or runtime boundary
change accompanies this presentation milestone.

Hosted acceptance found that removing filter session keys could reset counts
while retaining a browser chip. A follow-up assigns all reset values explicitly
and strengthens the existing regression; final hosted acceptance checks both
visible controls and totals. This preserves the raw-report counting method.
