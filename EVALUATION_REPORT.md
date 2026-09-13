# AFFORDAI — Evaluation Report

*Generated: 2026-09-13 17:57:05*

## Summary Metrics

| Metric | Score |
|---|---|
| Affordability Status Accuracy | 68.0% |
| Amount Safe to Pay Accuracy | 24.0% |
| Payment Method Accuracy | 72.0% |
| Payment Plan Accuracy | 72.0% |
| Earliest Date Accuracy | 20.0% |
| Spending Changes Accuracy | 84.0% |
| **Average Weighted Score** | **57.4%** |
| Average Amount Error | 206.5% |

*Evaluated 25 requests against ground truth.*

## Per-Request Results

| Request | Score | Status | Amount | Method | Plan | Date | Changes |
|---|---|---|---|---|---|---|---|
| request_01 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_02 | 10% | [FAIL] | [FAIL] (24%) | [FAIL] | [FAIL] | [FAIL] (±999d) | [OK] |
| request_03 | 80% | [OK] | [FAIL] (33%) | [OK] | [OK] | [OK] | [OK] |
| request_04 | 10% | [FAIL] | [FAIL] (51%) | [FAIL] | [FAIL] | [FAIL] (±11d) | [OK] |
| request_05 | 70% | [OK] | [FAIL] (2001%) | [OK] | [OK] | [FAIL] (±999d) | [OK] |
| request_06 | 55% | [FAIL] | [OK] | [OK] | [OK] | [FAIL] (±12d) | [FAIL] |
| request_07 | 70% | [OK] | [FAIL] (10%) | [OK] | [OK] | [FAIL] (±15d) | [OK] |
| request_08 | 10% | [FAIL] | [FAIL] (83%) | [FAIL] | [FAIL] | [FAIL] (±999d) | [OK] |
| request_09 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_10 | 70% | [OK] | [FAIL] (2000%) | [OK] | [OK] | [FAIL] (±999d) | [OK] |
| request_11 | 0% | [FAIL] | [FAIL] (49%) | [FAIL] | [FAIL] | [FAIL] (±999d) | [FAIL] |
| request_12 | 90% | [OK] | [OK] | [OK] | [OK] | [FAIL] (±76d) | [OK] |
| request_13 | 0% | [FAIL] | [FAIL] (117%) | [FAIL] | [FAIL] | [FAIL] (±69d) | [FAIL] |
| request_14 | 70% | [OK] | [FAIL] (30%) | [OK] | [OK] | [FAIL] (±999d) | [OK] |
| request_15 | 70% | [OK] | [FAIL] (177%) | [OK] | [OK] | [FAIL] (±999d) | [OK] |
| request_16 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_17 | 70% | [OK] | [FAIL] (13%) | [OK] | [OK] | [FAIL] (±46d) | [OK] |
| request_18 | 80% | [OK] | [FAIL] (14%) | [OK] | [OK] | [OK] | [OK] |
| request_19 | 35% | [OK] | [FAIL] (38%) | [FAIL] | [FAIL] | [FAIL] (±17d) | [OK] |
| request_20 | 70% | [OK] | [FAIL] (151%) | [OK] | [OK] | [FAIL] (±999d) | [OK] |
| request_21 | 55% | [FAIL] | [OK] | [OK] | [OK] | [FAIL] (±12d) | [FAIL] |
| request_22 | 70% | [OK] | [FAIL] (11%) | [OK] | [OK] | [FAIL] (±18d) | [OK] |
| request_23 | 10% | [FAIL] | [FAIL] (11%) | [FAIL] | [FAIL] | [FAIL] (±999d) | [OK] |
| request_24 | 70% | [OK] | [FAIL] (52%) | [OK] | [OK] | [FAIL] (±999d) | [OK] |
| request_25 | 70% | [OK] | [FAIL] (291%) | [OK] | [OK] | [FAIL] (±999d) | [OK] |

## Detailed Mismatches

### request_11 (score: 0%)

- **Status**: predicted `not_affordable`, expected `affordable_with_plan`
- **Amount**: predicted `6436793.21`, expected `12510645.00` (error: 48.5%)
- **Method**: predicted `not_recommended`, expected `full_payment`
- **Plan**: {'mismatch': 'one is none'}
- **Date**: off by 999 days
- **Changes**: mismatch

### request_13 (score: 0%)

- **Status**: predicted `affordable_with_plan`, expected `affordable_later`
- **Amount**: predicted `941.60`, expected `433.40` (error: 117.3%)
- **Method**: predicted `full_payment`, expected `wait`
- **Plan**: {'avg_date_diff': 69.0, 'avg_amount_error': 0.0}
- **Date**: off by 69 days
- **Changes**: mismatch

### request_02 (score: 10%)

- **Status**: predicted `not_affordable`, expected `affordable_with_plan`
- **Amount**: predicted `21412210.25`, expected `17229139.20` (error: 24.3%)
- **Method**: predicted `not_recommended`, expected `installments`
- **Plan**: {'mismatch': 'one is none'}
- **Date**: off by 999 days

### request_04 (score: 10%)

- **Status**: predicted `affordable_now`, expected `affordable_later`
- **Amount**: predicted `12693000.00`, expected `8401800.00` (error: 51.1%)
- **Method**: predicted `full_payment`, expected `wait`
- **Plan**: {'avg_date_diff': 11.0, 'avg_amount_error': 0.0}
- **Date**: off by 11 days

### request_08 (score: 10%)

- **Status**: predicted `not_affordable`, expected `affordable_later`
- **Amount**: predicted `521.57`, expected `284.57` (error: 83.3%)
- **Method**: predicted `not_recommended`, expected `wait`
- **Plan**: {'mismatch': 'one is none'}
- **Date**: off by 999 days

### request_23 (score: 10%)

- **Status**: predicted `not_affordable`, expected `affordable_later`
- **Amount**: predicted `10170.53`, expected `9152.00` (error: 11.1%)
- **Method**: predicted `not_recommended`, expected `wait`
- **Plan**: {'mismatch': 'one is none'}
- **Date**: off by 999 days

### request_19 (score: 35%)

- **Amount**: predicted `39660.00`, expected `28820.00` (error: 37.6%)
- **Method**: predicted `installments`, expected `partial_payment`
- **Plan**: {'avg_date_diff': 8.5, 'avg_amount_error': 0.5934614133788805}
- **Date**: off by 17 days

### request_06 (score: 55%)

- **Status**: predicted `affordable_now`, expected `affordable_with_plan`
- **Date**: off by 12 days
- **Changes**: mismatch

### request_21 (score: 55%)

- **Status**: predicted `affordable_now`, expected `affordable_with_plan`
- **Date**: off by 12 days
- **Changes**: mismatch

### request_05 (score: 70%)

- **Amount**: predicted `15488.00`, expected `737.00` (error: 2001.5%)
- **Date**: off by 999 days

### request_07 (score: 70%)

- **Amount**: predicted `95926.97`, expected `87170.56` (error: 10.0%)
- **Date**: off by 15 days

### request_10 (score: 70%)

- **Amount**: predicted `266700.00`, expected `12700.00` (error: 2000.0%)
- **Date**: off by 999 days

### request_14 (score: 70%)

- **Amount**: predicted `779.48`, expected `597.74` (error: 30.4%)
- **Date**: off by 999 days

### request_15 (score: 70%)

- **Amount**: predicted `230.14`, expected `83.05` (error: 177.1%)
- **Date**: off by 999 days

### request_17 (score: 70%)

- **Amount**: predicted `274600.00`, expected `243849.58` (error: 12.6%)
- **Date**: off by 46 days

### request_20 (score: 70%)

- **Amount**: predicted `13551.06`, expected `5400.00` (error: 150.9%)
- **Date**: off by 999 days

### request_22 (score: 70%)

- **Amount**: predicted `529.94`, expected `475.46` (error: 11.5%)
- **Date**: off by 18 days

### request_24 (score: 70%)

- **Amount**: predicted `20403.44`, expected `13420.00` (error: 52.0%)
- **Date**: off by 999 days

### request_25 (score: 70%)

- **Amount**: predicted `5573109.91`, expected `1425000.00` (error: 291.1%)
- **Date**: off by 999 days

### request_03 (score: 80%)

- **Amount**: predicted `1157048.76`, expected `873000.00` (error: 32.5%)

### request_18 (score: 80%)

- **Amount**: predicted `398.33`, expected `462.00` (error: 13.8%)

### request_12 (score: 90%)

- **Date**: off by 76 days
