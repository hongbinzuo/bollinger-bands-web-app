# TODO

- Run grid search to tune base_weights once Python environment is available:

- Evaluation matrix (baseline metrics snapshot):
  - Archive AUC/Brier/acc results for comparison in future iterations.

- Frontend UX polish:

- Functional verification checklist:
  - Check JSON serialization and date fields remain stable.
  - Validate UI rendering for downward levels across dark/light themes and small screens.

- Code review follow-ups:
  - Add request timeouts for external market APIs in `app.py` (Gate.io/Bybit/Bitget).
  - Fix logger initialization path when `MultiTimeframeStrategy` fails to initialize.
  - Fix signal de-dup key to use the actual take-profit field in formatted signals.
  - Enforce or remove unused request timeout logic in `multi_timeframe_api.py`.
  - Align symbol length validation across add/import/default paths.
  - Add cache safety: guard concurrent reads/writes and document pickle risk.
