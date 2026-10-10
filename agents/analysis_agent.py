"""Announcement Analysis Agent (Member 1 module).

Extracts event facts, evidence status, and unknowns from corporate event announcements.
"""

from __future__ import annotations

import re
import uuid
from typing import Any
from schemas import CateringSignal, EvidenceFact, LeadAnalysis, LeadInput


def analyze_announcement(payload: LeadInput | dict | str) -> LeadAnalysis:
    """Analyze announcement text and extract structured event facts."""
    if isinstance(payload, str):
        lead_input = LeadInput(announcement_text=payload)
    elif isinstance(payload, dict):
        lead_input = LeadInput(**payload)
    elif isinstance(payload, LeadInput):
        lead_input = payload
    else:
        raise ValueError(f"Unsupported payload type: {type(payload)}")

    text = lead_input.announcement_text or ""
    lead_id = lead_input.lead_id or f"LEAD-{uuid.uuid4().hex[:6].upper()}"

    # Extract company name
    company_name = lead_input.company_name
    if not company_name:
        company_match = re.search(r"(?:update|notice|announcement)?:\s*([A-Za-z0-9\s&]+?)\s+(?:is planning|announced|is hosting|plans|scheduled)", text, re.I)
        if company_match:
            company_name = company_match.group(1).strip()
        else:
            # Fallback extraction
            first_words = re.findall(r"\b[A-Z][a-zA-Z0-9&]+(?:\s+[A-Z][a-zA-Z0-9&]+)*\b", text)
            company_name = first_words[0] if first_words else "Unknown Organization"

    # Extract event type
    event_type = None
    event_type_match = re.search(
        r"(?:planning a|announced a|hosting a|organizing a)\s+(?:\d+(?:\.0)?(?:-|\s+)(?:person|guest|attendee|delegate)\s+)?([A-Za-z\s]+?)\s+(?:in|scheduled for|for|on)",
        text,
        re.I,
    )
    if event_type_match:
        event_type = event_type_match.group(1).strip().title()
    else:
        common_types = [
            "Technology Conference", "Annual Conference", "Technology Summit",
            "Corporate Training", "Team Workshop", "Dealer Convention", "Seminar", "Conference"
        ]
        for ctype in common_types:
            if re.search(rf"\b{re.escape(ctype)}\b", text, re.I):
                event_type = ctype
                break

    # Extract event date (YYYY-MM-DD)
    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    event_date = date_match.group(1) if date_match else None

    # Extract location (City, State, Country)
    location_match = re.search(r"\bin\s+([A-Za-z\s]+?,\s*[A-Za-z\s]+?,\s*India|[A-Za-z\s]+?,\s*India|[A-Za-z\s]+?\s+for\s+\d{4})", text, re.I)
    event_location = None
    if location_match:
        loc = location_match.group(1)
        loc = re.sub(r"\s+for\s+\d{4}.*$", "", loc).strip()
        event_location = loc
    else:
        cities = ["Bengaluru", "Mumbai", "Pune", "Goa", "Delhi", "Hyderabad", "Chennai", "Kolkata", "Srinagar"]
        for city in cities:
            if re.search(rf"\b{re.escape(city)}\b", text, re.I):
                event_location = f"{city}, India"
                break

    # Extract attendee count (e.g. 250-person, 200 guests, 150 attendees)
    attendee_count = None
    attendee_match = re.search(
        r"\b(\d+)(?:\.0)?\s*(?:-\s*)?(?:attendees?|guests?|people|delegates?|persons?|participants?|headcount|pax)\b",
        text,
        re.I,
    )
    if attendee_match:
        attendee_count = float(attendee_match.group(1))

    # Extract duration
    duration_match = re.search(r"(\d+)\s*-?\s*day", text, re.I)
    event_duration_days = int(duration_match.group(1)) if duration_match else 1

    # Catering signal evaluation
    catering_signal = CateringSignal.UNKNOWN.value
    if re.search(r"\b(?:requests? quotations?|lunch and|refreshments|food service|catering requirements?)\b", text, re.I):
        if "not specified" in text.lower() or "not mentioned" in text.lower() or "not published" in text.lower():
            catering_signal = CateringSignal.INFERRED.value
        else:
            catering_signal = CateringSignal.EXPLICIT.value
    elif re.search(r"\b(?:networking reception|full-day agenda|large in-person gathering|conference)\b", text, re.I):
        catering_signal = CateringSignal.INFERRED.value

    # Build evidence facts and unknowns
    evidence_facts: list[EvidenceFact] = []
    unknown_fields: list[str] = []
    inferred_fields: list[str] = []

    if company_name:
        evidence_facts.append(EvidenceFact(field_name="company_name", value=company_name, status="explicit"))
    if event_type:
        evidence_facts.append(EvidenceFact(field_name="event_type", value=event_type, status="explicit"))
    else:
        unknown_fields.append("event_type")

    if event_date:
        evidence_facts.append(EvidenceFact(field_name="event_date", value=event_date, status="explicit"))
    else:
        unknown_fields.append("event_date")

    if event_location:
        evidence_facts.append(EvidenceFact(field_name="event_location", value=event_location, status="explicit"))
    else:
        unknown_fields.append("event_location")

    if attendee_count is not None:
        evidence_facts.append(EvidenceFact(field_name="attendee_count", value=attendee_count, status="explicit"))
    else:
        unknown_fields.append("attendee_count")

    if catering_signal == CateringSignal.INFERRED.value:
        inferred_fields.append("catering_requirement")
    elif catering_signal == CateringSignal.UNKNOWN.value:
        unknown_fields.append("catering_requirement")

    return LeadAnalysis(
        lead_id=lead_id,
        company_name=company_name or "Unknown Company",
        event_type=event_type,
        event_date=event_date,
        event_location=event_location,
        attendee_count=attendee_count,
        event_duration_days=event_duration_days,
        catering_signal=catering_signal,
        source_url=lead_input.source_url,
        announcement_text=text,
        evidence_facts=evidence_facts,
        extracted_facts={"company_name": company_name, "event_type": event_type, "event_date": event_date},
        unknown_fields=unknown_fields,
        inferred_fields=inferred_fields,
    )
