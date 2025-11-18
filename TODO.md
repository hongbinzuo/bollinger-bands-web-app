# TODO

- Run grid search to tune base_weights once Python environment is available:
  - Command: python test_fibonacci_prob_gridsearch.py --symbols BTC,ETH,SOL --timeframes 4h,1d --days 120 --horizon_bars 24,36 --stride 6 --mode grid
  - Write back the suggested weights to FibonacciProbabilityModel.base_weights and commit.

- Evaluation matrix (baseline metrics snapshot):
  - Command: python test_fibonacci_prob_gridsearch.py --symbols BTC,ETH,SOL --timeframes 4h,1d --days 120 --horizon_bars 24,36 --stride 6 --mode matrix
  - Archive AUC/Brier/acc results for comparison in future iterations.

- Frontend UX polish:
  - Optionally display indicators (ATR/RSI/ADX last) in the Fibonacci Probability section.
  - Add a toggle to show/hide the Downward Fibonacci chart and cards.

- Functional verification checklist:
  - Verify /fibonacci-prob/api/analyze returns both up and down probabilities for several symbols/timeframes.
  - Check JSON serialization and date fields remain stable.
  - Validate UI rendering for downward levels across dark/light themes and small screens.

