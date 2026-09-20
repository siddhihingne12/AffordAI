# AFFORDAI — Evaluation Report

*Generated: 2026-09-20 12:29:09*

## Summary Metrics

| Metric | Score |
|---|---|
| Affordability Status Accuracy | 96.0% |
| Amount Safe to Pay Accuracy | 92.0% |
| Payment Method Accuracy | 96.0% |
| Payment Plan Accuracy | 96.0% |
| Earliest Date Accuracy | 96.0% |
| Spending Changes Accuracy | 96.0% |
| **Average Weighted Score** | **95.2%** |
| Average Amount Error | 5.3% |

*Evaluated 25 requests against ground truth.*

## Per-Request Results

| Request | Score | Status | Amount | Method | Plan | Date | Changes |
|---|---|---|---|---|---|---|---|
| request_01 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_02 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_03 | 80% | [OK] | [FAIL] (33%) | [OK] | [OK] | [OK] | [OK] |
| request_04 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_05 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_06 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_07 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_08 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_09 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_10 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_11 | 0% | [FAIL] | [FAIL] (100%) | [FAIL] | [FAIL] | [FAIL] (±999d) | [FAIL] |
| request_12 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_13 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_14 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_15 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_16 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_17 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_18 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_19 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_20 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_21 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_22 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_23 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_24 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |
| request_25 | 100% | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] |

## Detailed Mismatches

### request_11 (score: 0%)

- **Status**: predicted `not_affordable`, expected `affordable_with_plan`
- **Amount**: predicted `0.00`, expected `12510645.00` (error: 100.0%)
- **Method**: predicted `not_recommended`, expected `full_payment`
- **Plan**: {'mismatch': 'one is none'}
- **Date**: off by 999 days
- **Changes**: mismatch

### request_03 (score: 80%)

- **Amount**: predicted `1157048.76`, expected `873000.00` (error: 32.5%)
