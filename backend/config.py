"""
AFFORDAI Configuration Module

Handles environment variables, Gemini client initialization,
and project-wide constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
MEDIA_DIR = DATASET_DIR / "media" / "images"

# ── Environment ────────────────────────────────────────────────────────────────
load_dotenv(PROJECT_ROOT / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Gemini Client ──────────────────────────────────────────────────────────────
_client = None

def get_gemini_client() -> genai.Client:
    """Lazy-initialize and return the Gemini client."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY not set. Copy .env.example to .env and add your key."
            )
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

# ── Model Config ───────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"

# ── Financial Constants ────────────────────────────────────────────────────────
FORECAST_DAYS = 90  # Look-ahead window for cash-flow simulation

# ── Affordability Status Enum Values ───────────────────────────────────────────
STATUS_AFFORDABLE_NOW = "affordable_now"
STATUS_AFFORDABLE_WITH_PLAN = "affordable_with_plan"
STATUS_AFFORDABLE_LATER = "affordable_later"
STATUS_NOT_AFFORDABLE = "not_affordable"

VALID_STATUSES = {
    STATUS_AFFORDABLE_NOW,
    STATUS_AFFORDABLE_WITH_PLAN,
    STATUS_AFFORDABLE_LATER,
    STATUS_NOT_AFFORDABLE,
}

# ── Recommended Payment Method Enum Values ─────────────────────────────────────
METHOD_FULL_PAYMENT = "full_payment"
METHOD_PARTIAL_PAYMENT = "partial_payment"
METHOD_INSTALLMENTS = "installments"
METHOD_WAIT = "wait"
METHOD_NOT_RECOMMENDED = "not_recommended"

VALID_METHODS = {
    METHOD_FULL_PAYMENT,
    METHOD_PARTIAL_PAYMENT,
    METHOD_INSTALLMENTS,
    METHOD_WAIT,
    METHOD_NOT_RECOMMENDED,
}

# ── Event Status Values ────────────────────────────────────────────────────────
EVENT_SETTLED = "settled"
EVENT_PENDING = "pending"
EVENT_SCHEDULED = "scheduled"
EVENT_CANCELLED = "cancelled"
EVENT_FAILED = "failed"
EVENT_UNREALIZED = "unrealized"

# Statuses that represent real money movement
ACTIVE_EVENT_STATUSES = {EVENT_SETTLED, EVENT_PENDING, EVENT_SCHEDULED}
# Statuses to ignore in forecasting
IGNORED_EVENT_STATUSES = {EVENT_CANCELLED, EVENT_FAILED, EVENT_UNREALIZED}

# ── Event Flexibility Values ───────────────────────────────────────────────────
FLEX_FIXED = "fixed"
FLEX_STOPPABLE = "stoppable"
FLEX_REDUCIBLE = "reducible"
FLEX_REDUCIBLE_OR_STOPPABLE = "reducible_or_stoppable"

# ── Supported Currencies ───────────────────────────────────────────────────────
SUPPORTED_CURRENCIES = {"INR", "ZAR", "EUR", "USD", "IDR"}
