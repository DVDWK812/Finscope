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

Pending implementation and separate tested main release. Agent browser checks
are development evidence, not completed human usability sessions.
