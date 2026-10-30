# Public showcase freeze — 31 October 2026 Sydney

**Status: MAINTENANCE ONLY.** Stop nonessential showcase development. Subsequent
changes are limited to critical bug fixes and security updates, with regression,
isolation CI and actual hosted acceptance required again.

| Release evidence | Verified result |
|---|---|
| Final application commit | `4b1e409941a7861a34658e7fde15d15d3e41a0b8` |
| Public URL | https://finscope-dvdwk812.streamlit.app/ — existing application and URL retained |
| Exact-commit regression | [41082670618](https://github.com/DVDWK812/Finscope/actions/runs/41082670618): success, both Python 3.11 / Streamlit matrix jobs |
| Exact-commit isolation | [41082670152](https://github.com/DVDWK812/Finscope/actions/runs/41082670152): success, showcase-only dependencies and runtime guards |
| Offline verification | 236 tests; Python syntax; seven dry-run previews; six desktop/mobile pages |
| Hosted acceptance | All six pages at 1440×900, 1280×800, 768×1024 and 390×844; no page overflow, clipped controls or app exceptions |

The closeout follow-up changes documentation only; application files remain those
of this SHA. Final repository HEAD and its exact-push CI are recorded separately
in the local release receipt and delivery message.

## Browser findings and supported features

- Home, User Guide, Dashboard Preview, Knowledge Graph, News Explorer and Get
  FinScope work on the existing hosted application. The premium design is retained.
- Dashboard: 24 originals; Technology gives 4; Positive within Technology gives 2;
  Reset restores 24 and clears selections. A complete 17–29 October range gives
  22 reports/13 days; Reset restores 16–29 October and 24 reports.
- Graph: Company Focus and Industry Network, readable company/industry/headline
  labels, semantic tone labels, three reviewed unverified topic groups and original
  article inspection. Cedar has seven default nodes; optional sources add three.
  At 1440px the map fits its 1095px container with no horizontal scroll or node
  overlaps. Mobile has a focusable 321px viewport over a 960px pannable map.
- Word cloud: exact once-per-headline frequencies from authored titles, with
  generic/company words excluded. `research` matches three originals across all
  examples and two for Cedar; both named matches and original details resolve
  correctly. Ten Cedar terms have no overlap at 390px.
- Explorer: four Cedar originals, matching headline selection and distinct details;
  desktop row selection opens the corresponding original. Technical IDs stay in
  collapsed details rather than default article labels.
- Product link: [functional local application](https://github.com/DVDWK812/Finscope/tree/local).
  [Showcase source](https://github.com/DVDWK812/Finscope/tree/main) is separate.
  Windows and macOS/Linux instructions explicitly clone `--branch local
  --single-branch`, use `requirements-local.txt` and launch the root app on localhost.
  Displayed clone/install/model commands were not executed.

## Boundaries and limitations

All 24 public records and preset sentiments are authored fictional examples.
Guarded tests block provider HTTP, local/model imports and SQLite; the public path
has no news API, credential input, inference, database or model-download action.
Optional local integrations are documented as implemented on the separate product
branch, subject to configuration/rights; their live availability was not retested.
Browser request observations include hosting-platform traffic and are not an
exhaustive server-network audit; isolation evidence comes from the guarded code
path and tests.

The hosted Python runtime initially retained the old link after Cloud reported an
update. Rebooting the existing app and reconnecting loaded the corrected link;
all acceptance checks followed. Admin access remained available. Cloud does not
display an application build SHA, so browser observations identify served behavior,
not an independent build-hash attestation. Native hosting controls and nonblocking
Streamlit HTML-component/default-state warnings remain. Complete the native date
range selection before interpreting counts. Mobile graph panning is intentional.
No hosting endurance or human usability certification is claimed.

Raw originals remain the default; candidate links do not validate deduplication or
contradiction detection. Frozen results, original annotations and qualifications
are unchanged; reviewer independence/completion and three-human usability evidence
remain unverified. Only the concise report synopsis is maintained.

## Final branch configuration

**Rename: DEFERRED.** GitHub default is `main`; Streamlit coordinates are
`DVDWK812/Finscope`, `main`, `deploy/streamlit_app.py`. General settings offers no
branch migration control. Both workflows run on push/PR without branch filters.
Tracking remains `main` → `origin/main`; the separate product worktree tracks
`local` → `origin/local`. No duplicate `web` branch was created.

Streamlit's official [coordinate-change procedure](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app)
requires deleting and redeploying the application and warns about loss of admin
access after an unprepared coordinate change. Those actions require explicit user
approval; none was performed. The existing URL takes priority over the rename.

**Local untouched by showcase work:** no switch, reset, merge, edit or push of
local was performed. Its separate product worktree independently advanced from
`ce22c9ff04e9cc8877e1e764103761469f1c8abc` to
`22ac30148b73214a0ea3163a37367a8f11249066` during closeout; local and remote refs
agree at the latter observed check. That concurrent commit was preserved.
Five unrelated working-tree files and 23 protected evidence files retained their
byte hashes. Private annotations/screenshots/logs are not published with this
record. Agent screenshots and verification logs are retained locally under
`reports/showcase_closeout_20261031/` (ignored).
