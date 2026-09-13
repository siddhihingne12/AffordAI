"""
AFFORDAI Evidence Extractor

Handles two key tasks:
1. VLM Image Extraction — Extract amounts from 16 PNG images using Gemini Vision
2. LLM Message Parsing — Extract financial signals from 215 messages (multilingual)
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Optional

from backend.config import get_gemini_client, GEMINI_MODEL, MEDIA_DIR
from backend.data_loader import DataStore
from backend.models import MessageAdjustment, ImageMapping
from backend.utils import parse_date, parse_float


# ═══════════════════════════════════════════════════════════════════════════════
# Image Amount Extraction (VLM)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_image_amounts(data: DataStore) -> dict[str, float]:
    """
    Extract amounts from images for events with blank amount fields.
    
    Each of the 16 images in images.csv corresponds to an event in
    financial_events.csv that has a blank 'amount'. The image contains
    a receipt, payslip, invoice, or similar document with the amount.
    
    Returns:
        dict mapping event_id -> extracted amount
    """
    client = get_gemini_client()
    extracted = {}
    
    print("\n[IMG]  Extracting amounts from images...")
    
    for img_mapping in data.images_list:
        event = data.events_by_id.get(img_mapping.related_event_id)
        if event is None:
            print(f"   Event {img_mapping.related_event_id} not found")
            continue
        
        # Only process events with blank amounts
        if event.amount is not None:
            extracted[event.event_id] = event.amount
            continue
        
        image_path = MEDIA_DIR / f"{img_mapping.image_id}.png"
        if not image_path.exists():
            print(f"   Image {image_path} not found")
            continue
        
        try:
            amount = _extract_amount_from_image(client, image_path, event)
            if amount is not None:
                extracted[event.event_id] = amount
                # Update the event in the data store
                event.amount = amount
                print(f"  OK {img_mapping.image_id} → {event.event_id}: "
                      f"{event.currency} {amount:,.2f} ({event.description})")
            else:
                print(f"  FAIL {img_mapping.image_id}: could not extract amount")
        except Exception as e:
            print(f"  FAIL {img_mapping.image_id} error: {e}")
        
        # Rate limiting
        time.sleep(1)
    
    print(f"\n[OK] Extracted {len(extracted)} amounts from images")
    return extracted


def _extract_amount_from_image(client, image_path: Path, event) -> Optional[float]:
    """
    Send an image to Gemini Vision and extract the relevant financial amount.
    
    Uses the event's description, category, and currency as context to help
    the model identify the correct amount on the document.
    """
    # Read image bytes
    image_bytes = image_path.read_bytes()
    
    prompt = f"""Extract the total payment amount from this financial document.

Context about the transaction:
- Description: {event.description}
- Category: {event.category}
- Direction: {event.direction} (debit = money going out, credit = money coming in)
- Currency: {event.currency}
- Event type: {event.event_type}

Instructions:
- Look for the total amount, net pay, total payable, balance due, fare amount, or final amount.
- If the document is a payslip, extract the NET PAY (take-home salary), not gross pay.
- If the document is an invoice, extract the total amount or balance due.
- If the document is a receipt, extract the total amount paid.
- Return ONLY a JSON object with the numeric amount.
- Do NOT include currency symbols or commas in the number.
- For Indian number formatting (e.g., 1,00,000), convert to standard: 100000.

Return exactly this JSON format:
{{"amount": <number>}}
"""
    
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": __import__("base64").b64encode(image_bytes).decode(),
                        }
                    },
                ]
            }
        ],
    )
    
    # Parse the response
    text = response.text.strip()
    # Clean up markdown code blocks if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    
    try:
        result = json.loads(text)
        return float(result["amount"])
    except (json.JSONDecodeError, KeyError, ValueError):
        # Try to extract number from plain text
        import re
        numbers = re.findall(r"[\d]+\.?\d*", text.replace(",", ""))
        if numbers:
            return float(numbers[-1])  # Take the last number (usually the total)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Message Intelligence (LLM)
# ═══════════════════════════════════════════════════════════════════════════════

def parse_all_messages(data: DataStore) -> dict[str, list[MessageAdjustment]]:
    """
    Parse all messages and extract structured financial adjustments.
    
    Messages may be in English or Indonesian (Bahasa). The LLM handles
    both languages natively.
    
    Returns:
        dict mapping user_id -> list of MessageAdjustment objects
    """
    client = get_gemini_client()
    adjustments_by_user: dict[str, list[MessageAdjustment]] = {}
    
    print("\n[MSG] Parsing messages for financial signals...")
    
    # Process messages in batches per user to reduce API calls
    all_user_ids = sorted(data.messages_by_user.keys())
    
    for i, user_id in enumerate(all_user_ids):
        messages = data.messages_by_user[user_id]
        
        try:
            user_adjustments = _parse_user_messages(client, user_id, messages, data)
            if user_adjustments:
                adjustments_by_user[user_id] = user_adjustments
                for adj in user_adjustments:
                    print(f"  OK {user_id}: {adj.adjustment_type} — {adj.description[:60]}")
        except Exception as e:
            print(f"  FAIL {user_id} error: {e}")
        
        # Rate limiting — pause every 10 users
        if (i + 1) % 10 == 0:
            time.sleep(2)
    
    total = sum(len(v) for v in adjustments_by_user.values())
    print(f"\n[OK] Extracted {total} financial adjustments from messages")
    return adjustments_by_user


def _parse_user_messages(
    client, user_id: str, messages: list, data: DataStore
) -> list[MessageAdjustment]:
    """Parse messages for a single user and extract financial adjustments."""
    
    # Build message context
    msg_texts = []
    for msg in messages:
        source = msg.source_type
        req = f" (for {msg.request_id})" if msg.request_id else ""
        evt = f" (about {msg.related_event_id})" if msg.related_event_id else ""
        msg_texts.append(f"[{source}{req}{evt}] {msg.message_text}")
    
    messages_block = "\n\n".join(msg_texts)
    
    # Get user profile for context
    profile = data.profiles.get(user_id)
    currency = profile.home_currency if profile else "unknown"
    
    prompt = f"""Analyze these financial messages for user {user_id} (currency: {currency}).
Extract ALL actionable financial adjustments. Messages may be in English or Indonesian.

Messages:
{messages_block}

For EACH adjustment found, return a JSON object with:
- "adjustment_type": one of:
  - "salary_change" — salary amount changed (increase or decrease)
  - "salary_confirmed" — next salary date/amount confirmed  
  - "income_end" — employment or contract ended, no more income
  - "new_income" — new income source confirmed (first salary)
  - "payment_delay" — payment date has been delayed/changed
  - "refund_pending" — refund initiated but NOT yet in account (don't count as cash)
  - "refund_completed" — refund has been credited to account
  - "new_deduction" — new recurring deduction (childcare, rent increase, etc.)
  - "rent_increase" — rent has increased by a percentage or fixed amount
  - "bonus_unconfirmed" — bonus mentioned but NOT yet confirmed/approved
  - "prize_credited" — prize/lottery winnings credited to account
  - "prize_pending" — prize claimed but NOT yet credited
  - "income_pending" — income/payout is pending, NOT yet withdrawable
  - "internal_transfer" — transfer between own accounts (not real income/expense)
  - "investment_unrealized" — portfolio value changed but no cash generated
- "amount": numeric amount if mentioned (null if not)
- "effective_date": "YYYY-MM-DD" if mentioned (null if not)
- "description": brief summary of what changed
- "confidence": 0.0 to 1.0 how certain this adjustment is

CRITICAL RULES:
- "refund_pending" means money is NOT yet available — do NOT count it as balance.
- "income_pending" / "prize_pending" means money is NOT yet withdrawable.
- "bonus_unconfirmed" means the bonus is NOT guaranteed — do NOT rely on it.
- "investment_unrealized" means no actual cash — do NOT add to balance.
- "internal_transfer" between own accounts is NOT real income.
- Only "salary_confirmed", "salary_change", "new_income", "refund_completed", "prize_credited" represent REAL available money.

Return a JSON array. If no adjustments found, return [].
"""
    
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    
    text = response.text.strip()
    # Clean up markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    
    try:
        results = json.loads(text)
        if not isinstance(results, list):
            results = [results]
    except json.JSONDecodeError:
        return []
    
    adjustments = []
    for r in results:
        if not isinstance(r, dict):
            continue
        adj = MessageAdjustment(
            adjustment_type=r.get("adjustment_type", "unknown"),
            amount=parse_float(r.get("amount")),
            effective_date=parse_date(str(r.get("effective_date", ""))) if r.get("effective_date") else None,
            description=r.get("description", ""),
            confidence=float(r.get("confidence", 0.5)),
        )
        adjustments.append(adj)
    
    return adjustments
