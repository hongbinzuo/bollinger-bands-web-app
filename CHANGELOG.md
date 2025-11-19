# Changelog

All notable changes to this project will be documented in this file.

This project follows Conventional Commits and maintains short, focused release notes.

## [v2.2.0] - 2025-11-19

Highlights
- Embedded K-line draw tab in the main UI (no iframe), powered by local TradingView Lightweight Charts.
- Local static assets (no CDN) for reliability; base stylesheet added to avoid 404.
- Support/Resistance lines: green support, red resistance; labels (S1/R1) editable; drag-to-adjust with snapping; auto refresh option.
- Export features: chart PNG (with fallback), config JSON, levels CSV; save/list/delete persisted on server.
- Continued stability fixes for Fibonacci Probability data source and JSON output.

Added
- feat(ui/kline): new “K线绘制” tab (natural-language parse: symbol/timeframe/support/resistance/remarks; click-to-add; draggable lines; persistence APIs).
- feat(kline): export chart as PNG (uses takeScreenshot when available; fallback to compositing canvases); export/import JSON; export CSV.
- chore(static): add local `static/vendor/lightweight-charts/...` and minimal `static/style.css`.

Changed
- ui: initialize/resize chart on tab switch; use ResizeObserver to ensure visibility; embed tab in-page instead of iframe.

Fixed
- fix(ui): prevent script-in-template-literal breakage; move KLINE script to page end; guards around uninitialized series/lines.
- fix(fibonacci-prob): multi-exchange fallback (Bybit spot/linear → Gate.io → Bitget), strict mode (no mock), JSON NaN/Inf sanitization; surface `data_source` and `used_symbol`.

Links
- [Tag v2.2.0][v2.2.0]

## [v2.1.0] - 2025-11-19

Highlights
- Fibonacci Probability now uses real market data only (no mock), with multi-exchange fallback: Bybit (spot/linear) -> Gate.io -> Bitget.
- Frontend stability improvements: JSON NaN/Inf sanitized; probability UI shows data source and used symbol.

Added
- feat(fibonacci-prob): multi-exchange fallback (Bybit spot/linear -> Gate.io -> Bitget) for K-line fetching.
- feat(fibonacci-prob): downside Fibonacci extensions and probabilities; dynamic weighting; evaluation/gridsearch scripts.
- feat(ui): ATR/RSI/ADX and +DI/-DI snapshot display on Fibonacci Probability panel.

Fixed
- fix(fibonacci-prob): sanitize JSON outputs (NaN/Inf -> null) to avoid frontend JSON.parse errors.
- fix(chart/frontend): canvas context errors and toFixed field mismatches in related Fibonacci views.
- fix(api): multi_timeframe_api undefined strategy 500.

Changed
- change: strict mode — never use mock data; if no real K-lines available, return failure.
- ui: show `data_source` and `used_symbol` in Fibonacci Probability results for traceability.

Notes
- See `templates/index.html` for UI additions; `fibonacci_probability_model.py` for data sourcing and sanitization.
- Prior releases and snapshots are available under `versions/`.

[v2.1.0]: https://github.com/hongbinzuo/bollinger-bands-web-app/releases/tag/v2.1.0
[v2.2.0]: https://github.com/hongbinzuo/bollinger-bands-web-app/releases/tag/v2.2.0
