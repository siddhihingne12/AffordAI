# AFFORDAI — System Architecture

## Overview

AFFORDAI uses a **hybrid architecture**: deterministic Python for all financial calculations and safety validation, with Google Gemini LLM/VLM for multimodal evidence extraction and natural language explanation generation.

**Core principle**: The LLM never performs arithmetic. All balance calculations, date handling, payment-plan simulation, and safety checks are deterministic Python code.

## System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AFFORDAI Pipeline                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. DATA INGESTION                                                  │
│     ├── requests.csv (250 requests)                                 │
│     ├── financial_profiles.csv (275 users)                          │
│     ├── financial_events.csv (25,342 events)                        │
│     ├── exchange_rates.csv (134 rates, 5 currency pairs)            │
│     ├── request_payment_options.csv (790 options)                   │
│     ├── messages.csv (215 messages, multilingual)                   │
│     └── images.csv + media/images/ (16 PNGs)                       │
│                                                                     │
│  2. EVIDENCE EXTRACTION (AI-powered)                                │
│     ├── VLM: 16 images → amounts (Gemini Vision)                   │
│     │   Types: payslips, rent receipts, invoices, taxi fares        │
│     └── LLM: 215 messages → financial signals (Gemini Flash)       │
│         Types: salary changes, refunds, income end, rent increases  │
│                                                                     │
│  3. FINANCIAL SAFETY TWIN (per user)                                │
│     ├── Current balance + minimum balance                           │
│     ├── Recurring expenses (detected from history patterns)         │
│     ├── Income streams (salary patterns + message adjustments)      │
│     ├── Pending/scheduled events                                    │
│     └── User preferences (priorities, methods, flexibility)         │
│                                                                     │
│  4. CASH-FLOW FORECAST ENGINE (deterministic)                       │
│     ├── Day-by-day balance simulation over 90 days                  │
│     ├── Projects recurring expenses + income                        │
│     ├── Accounts for pending/scheduled events                       │
│     ├── Currency conversion via exchange_rates.csv                  │
│     └── Tracks minimum balance reached                              │
│                                                                     │
│  5. WHAT-IF STRATEGY SIMULATOR                                      │
│     ├── BUY_NOW_FULL — pay everything today                        │
│     ├── INSTALLMENTS — use each installment plan                   │
│     ├── WAIT — postpone to earliest safe date                      │
│     ├── PARTIAL_PAYMENT — pay safe amount + defer rest             │
│     ├── REDUCE_SPENDING — stop/reduce flexible expenses            │
│     └── DO_NOT_PROCEED — fallback                                  │
│                                                                     │
│  6. SAFETY ENGINE (hard constraints)                                │
│     ├── Balance ≥ minimum at every point in forecast               │
│     ├── Essential expenses remain covered                           │
│     ├── Every installment affordable on its date                   │
│     ├── Plan completes by desired_completion_date                  │
│     └── User accepts the payment method                            │
│                                                                     │
│  7. DECISION AGENT (AI-powered)                                     │
│     ├── Takes computed results (no arithmetic)                      │
│     ├── Generates 1-2 sentence explanation                          │
│     └── Matches style patterns from sample outputs                 │
│                                                                     │
│  8. OUTPUT                                                          │
│     ├── output.csv (250 rows, exact schema)                        │
│     ├── EVALUATION_REPORT.md                                       │
│     └── Dashboard (React + Recharts)                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## AI vs Deterministic Responsibilities

| Task | Engine | Rationale |
|---|---|---|
| Image amount extraction | Gemini Vision | Unstructured visual data |
| Message financial signals | Gemini Flash | Multilingual text understanding |
| Decision explanation | Gemini Flash | Natural language generation |
| Balance calculations | Python | Must be exact — no hallucination |
| Recurring expense detection | Python | Pattern matching on dates/amounts |
| Cash-flow forecasting | Python | Day-by-day arithmetic |
| Strategy simulation | Python | Systematic what-if analysis |
| Safety constraint validation | Python | Hard rules — no approximation |
| Currency conversion | Python | Lookup from exchange_rates.csv |
| Date arithmetic | Python | Calendar operations |
| Payment plan construction | Python | Systematic date+amount scheduling |

## Financial Safety Twin

The Safety Twin is a structured snapshot of everything known about a user's financial state at the time of the request:

```python
FinancialSafetyTwin:
    user_id: str
    home_currency: str               # INR, ZAR, EUR, USD, or IDR
    current_balance: float           # From financial_profiles.csv
    minimum_balance: float           # User's preferred minimum
    
    income_streams: [IncomeStream]   # Detected salary patterns
    income_adjustments: [Adjustment] # From messages (raises, cuts)
    
    recurring_expenses: [Expense]    # Detected monthly patterns
        - category, median_amount, day_of_month
        - flexibility: fixed, stoppable, reducible, reducible_or_stoppable
        - minimum_allowed_amount (for reducible)
    
    pending_debits: [Event]          # Pending/scheduled outflows
    pending_credits: [Event]         # Pending/scheduled inflows
    
    priorities: [str]                # education, debt_repayment, etc.
    protected_categories: [str]      # Must never be cut
    willing_to_reduce: [str]         # User accepts reducing these
    willing_to_stop: [str]           # User accepts stopping these
    accepted_payment_methods: [str]  # full_payment, installments, etc.
    max_installment_months: int      # Cap on installment duration
```

## Recurring Expense Detection

The system detects recurring expenses from historical transaction patterns:

1. Group settled debit events by `user_id` + `category`
2. Sort by date and check for consistent intervals
3. If average interval is 20-35 days → monthly pattern
4. If average interval is 5-14 days → weekly pattern (summed to monthly)
5. Use median amount as the projected monthly expense
6. Use median day-of-month as the typical payment day
7. Carry the `flexibility` and `minimum_allowed_amount` from the most recent event

## Safety Rules

A strategy is **rejected** if ANY of these are violated:

1. **Balance Floor**: Balance drops below `minimum_balance_to_keep` at any point during the 90-day forecast
2. **Essential Coverage**: Protected expense categories become uncoverable
3. **Installment Safety**: Any installment payment cannot be made on its scheduled date
4. **Deadline**: Plan doesn't complete by `desired_completion_date`
5. **Method Acceptance**: User hasn't listed the required payment method in their preferences

## Event Status Handling

| Status | Counted? | Rationale |
|---|---|---|
| `settled` | ✅ For patterns | Already happened — used for recurring detection |
| `pending` | ✅ As future debit/credit | Money committed but not yet moved |
| `scheduled` | ✅ As future debit/credit | Confirmed future transaction |
| `cancelled` | ❌ Ignored | Never happening |
| `failed` | ❌ Ignored | Did not succeed |
| `unrealized` | ❌ Ignored | Not real cash (investment gains) |

## Message Adjustment Types

| Type | Real Money? | Action |
|---|---|---|
| `salary_change` | ✅ Yes | Update salary in twin |
| `salary_confirmed` | ✅ Yes | Confirm amount/date |
| `new_income` | ✅ Yes | Add income stream |
| `refund_completed` | ✅ Yes | Add pending credit |
| `prize_credited` | ✅ Yes | Add one-off credit |
| `income_end` | ⚠️ Removes | Zero out salary |
| `refund_pending` | ❌ Not yet | Don't count as cash |
| `bonus_unconfirmed` | ❌ Not guaranteed | Don't rely on it |
| `prize_pending` | ❌ Not yet | Don't count as cash |
| `income_pending` | ❌ Not yet | Don't count as cash |
| `investment_unrealized` | ❌ Not cash | Ignore |
| `internal_transfer` | ❌ Not income | Ignore |

## Strategy Selection

Among valid (safe) strategies, the best is selected by:

1. **Prefer user-accepted methods** — `payment_methods_user_will_consider`
2. **Minimize spending changes** — fewer adjustments = better
3. **Minimize total cost** — lower financing fees
4. **Maximize safety margin** — more buffer above minimum

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/requests` | List all requests with decisions |
| GET | `/api/requests/{id}` | Single request detail |
| GET | `/api/users/{id}/profile` | User financial profile |
| GET | `/api/users/{id}/forecast` | Cash-flow forecast for charts |
| POST | `/api/process/{id}` | Process a single request |
| POST | `/api/run` | Process all 250 requests |
| GET | `/api/evaluation` | Evaluation report |
| GET | `/api/sample-outputs` | Ground truth samples |
