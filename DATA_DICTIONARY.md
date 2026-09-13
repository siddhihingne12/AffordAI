# AFFORDAI — Data Dictionary

Complete schema documentation for all dataset files. All information verified from actual CSV inspection.

## Relationships

```
financial_profiles (user_id) ──┐
                               ├──> requests (user_id, request_id)
financial_events (user_id) ────┘         │
       │                                 │
       │ event_id ←── related_event_id   ├──> request_payment_options (request_id)
       │                                 │
       └──── images (related_event_id) ──┘
             messages (user_id, request_id, related_event_id)
             exchange_rates (currency conversion)
```

---

## requests.csv

**250 rows** — Financial requests to evaluate (request_26 to request_275).

| Column | Type | Example | Description |
|---|---|---|---|
| `request_id` | string | `request_26` | Unique request identifier |
| `user_id` | string | `user_26` | Links to financial_profiles |
| `request_date` | date | `2025-08-03` | Date the request was made |
| `request_type` | string | `purchase` | Category of the request |
| `requested_amount` | float | `15656000` | Amount requested in user's home currency |
| `desired_completion_date` | date | `2025-10-07` | Deadline for completing payment |
| `allows_partial_payment` | boolean | `false` | Whether partial payment is acceptable |
| `request_text` | string | *varies* | Natural language description of the request |

**Request types (9)**: `family_transfer` (28), `purchase` (28), `investment` (28), `debt_repayment` (28), `travel` (28), `housing` (28), `education` (28), `emergency_expense` (27), `other` (27)

**Currencies found in request text**: INR (60), EUR (54), ZAR (47), IDR (50), USD (39)

---

## sample_requests.csv

**25 rows** — Ground truth for evaluation (request_01 to request_25). Contains all columns from `requests.csv` plus the 7 output columns.

**Status distribution**: `affordable_now` (3), `affordable_with_plan` (9), `affordable_later` (6), `not_affordable` (7)

**Method distribution**: `full_payment` (6), `installments` (5), `wait` (6), `not_recommended` (7), `partial_payment` (1)

---

## financial_profiles.csv

**275 rows** — One row per user.

| Column | Type | Example | Description |
|---|---|---|---|
| `user_id` | string | `user_01` | Unique user identifier |
| `home_currency` | string | `ZAR` | User's primary currency |
| `current_available_balance` | float | `58481.1` | Current bank balance |
| `minimum_balance_to_keep` | float | `18000` | User's preferred minimum balance |
| `financial_priorities` | pipe-list | `education\|debt_repayment` | Ranked priorities |
| `expense_categories_to_protect` | pipe-list | `rent\|education\|groceries` | Cannot be reduced |
| `expense_categories_user_is_willing_to_reduce` | pipe-list | `dining` | Can be reduced |
| `expense_categories_user_is_willing_to_stop` | pipe-list | `delivery_membership` | Can be stopped |
| `payment_methods_user_will_consider` | pipe-list | `full_payment` | Accepted methods |
| `max_installment_months` | int/empty | `` | Max installment duration (blank = no limit) |

**Home currencies**: INR, ZAR, EUR, USD, IDR

**Payment methods**: `full_payment`, `installments`, `partial_payment`

---

## financial_events.csv

**25,342 rows** — Transaction history for all 275 users (56-129 events per user).

| Column | Type | Example | Description |
|---|---|---|---|
| `event_id` | string | `event_01` | Unique event identifier |
| `user_id` | string | `user_01` | Links to financial_profiles |
| `event_type` | string | `expense` | Type of event |
| `description` | string | `Apartment rent transfer` | Human-readable description |
| `category` | string | `rent` | Expense/income category |
| `direction` | string | `debit` | `debit` (money out) or `credit` (money in) |
| `amount` | float/blank | `5148` | Amount (**blank for 16 events** — extract from images) |
| `currency` | string | `ZAR` | Currency of the amount |
| `event_date` | date | `2023-10-02` | When the event occurred |
| `settlement_date` | date/blank | `2023-10-02` | When the money moved |
| `status` | string | `settled` | Current event status |
| `linked_event_id` | string/blank | `` | Related event (e.g., refund → original purchase) |
| `flexibility` | string | `fixed` | How adjustable this expense is |
| `minimum_allowed_amount` | float/blank | `` | Minimum if reduced |

**Event types (8)**: `income`, `expense`, `subscription`, `debt_payment`, `refund`, `investment_purchase`, `investment_sale`, `investment_valuation`

**Event statuses (6)**: `settled`, `pending`, `scheduled`, `cancelled`, `failed`, `unrealized`

**Flexibility types (4)**: `fixed`, `stoppable`, `reducible`, `reducible_or_stoppable`

**Events with blank amounts (16)**: Each maps to an image in images.csv:
- `event_253` (salary), `event_1442` (rent), `event_1545` (groceries), `event_1700` (groceries), `event_1786` (utilities), `event_3051` (groceries), `event_3231` (dining), `event_4535` (housing), `event_5170` (utilities), `event_6033` (groceries), `event_6859` (healthcare), `event_7307` (transport), `event_7941` (shopping), `event_9421` (healthcare), `event_9806` (transport), `event_10521` (transport)

---

## exchange_rates.csv

**134 rows** — Currency exchange rates for 5 currency pairs.

| Column | Type | Example | Description |
|---|---|---|---|
| `rate_date` | date | `2023-10-15` | Date of the rate |
| `from_currency` | string | `EUR` | Source currency |
| `to_currency` | string | `ZAR` | Target currency |
| `rate` | float | `20` | Conversion multiplier |

**Currency pairs**: EUR→ZAR, EUR→USD, USD→IDR, USD→INR, USD→EUR

**Date range**: 2023-10-15 to 2026-11-15

---

## request_payment_options.csv

**790 rows** — 2-4 payment options per request.

| Column | Type | Example | Description |
|---|---|---|---|
| `payment_option_id` | string | `payment_option_01` | Unique option identifier |
| `request_id` | string | `request_01` | Links to requests |
| `payment_method` | string | `full_payment` | Method type |
| `payment_amount` | float | `25256` | Amount per payment |
| `number_of_payments` | int | `1` | Number of installments |
| `first_payment_date` | date/blank | `2024-03-03` | When first payment is due |
| `payment_frequency_days` | int/blank | `` | Days between installments |
| `financing_fee` | float | `0` | Additional fees |
| `total_payable_amount` | float | `25256` | Total including fees |

**Payment methods**: `full_payment`, `installments`

---

## messages.csv

**215 rows** — Messages containing financial signals (English and Indonesian).

| Column | Type | Example | Description |
|---|---|---|---|
| `message_id` | string | `message_01` | Unique message identifier |
| `user_id` | string | `user_02` | Links to financial_profiles |
| `request_id` | string/blank | `` | Links to specific request (128 linked) |
| `related_event_id` | string/blank | `` | Links to specific event |
| `sent_at` | datetime | `2025-07-29T09:30:00Z` | Timestamp |
| `source_type` | string | `employer` | Who sent the message |
| `message_text` | string | *varies* | Full message content |

**Users with messages**: 215 (one per user)

**Messages linked to requests**: 128

---

## images.csv

**16 rows** — Maps images to events with blank amounts.

| Column | Type | Example | Description |
|---|---|---|---|
| `image_id` | string | `image_01` | Unique image identifier |
| `user_id` | string | `user_03` | Links to financial_profiles |
| `request_id` | string | `request_03` | Links to requests |
| `related_event_id` | string | `event_253` | Event with blank amount |

**Image types found**: Pay slips (salary details), rent receipts, grocery invoices, maintenance invoices, taxi fare receipts, airline tickets, EV charging receipts, pharmacy bills, hospital bills, shopping receipts.

---

## output.csv (Template)

**250 rows** — Blank template to fill (request_26 to request_275).

| Column | Type | Description |
|---|---|---|
| `request_id` | string | Must match requests.csv |
| `amount_safe_to_pay` | float | Maximum safely payable today |
| `affordability_status` | string | One of 4 status values |
| `recommended_payment_method` | string | One of 5 method values |
| `payment_plan` | string | `YYYY-MM-DD:amount\|...` or `none` |
| `earliest_date_for_full_payment` | string | `YYYY-MM-DD` or empty |
| `spending_changes_needed` | string | `none`, `stop:event_id`, `reduce_to:event_id:amount` |
| `decision_explanation` | string | 1-2 sentence explanation |

### Output Format Examples (from ground truth)

**affordable_now + full_payment**:
```
amount_safe_to_pay: 25256
payment_plan: 2024-03-03:25256
spending_changes_needed: none
```

**affordable_with_plan + installments**:
```
amount_safe_to_pay: 17229139.2
payment_plan: 2025-08-08:15952906.67|2025-09-07:15952906.67|2025-10-07:15952906.67
spending_changes_needed: none
```

**affordable_with_plan + spending changes**:
```
spending_changes_needed: stop:event_476
spending_changes_needed: reduce_to:event_989:665950
spending_changes_needed: stop:event_1815|reduce_to:event_1816:23.50
```

**affordable_later + wait**:
```
payment_plan: 2019-11-15:5491000
earliest_date_for_full_payment: 2019-11-15
```

**not_affordable**:
```
payment_plan: none
earliest_date_for_full_payment: (empty)
```
