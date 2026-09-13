"""
AFFORDAI Data Loader

Loads all CSV files from the dataset/ directory into structured DataFrames
and provides lookup functions for cross-referencing data.
"""

from __future__ import annotations
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from backend.config import DATASET_DIR
from backend.models import (
    FinancialRequest, UserProfile, FinancialEvent, PaymentOption,
    Message, ImageMapping, ExchangeRate,
)
from backend.utils import (
    parse_date, parse_float, parse_int, parse_pipe_list, parse_bool,
    CurrencyConverter,
)


@dataclass
class DataStore:
    """Central data store holding all loaded CSVs and lookup structures."""
    
    # Raw DataFrames
    requests_df: pd.DataFrame
    sample_requests_df: pd.DataFrame
    profiles_df: pd.DataFrame
    events_df: pd.DataFrame
    exchange_rates_df: pd.DataFrame
    payment_options_df: pd.DataFrame
    messages_df: pd.DataFrame
    images_df: pd.DataFrame
    
    # Parsed objects
    requests: dict[str, FinancialRequest]       # request_id -> FinancialRequest
    profiles: dict[str, UserProfile]             # user_id -> UserProfile
    events_by_user: dict[str, list[FinancialEvent]]  # user_id -> [events]
    events_by_id: dict[str, FinancialEvent]      # event_id -> FinancialEvent
    payment_options_by_request: dict[str, list[PaymentOption]]  # request_id -> [options]
    messages_by_user: dict[str, list[Message]]   # user_id -> [messages]
    messages_by_request: dict[str, list[Message]]  # request_id -> [messages]
    images_by_event: dict[str, ImageMapping]     # related_event_id -> ImageMapping
    images_list: list[ImageMapping]
    converter: CurrencyConverter
    
    # Sample ground truth for evaluation
    sample_outputs: dict[str, dict]  # request_id -> full sample row


def load_all_data() -> DataStore:
    """
    Load all CSV files from the dataset/ directory and build
    lookup structures for efficient cross-referencing.
    
    Returns:
        DataStore with all data loaded and indexed.
    """
    print("[DIR] Loading dataset files...")
    
    # ── Load raw CSVs ──────────────────────────────────────────────────────
    requests_df = pd.read_csv(DATASET_DIR / "requests.csv")
    sample_requests_df = pd.read_csv(DATASET_DIR / "sample_requests.csv")
    profiles_df = pd.read_csv(DATASET_DIR / "financial_profiles.csv")
    events_df = pd.read_csv(DATASET_DIR / "financial_events.csv")
    exchange_rates_df = pd.read_csv(DATASET_DIR / "exchange_rates.csv")
    payment_options_df = pd.read_csv(DATASET_DIR / "request_payment_options.csv")
    messages_df = pd.read_csv(DATASET_DIR / "messages.csv")
    images_df = pd.read_csv(DATASET_DIR / "images.csv")
    
    print(f"  OK requests.csv: {len(requests_df)} rows")
    print(f"  OK sample_requests.csv: {len(sample_requests_df)} rows")
    print(f"  OK financial_profiles.csv: {len(profiles_df)} rows")
    print(f"  OK financial_events.csv: {len(events_df)} rows")
    print(f"  OK exchange_rates.csv: {len(exchange_rates_df)} rows")
    print(f"  OK request_payment_options.csv: {len(payment_options_df)} rows")
    print(f"  OK messages.csv: {len(messages_df)} rows")
    print(f"  OK images.csv: {len(images_df)} rows")
    
    # ── Parse Requests ─────────────────────────────────────────────────────
    requests = {}
    for _, row in requests_df.iterrows():
        req = FinancialRequest(
            request_id=row["request_id"],
            user_id=row["user_id"],
            request_date=parse_date(str(row["request_date"])),
            request_type=row["request_type"],
            requested_amount=float(row["requested_amount"]),
            desired_completion_date=parse_date(str(row["desired_completion_date"])),
            allows_partial_payment=parse_bool(row["allows_partial_payment"]),
            request_text=str(row["request_text"]),
        )
        requests[req.request_id] = req
    
    # Also parse sample requests (they have input fields too)
    for _, row in sample_requests_df.iterrows():
        req = FinancialRequest(
            request_id=row["request_id"],
            user_id=row["user_id"],
            request_date=parse_date(str(row["request_date"])),
            request_type=row["request_type"],
            requested_amount=float(row["requested_amount"]),
            desired_completion_date=parse_date(str(row["desired_completion_date"])),
            allows_partial_payment=parse_bool(row["allows_partial_payment"]),
            request_text=str(row["request_text"]),
        )
        requests[req.request_id] = req
    
    # ── Parse Profiles ─────────────────────────────────────────────────────
    profiles = {}
    for _, row in profiles_df.iterrows():
        prof = UserProfile(
            user_id=row["user_id"],
            home_currency=row["home_currency"],
            current_available_balance=float(row["current_available_balance"]),
            minimum_balance_to_keep=float(row["minimum_balance_to_keep"]),
            financial_priorities=parse_pipe_list(str(row.get("financial_priorities", ""))),
            expense_categories_to_protect=parse_pipe_list(str(row.get("expense_categories_to_protect", ""))),
            expense_categories_user_is_willing_to_reduce=parse_pipe_list(str(row.get("expense_categories_user_is_willing_to_reduce", ""))),
            expense_categories_user_is_willing_to_stop=parse_pipe_list(str(row.get("expense_categories_user_is_willing_to_stop", ""))),
            payment_methods_user_will_consider=parse_pipe_list(str(row.get("payment_methods_user_will_consider", ""))),
            max_installment_months=parse_int(row.get("max_installment_months")),
        )
        profiles[prof.user_id] = prof
    
    # ── Parse Financial Events ─────────────────────────────────────────────
    events_by_user: dict[str, list[FinancialEvent]] = {}
    events_by_id: dict[str, FinancialEvent] = {}
    
    for _, row in events_df.iterrows():
        evt = FinancialEvent(
            event_id=row["event_id"],
            user_id=row["user_id"],
            event_type=str(row["event_type"]),
            description=str(row["description"]),
            category=str(row["category"]),
            direction=str(row["direction"]),
            amount=parse_float(row.get("amount")),
            currency=str(row["currency"]),
            event_date=parse_date(str(row["event_date"])),
            settlement_date=parse_date(str(row.get("settlement_date", ""))),
            status=str(row["status"]),
            linked_event_id=str(row.get("linked_event_id", "")) if pd.notna(row.get("linked_event_id")) else None,
            flexibility=str(row.get("flexibility", "fixed")),
            minimum_allowed_amount=parse_float(row.get("minimum_allowed_amount")),
        )
        events_by_user.setdefault(evt.user_id, []).append(evt)
        events_by_id[evt.event_id] = evt
    
    # ── Parse Payment Options ──────────────────────────────────────────────
    payment_options_by_request: dict[str, list[PaymentOption]] = {}
    
    for _, row in payment_options_df.iterrows():
        opt = PaymentOption(
            payment_option_id=row["payment_option_id"],
            request_id=row["request_id"],
            payment_method=str(row["payment_method"]),
            payment_amount=float(row["payment_amount"]),
            number_of_payments=int(row["number_of_payments"]),
            first_payment_date=parse_date(str(row.get("first_payment_date", ""))),
            payment_frequency_days=parse_int(row.get("payment_frequency_days")),
            financing_fee=float(row.get("financing_fee", 0)),
            total_payable_amount=float(row["total_payable_amount"]),
        )
        payment_options_by_request.setdefault(opt.request_id, []).append(opt)
    
    # ── Parse Messages ─────────────────────────────────────────────────────
    messages_by_user: dict[str, list[Message]] = {}
    messages_by_request: dict[str, list[Message]] = {}
    
    for _, row in messages_df.iterrows():
        msg = Message(
            message_id=row["message_id"],
            user_id=row["user_id"],
            request_id=str(row.get("request_id", "")) if pd.notna(row.get("request_id")) else None,
            related_event_id=str(row.get("related_event_id", "")) if pd.notna(row.get("related_event_id")) else None,
            sent_at=str(row["sent_at"]),
            source_type=str(row["source_type"]),
            message_text=str(row["message_text"]),
        )
        messages_by_user.setdefault(msg.user_id, []).append(msg)
        if msg.request_id:
            messages_by_request.setdefault(msg.request_id, []).append(msg)
    
    # ── Parse Images ───────────────────────────────────────────────────────
    images_by_event: dict[str, ImageMapping] = {}
    images_list: list[ImageMapping] = []
    
    for _, row in images_df.iterrows():
        img = ImageMapping(
            image_id=row["image_id"],
            user_id=row["user_id"],
            request_id=str(row.get("request_id", "")) if pd.notna(row.get("request_id")) else None,
            related_event_id=str(row["related_event_id"]),
        )
        images_by_event[img.related_event_id] = img
        images_list.append(img)
    
    # ── Currency Converter ─────────────────────────────────────────────────
    converter = CurrencyConverter(exchange_rates_df)
    
    # ── Sample Outputs for Evaluation ──────────────────────────────────────
    sample_outputs = {}
    for _, row in sample_requests_df.iterrows():
        sample_outputs[row["request_id"]] = row.to_dict()
    
    print(f"\n[OK] Data loaded: {len(requests)} requests, {len(profiles)} profiles, "
          f"{sum(len(v) for v in events_by_user.values())} events")
    
    return DataStore(
        requests_df=requests_df,
        sample_requests_df=sample_requests_df,
        profiles_df=profiles_df,
        events_df=events_df,
        exchange_rates_df=exchange_rates_df,
        payment_options_df=payment_options_df,
        messages_df=messages_df,
        images_df=images_df,
        requests=requests,
        profiles=profiles,
        events_by_user=events_by_user,
        events_by_id=events_by_id,
        payment_options_by_request=payment_options_by_request,
        messages_by_user=messages_by_user,
        messages_by_request=messages_by_request,
        images_by_event=images_by_event,
        images_list=images_list,
        converter=converter,
        sample_outputs=sample_outputs,
    )
