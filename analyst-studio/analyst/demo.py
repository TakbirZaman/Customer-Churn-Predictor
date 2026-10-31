"""Deterministic demonstration: real calculations, no simulated AI response."""
from pathlib import Path
import shutil
from .tools import Toolbox


def run(workspace):
    ws=Toolbox(workspace)
    source=Path(__file__).resolve().parent.parent/'data'/'demo_sales.csv'
    shutil.copyfile(source,ws.data/'demo_sales.csv')
    profile=ws.inspect_data('demo_sales.csv')
    totals=ws.aggregate('demo_sales.csv','revenue',group_by=['category'])
    monthly=ws.aggregate('demo_sales.csv','revenue',date_column='date')
    chart=ws.chart('outputs/'+monthly['artifact'],'_period','value','line','Monthly revenue · synthetic demo')
    total=totals['independent_sum_check']
    text=f'''## Summary
The synthetic demo contains {profile['rows']} rows and total revenue of **{total:,.0f} BDT**.
This report uses deterministic calculations; no language model was called.

## Data & Method
Source: demo_sales.csv. Grouped pandas sums, cross-checked using math.fsum.
The sample's currency is BDT. All records are retained; missing group labels are retained.

## Findings
- Duplicate rows: {profile['duplicate_rows']}.
- Monthly figures: {monthly['rows']}.
- Category figures: {totals['rows']}.

## Recommendations
Inspect category margins and customer acquisition costs before deciding where to invest.

## Risks
Synthetic data cannot establish demand, profitability, or causality. No market research performed.

## Sources
Bundled synthetic demo_sales.csv. Chart: {chart['artifact']}.
'''
    report=ws.write_report('Demo analysis',text)
    return {'profile':profile,'totals':totals,'monthly':monthly,'chart':chart,'report':report,'text':text}
