# Organic visual update

Applied to the Desktop SmartDine project on 28 October 2026. No commit or push was made.

Presentation uses the supplied sand/paper/ink/moss/clay tokens, Source Serif 4 and Instrument Sans under the requested CSS family aliases, flat decorative forms, subtle paper grain, irregular control/sheet corners, and restrained pressed feedback. Content, routes, model, data, recommendation features and filter rules remain unchanged.

## Files

- `app.py`: shared theme/font loading, existing header and card presentation; native `initial_sidebar_state="auto"` keeps the mobile form accessible while retaining the sidebar toggle.
- `.streamlit/config.toml`: native light theme using the requested colors.
- `SmartDine/frontend/organic-tokens.css`: authoritative shared tokens, font aliases, decorative shapes, and reduced-motion rules.
- `SmartDine/frontend/streamlit.css`: styles existing Streamlit widgets, states and responsive layout.
- `SmartDine/frontend/index.css`: Organic styling for the existing dashboard components, with 1000/700px breakpoints.
- `SmartDine/frontend/index.html`: local font loading through CSS, decorative forms hidden from assistive technology, accessible dialog labeling, and versioned style/script URLs.
- `SmartDine/frontend/app.js`: earth-colored presentation, native keyboard dietary buttons with pressed state and retained focus, labeled member inputs, and dialog Escape/Tab/focus-return support. Scoring requests are unchanged.
- `SmartDine/frontend/fonts/`: two local WOFF2 fonts and their original SIL Open Font License texts. Sources: Google Fonts (fonts.googleapis.com/fonts.gstatic.com), licenses from github.com/google/fonts.
- `tools/package_submission.py`: include the new theme configuration, fonts and licenses in future packages.
- `tests/test_artifacts_api.py`: existing asset-serving assertions now check the new asset version query; paths and endpoint assertions remain intact.

Original edited files are preserved in `.local-backup/before-organic-style/`. New theme files can be identified by `git status`; no original files were deleted.

## Verification

- Existing Python suite: 74 passed, 0 failures, 0 errors, 0 skips; 13 dependency deprecation warnings. Command: `.\.venv\Scripts\python.exe -m pytest -q --tb=short`.
- Existing frontend suite: 5 assertions passed using `node tests/test_frontend.cjs`.
- JavaScript/Python/TOML/CSS syntax and `git diff --check` passed.
- Streamlit AppTest: initial render, Recommend, preset change, group-size change and another Recommend passed.
- Real browser: dashboard and Streamlit render with the new palette. Streamlit generated ten result cards; first-card background verified as the moss token. Dashboard keyboard Space selected a diet, retained focus and showed a focus outline; dialog Tab stayed inside and Escape closed it.
- Dashboard rendered at a 1280px desktop viewport, and inside local-only exact-width test frames at 390px, 700px and 1000px. CSS content widths were 375, 685 and 985px after the browser's scrollbar. Scroll widths matched those client widths. Main columns were respectively one, one and two. A clipped mobile headline was corrected before final verification.
- Streamlit rendered in a 390px frame: scroll width 390px, single-column header, and member inputs 342px wide. The native automatic sidebar defaults closed on mobile.
- Reduced-motion rules are included in both stylesheets; the OS preference was not changed to test them.
- In-app viewport overrides did not apply on this host; responsive verification therefore used local HTML frames, not a claimed browser resize. The temporary frames are verification tools outside the product and are not new app routes.

## Preview

Streamlit: http://127.0.0.1:8502
Dashboard/API: http://127.0.0.1:8001

Normal launch commands remain `python -m streamlit run app.py` and `python server.py`. Existing running processes need a restart or refresh to load theme settings and versioned assets. No dependencies were added to requirements.txt.
