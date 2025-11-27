# Changelog

All notable changes to this project will be documented in this file.

This project follows Conventional Commits and maintains short, focused release notes.

## [v2.2.0] - 2025-11-19

Highlights
- Embedded K-line draw tab in the main UI (no iframe), powered by local TradingView Lightweight Charts.
- Local static assets (no CDN) for reliability; base stylesheet added to avoid 404.
- Support/Resistance lines: green support, red resistance; labels (S1/R1) editable; drag-to-adjust with snapping; auto refresh option.
- Export features: chart PNG (with fallback), config JSON, levels CSV; save/list/delete persisted on server.

Added
- feat(ui/kline): new “K线绘制” tab (natural-language parse: symbol/timeframe/support/resistance/remarks; click-to-add; draggable lines; persistence APIs).
- feat(kline): export chart as PNG (uses takeScreenshot when available; fallback to compositing canvases); export/import JSON; export CSV.
- chore(static): add local `static/vendor/lightweight-charts/...` and minimal `static/style.css`.

Changed
- ui: initialize/resize chart on tab switch; use ResizeObserver to ensure visibility; embed tab in-page instead of iframe.

Fixed
- fix(ui): prevent script-in-template-literal breakage; move KLINE script to page end; guards around uninitialized series/lines.

Links
- [Tag v2.2.0][v2.2.0]

## [v2.1.0] - 2025-11-19

Highlights
- Frontend stability improvements: JSON NaN/Inf sanitized; probability UI shows data source and used symbol.

Added

Fixed
- fix(api): multi_timeframe_api undefined strategy 500.

Changed
- change: strict mode — never use mock data; if no real K-lines available, return failure.

Notes
- Prior releases and snapshots are available under `versions/`.

[v2.1.0]: https://github.com/hongbinzuo/bollinger-bands-web-app/releases/tag/v2.1.0
[v2.2.0]: https://github.com/hongbinzuo/bollinger-bands-web-app/releases/tag/v2.2.0
