## 1. Reverse Resource Chart Ordering

- [x] 1.1 Change `CostValueChart` to sort grouped rows by descending `sortValue`.
- [x] 1.2 Change `RuntimeBarChart` to sort grouped rows by descending `sortValue`.
- [x] 1.3 Change `TokenUsageChart` to sort grouped rows by descending `sortValue`.

## 2. Verify Ordering Behavior

- [x] 2.1 Add focused regression coverage proving the three charts order representative values highest-first while preserving the existing single-mode and `Both`-mode `sortValue` calculations.
- [x] 2.2 Run the web test suite and production build, then verify API Cost, API Time, and Token Usage render highest-to-lowest from left to right for single and `Both` output modes.
