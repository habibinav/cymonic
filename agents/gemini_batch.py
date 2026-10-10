"""gemini_batch.py — Gemini reasoning + proposal writing, many leads per request.

One Gemini call handles a whole batch of leads (default 8) and returns, for each lead:
a one-line headline, the reasoning, scores and a tailored draft. Several batches run in
parallel. The pipeline caches results in data/ai_cache.json.

The hard rules (service area, guest limits, notice period) are applied BEFORE this step by
Member 1's qualification agent; out-of-policy leads are never sent to Gemini.
Member 1's strategy agent still turns Gemini's scores into the pursuit tier, and Member 3's
validate_generated_content() still sanitises every draft.
"""
from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from gemini_client import generate_json

logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.getenv("GEMINI_BATCH_SIZE", "8"))
PARALLEL = int(os.getenv("GEMINI_PARALLEL", "6"))

SYSTEM_PROMPT = """You are the reasoning + proposal agent for "{caterer}", a corporate catering company in India.
You receive a JSON list of event leads. Each has the original announcement, extracted facts,
and rule-based qualification results (the leads already passed service-area / capacity / notice checks,
or are marked needs_research if key facts are missing).

For EACH lead:
1. Reason about it like an experienced sales lead: order size (guests x days x meals), whether food is
   explicit or only implied, repeat-business potential, client profile, timing, logistics, gaps.
   Be specific to that event — never reuse the same sentences across leads.
2. Score it:
   - commercial_potential_score 0-10: 7.5+ = high-value/strategic, worth a custom pitch;
     5-7.4 = solid standard deal; below 5 = small/uncertain, light email only.
   - operational_feasibility_score 0-10: how comfortably we can deliver it.
3. Pick the tier: if qualification status is "needs_research" -> "needs_research";
   else if commercial >= 7.5 and feasibility >= 6 -> "high_effort_pitch";
   else if commercial >= 5 -> "standard_proposal"; else -> "light_outreach".
4. Write the draft for that tier in Markdown, addressed to the client company:
   - high_effort_pitch: tailored executive pitch, 150-220 words, with short "##"/"###" sections
     (why this event matters, proposed catering approach for THIS event's format and schedule, what we need to confirm, next step).
   - standard_proposal: proposal outline, 100-160 words, short sections.
   - light_outreach: friendly exploratory email, 60-100 words, with a Subject line.
   - needs_research: INTERNAL checklist (not to the client) of 3-6 specific questions to verify.

Hard rules for drafts:
- Use ONLY the facts given. Never invent prices, rates, discounts, awards, testimonials, past
  relationships, contact names or headcounts.
- Only offer these capabilities: {capabilities}. Dietary options: {dietary}.
- Unknown details -> placeholders like [confirm guest count], [confirm event date],
  [confirm venue address and facilities], [to be confirmed after requirements are validated].
- Sign off as "{caterer}". Do not claim anything was sent.

Return ONLY JSON: {{"leads": [ {{
  "id": "<same id as input>",
  "headline": "max 12 words — the single most important insight about this lead",
  "summary": "2-3 sentence assessment",
  "positives": ["..."], "risks": ["..."], "uncertainties": ["..."],
  "commercial_potential_score": 0.0, "operational_feasibility_score": 0.0,
  "next_action": "one concrete next step",
  "tier": "high_effort_pitch | standard_proposal | light_outreach | needs_research",
  "draft": "markdown text"
}} ] }}
Return exactly one object per input lead, in any order."""


def _system(profile) -> str:
    return SYSTEM_PROMPT.format(
        caterer=profile.company_name,
        capabilities=", ".join(c.replace("_", " ") for c in profile.confirmed_capabilities) or "corporate catering",
        dietary=", ".join(d.replace("_", " ") for d in profile.dietary_options) or "standard",
    )


def _one_batch(items: list[dict], system: str) -> dict:
    data = generate_json(system, "Leads:\n" + json.dumps(items, ensure_ascii=False, default=str))
    out = {}
    for r in (data or {}).get("leads", []) or []:
        if isinstance(r, dict) and r.get("id") is not None and r.get("summary"):
            out[str(r["id"])] = r
    if data is None:
        logger.warning("Gemini batch of %d leads failed", len(items))
    return out


def analyze(items: list[dict], profile, progress=None) -> dict:
    """items: [{"id": ..., ...lead payload...}]. Returns {id: gemini_result} for the ones that worked.
    progress(done, total) is called as leads finish."""
    if not items:
        return {}
    system = _system(profile)
    batches = [items[i:i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    results, done = {}, 0
    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        futures = {pool.submit(_one_batch, b, system): b for b in batches}
        for fut in as_completed(futures):
            try:
                results.update(fut.result())
            except Exception as exc:
                logger.warning("Gemini batch crashed: %s", exc)
            done += len(futures[fut])
            if progress:
                progress(done, len(items))
    return results
