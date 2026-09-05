"""
Tags an email using a small local model served by Ollama.

Setup (one-time):
1. Install Ollama: https://ollama.com/download
2. Pull a small model, e.g.:  ollama pull llama3.2:1b
   (qwen2.5:0.5b is even smaller/faster if you want to push the "tiny model" story)
3. Make sure `ollama serve` is running (it usually auto-starts after install)
"""

import json
import re

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"

# Fixed taxonomy -- this is the single biggest lever for small-model accuracy.
# Each tag has a one-line description so the model isn't guessing what the name means
# from the word alone (e.g. "Work" without context can look like it matches anything
# vaguely professional, like an online-course ad).
# Tuned for a personal inbox rather than a business/support inbox.
TAGS = {
    "Work": "Direct correspondence FROM your actual job, colleagues, or clients -- someone specifically emailing you about work you do. NOT tech/industry newsletters, developer blogs, or professional content mailing lists, even if the topic is software/business-related -- those go in Newsletter/Subscription instead.",
    "Finance/Banking": "Bank alerts, bills, statements, invoices, payment confirmations, receipts for actual purchases.",
    "Shopping/Orders": "Order confirmations, shipping/delivery updates for something you bought.",
    "Social/Notifications": "Automated notifications from social media, apps, or platforms (likes, comments, sign-in alerts).",
    "Newsletter/Subscription": "Recurring content you signed up to receive -- blogs, digests, mailing lists, 'weekly' round-ups, personal writing from someone you follow. If it reads like a published post rather than a message written specifically to you, it belongs here, even if the topic is work/tech-related.",
    "Personal": "Direct correspondence from a specific person you know (friend, family) written to you individually, not a mass mailing.",
    "Travel": "Bookings, itineraries, boarding passes, reservation confirmations.",
    "Urgent": "Needs action or a response soon. Can be combined with any other tag.",
    "Promotional/Spam": "Marketing, ads, discount offers, product recommendations, or anything trying to sell you something you didn't specifically ask about.",
    "Other": "Doesn't clearly fit any tag above.",
}

PROMPT_TEMPLATE = """You are an email tagging assistant. Assign one or more tags to the email below from this fixed list ONLY:
{tags}

Rules:
- Only use tags from the list above, exact spelling.
- An email can have more than one tag (e.g. both "Urgent" and "Finance/Banking").
- Read each tag's description carefully -- some tags look similar but mean different things
  (e.g. "Work" means correspondence FROM your job, not an ad ABOUT work topics like courses).
- If nothing fits well, use "Other".
- Respond with ONLY a JSON object, no other text, in this exact format:
{{"tags": ["Tag1", "Tag2"]}}

Email subject: {subject}
Email from: {sender}
Email body:
{body}

JSON response:"""


def _tag_list_for_prompt() -> str:
    return "\n".join(f"- {tag}: {desc}" for tag, desc in TAGS.items())


def _extract_json(text: str) -> dict:
    """Small models often wrap JSON in extra text/markdown fences, or -- for thinking-mode
    models -- a whole reasoning block before the answer. Strip that first, then pull out
    the JSON object."""
    # Drop everything up to and including a </think> close tag, if present. Thinking-mode
    # models put their real answer after this point; searching the whole blob risks matching
    # stray braces the reasoning prose happens to contain.
    if "</think>" in text:
        text = text.split("</think>", 1)[1]

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"tags": ["Other"], "parsed_ok": False}
    try:
        parsed = json.loads(match.group(0))
        if "tags" in parsed and isinstance(parsed["tags"], list):
            # keep only tags that are actually in our taxonomy
            valid = [t for t in parsed["tags"] if t in TAGS]
            return {"tags": valid or ["Other"], "parsed_ok": True}
    except json.JSONDecodeError:
        pass
    return {"tags": ["Other"], "parsed_ok": False}


def tag_email(subject: str, sender: str, body: str) -> dict:
    """Returns {"tags": [...], "parsed_ok": bool, "raw_response": str}.

    parsed_ok=False means the model's output couldn't be parsed as valid JSON --
    the "Other" tag in that case is a parsing failure, not a real model decision.
    raw_response is included so a debug view can show exactly what the model said.
    """
    # Tagging only needs enough text to get the gist -- shorter input = faster inference.
    prompt = PROMPT_TEMPLATE.format(
        tags=_tag_list_for_prompt(), subject=subject, sender=sender, body=body[:400]
    )

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",  # keep the model loaded in memory between calls
            "options": {
                "temperature": 0,
                "num_predict": -1,  # qwen2.5:3b doesn't have a reasoning phase to worry about --
                                      # plenty of headroom for the JSON without risking a runaway response
            },
        },
        timeout=3000,
    )
    response.raise_for_status()
    raw_text = response.json().get("response", "")
    result = _extract_json(raw_text)
    result["raw_response"] = raw_text
    return result