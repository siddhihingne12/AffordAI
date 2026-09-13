# AFFORDAI

> **AI-Powered Financial Affordability & Safe Spending Agent**  
> *"Don't ask if you have enough money. Ask if you can safely afford it."*

AFFORDAI is a multimodal AI financial agent that determines whether a user can safely afford a requested expense. It analyzes future cash flow, recurring expenses, pending payments, confirmed income, payment preferences, and information extracted from messages and images to produce personalized, actionable recommendations.

## Quick Start

### Prerequisites

- Python 3.11+
- Google Gemini API key ([Get one here](https://aistudio.google.com))
- Node.js 18+ (for dashboard)

### Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 3. Run the agent
python run_agent.py --all        # Process all 275 requests
python run_agent.py --requests   # Process only the 250 output requests (default)
python run_agent.py --samples    # Process only the 25 sample requests

# 4. Start the API server
uvicorn backend.app:app --reload --port 8000

# 5. Start the dashboard
cd frontend
npm install
npm run dev
```

### Output

The agent produces `dataset/output.csv` with 250 rows containing:

| Column | Description |
|---|---|
| `request_id` | Unique identifier (request_26 to request_275) |
| `amount_safe_to_pay` | Maximum amount safely payable today |
| `affordability_status` | `affordable_now`, `affordable_with_plan`, `affordable_later`, `not_affordable` |
| `recommended_payment_method` | `full_payment`, `partial_payment`, `installments`, `wait`, `not_recommended` |
| `payment_plan` | Date:amount pairs separated by `\|` or `none` |
| `earliest_date_for_full_payment` | YYYY-MM-DD or empty |
| `spending_changes_needed` | `none`, `stop:event_id`, `reduce_to:event_id:amount` |
| `decision_explanation` | Personalized 1-2 sentence explanation |

## Architecture

```
User Request → Data Loader → Evidence Extraction (VLM/LLM)
    → Financial Safety Twin → Cash-Flow Forecast (90 days)
    → What-If Strategy Simulator (6 strategies)
    → Safety Engine (hard constraints)
    → Decision Agent (LLM explanation)
    → output.csv + Dashboard
```

**Design Principle**: LLM handles understanding & explanation. Python handles all financial math and safety validation.

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

## Dataset

| File | Records | Purpose |
|---|---|---|
| `requests.csv` | 250 | Financial requests to evaluate |
| `sample_requests.csv` | 25 | Ground truth for evaluation |
| `financial_profiles.csv` | 275 | User profiles with balances & preferences |
| `financial_events.csv` | 25,342 | Transaction history |
| `exchange_rates.csv` | 134 | Currency conversion rates |
| `request_payment_options.csv` | 790 | Available payment plans |
| `messages.csv` | 215 | Messages with financial signals |
| `images.csv` | 16 | Image-to-event mappings |
| `media/images/` | 16 PNGs | Receipts, payslips, invoices |

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for complete schema documentation.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| LLM/VLM | Google Gemini 2.5 Flash |
| Data | pandas |
| Backend API | FastAPI |
| Frontend | React + Vite + Recharts |
| Validation | Pydantic |
| Evaluation | Custom Python metrics |

## Evaluation

The agent is evaluated against 25 ground-truth samples using:

- **Affordability Status Accuracy** — exact match
- **Amount Safe to Pay Accuracy** — within ±5%
- **Payment Method Accuracy** — exact match
- **Payment Plan Accuracy** — dates ±3 days, amounts ±5%
- **Earliest Date Accuracy** — within ±3 days
- **Spending Changes Accuracy** — exact match
- **Safety Violation Rate** — target 0%

```bash
python run_agent.py --all  # Processes samples + generates EVALUATION_REPORT.md
```

## Project Structure

```
AFFAI/
├── dataset/                    # CSV data + images
├── backend/
│   ├── config.py               # Configuration & constants
│   ├── models.py               # Data models & schemas
│   ├── utils.py                # Currency conversion & helpers
│   ├── data_loader.py          # CSV ingestion & indexing
│   ├── evidence_extractor.py   # VLM image + LLM message extraction
│   ├── profile_builder.py      # Financial Safety Twin builder
│   ├── forecast_engine.py      # Day-by-day cash-flow simulation
│   ├── strategy_simulator.py   # What-If payment strategies
│   ├── safety_engine.py        # Hard constraint validation
│   ├── decision_agent.py       # LLM explanation generation
│   ├── output_writer.py        # CSV output formatter
│   └── app.py                  # FastAPI REST API
├── evaluation/
│   ├── evaluate.py             # Evaluation runner
│   └── metrics.py              # Accuracy metrics
├── frontend/                   # React dashboard
├── run_agent.py                # Main entry point
├── requirements.txt
├── README.md
├── ARCHITECTURE.md
└── DATA_DICTIONARY.md
```
