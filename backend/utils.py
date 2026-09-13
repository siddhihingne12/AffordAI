"""
AFFORDAI Utility Functions

Currency conversion using exchange_rates.csv and date arithmetic helpers.
"""

from __future__ import annotations
from datetime import date, timedelta
from typing import Optional
import pandas as pd


class CurrencyConverter:
    """
    Convert amounts between currencies using provided exchange rates.
    
    The exchange_rates.csv provides directional rates (e.g. EUR→ZAR = 20).
    We also support reverse lookups (ZAR→EUR = 1/20).
    """

    def __init__(self, rates_df: pd.DataFrame):
        """
        Args:
            rates_df: DataFrame with columns [rate_date, from_currency, to_currency, rate]
        """
        self.rates_df = rates_df.copy()
        self.rates_df["rate_date"] = pd.to_datetime(self.rates_df["rate_date"]).dt.date
        self.rates_df["rate"] = self.rates_df["rate"].astype(float)
        
        # Build reverse rates too
        reverse = self.rates_df.copy()
        reverse["from_currency"], reverse["to_currency"] = (
            reverse["to_currency"].copy(),
            reverse["from_currency"].copy(),
        )
        reverse["rate"] = 1.0 / reverse["rate"]
        
        self.all_rates = pd.concat([self.rates_df, reverse], ignore_index=True)
    
    def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        ref_date: date,
    ) -> float:
        """
        Convert amount from one currency to another using the nearest
        available exchange rate to ref_date.
        
        Returns the converted amount, or the original amount if currencies match.
        """
        if from_currency == to_currency:
            return amount
        
        # Find rates for this currency pair
        pair_rates = self.all_rates[
            (self.all_rates["from_currency"] == from_currency)
            & (self.all_rates["to_currency"] == to_currency)
        ].copy()
        
        if pair_rates.empty:
            # Try chaining through USD
            return self._chain_convert(amount, from_currency, to_currency, ref_date)
        
        # Find nearest rate by date
        pair_rates["date_diff"] = pair_rates["rate_date"].apply(
            lambda d: abs((d - ref_date).days)
        )
        nearest = pair_rates.loc[pair_rates["date_diff"].idxmin()]
        
        return amount * nearest["rate"]
    
    def _chain_convert(
        self, amount: float, from_curr: str, to_curr: str, ref_date: date
    ) -> float:
        """Chain conversion through USD: from → USD → to."""
        # Try from_curr → USD → to_curr
        try:
            usd_amount = self.convert(amount, from_curr, "USD", ref_date)
            return self.convert(usd_amount, "USD", to_curr, ref_date)
        except Exception:
            pass
        
        # Try from_curr → EUR → to_curr
        try:
            eur_amount = self.convert(amount, from_curr, "EUR", ref_date)
            return self.convert(eur_amount, "EUR", to_curr, ref_date)
        except Exception:
            pass
        
        raise ValueError(
            f"Cannot convert {from_curr} → {to_curr}: no rate path found"
        )


def parse_date(date_str: str) -> Optional[date]:
    """Parse a YYYY-MM-DD date string, returning None for empty/invalid."""
    if not date_str or not isinstance(date_str, str) or not date_str.strip():
        return None
    try:
        return date.fromisoformat(date_str.strip())
    except (ValueError, TypeError):
        return None


def parse_float(val) -> Optional[float]:
    """Parse a float value, returning None for empty/invalid."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_int(val) -> Optional[int]:
    """Parse an int value, returning None for empty/invalid."""
    f = parse_float(val)
    if f is None:
        return None
    return int(f)


def parse_pipe_list(val: str) -> list[str]:
    """Parse a pipe-separated list like 'rent|utilities|groceries'."""
    if not val or not isinstance(val, str) or not val.strip():
        return []
    return [item.strip() for item in val.split("|") if item.strip()]


def parse_bool(val) -> bool:
    """Parse a boolean value from various string representations."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return bool(val)


def format_amount(amount: float) -> str:
    """
    Format an amount for output, matching the sample output style.
    Remove unnecessary trailing zeros but keep precision when needed.
    """
    if amount == int(amount):
        return str(int(amount))
    
    # Format with 2 decimal places, then strip trailing zeros
    formatted = f"{amount:.2f}"
    # But keep at least the significant decimals
    if "." in formatted:
        formatted = formatted.rstrip("0")
        if formatted.endswith("."):
            formatted = formatted[:-1]
    return formatted


def format_payment_plan(entries: list) -> str:
    """
    Format payment plan entries as 'YYYY-MM-DD:amount|YYYY-MM-DD:amount'.
    Returns 'none' if empty.
    """
    if not entries:
        return "none"
    parts = []
    for entry in entries:
        date_str = entry.payment_date.isoformat()
        amt_str = format_amount(entry.amount)
        parts.append(f"{date_str}:{amt_str}")
    return "|".join(parts)


def format_spending_changes(changes: list) -> str:
    """
    Format spending changes as pipe-separated string.
    Returns 'none' if empty.
    """
    if not changes:
        return "none"
    return "|".join(c.to_string() for c in changes)


def add_months(d: date, months: int) -> date:
    """Add months to a date, clamping to month end if needed."""
    month = d.month + months
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    day = min(d.day, max_day)
    return date(year, month, day)


def date_range(start: date, end: date) -> list[date]:
    """Generate a list of dates from start to end (inclusive)."""
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]
