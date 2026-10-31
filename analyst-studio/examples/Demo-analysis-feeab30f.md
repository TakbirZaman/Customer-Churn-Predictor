# Demo analysis

## Summary
The synthetic demo contains 6 rows and total revenue of **63,000 BDT**.
This report uses deterministic calculations; no language model was called.

## Data & Method
Source: demo_sales.csv. Grouped pandas sums, cross-checked using math.fsum.
The sample's currency is BDT. All records are retained; missing group labels are retained.

## Findings
- Duplicate rows: 0.
- Monthly figures: [{'_period': '2026-01', 'value': 16000}, {'_period': '2026-02', 'value': 30000}, {'_period': '2026-03', 'value': 17000}].
- Category figures: [{'category': 'Services', 'value': 48000}, {'category': 'Software', 'value': 15000}].

## Recommendations
Inspect category margins and customer acquisition costs before deciding where to invest.

## Risks
Synthetic data cannot establish demand, profitability, or causality. No market research performed.

## Sources
Bundled synthetic demo_sales.csv. Chart: chart_e032a981.png.
