# llm.py
import os
import json
import re
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ---------- Shared helpers ----------

def format_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "None yet."
    lines = []
    for i, qa in enumerate(history, start=1):
        lines.append(f"Q{i}: {qa.get('question','')}\nA{i}: {qa.get('answer','')}")
    return "\n".join(lines)


# ---------- Part 1: Question flow (unchanged) ----------

QNA_SYSTEM_PROMPT = """
You are a car-purchase advisor helping a user choose the best car for their needs in Singapore.

You will ask at most MAX_QUESTIONS questions, one by one.
Each time you receive conversation_history (a list of previous question-answer pairs),
you must decide what to do next.

Your job:
- If the number of Q&A pairs so far is less than MAX_QUESTIONS,
  propose the *next* most useful question to learn about the user's needs
  (budget, main usage, family size, driving pattern, running cost sensitivity,
   new vs used, brand preference, body type, etc.).
- If the number of Q&A pairs is already MAX_QUESTIONS or more,
  you MUST treat the conversation as complete:
  - set "done": true
  - "next_question": null
  - provide a friendly "summary" of what you learned about the user
    and what kind of car would suit them (segment, rough budget band, key traits).

You MUST respond as a single JSON object, with this exact structure:

{
  "done": false,
  "next_question": "string or null",
  "summary": "string"
}

Rules:
- When done is false:
    - next_question MUST be a short, clear, single question.
    - summary MUST be an empty string "".
- When done is true:
    - next_question MUST be null.
    - summary MUST be a short 1–3 paragraph explanation.
- Do NOT include any extra keys.
- Do NOT output anything before or after the JSON.
"""


def get_next_turn(history: List[Dict[str, str]], max_questions: int = 5) -> Dict[str, Any]:
    """
    Call Groq / Llama3.1 to get either the next question or a final summary.

    HARD CAP: if len(history) >= max_questions, we *force* done = True on our side,
    even if the model tries to ask more.
    """
    hard_cap_reached = len(history) >= max_questions

    # Fallback if no Groq client
    if client is None:
        if hard_cap_reached:
            return {
                "done": True,
                "next_question": None,
                "summary": "LLM is not configured, but based on your answers we would summarise your needs here."
            }
        else:
            return {
                "done": False,
                "next_question": "What is your approximate car budget in SGD?",
                "summary": ""
            }

    history_text = format_history(history)

    if hard_cap_reached:
        user_prompt = f"""
MAX_QUESTIONS = {max_questions}

Conversation history so far:
{history_text}

The number of Q&A pairs is already {len(history)}, which is >= MAX_QUESTIONS.
You MUST now treat the conversation as complete and ONLY return a JSON with:
  - "done": true
  - "next_question": null
  - "summary": a short explanation of the user's needs and what kind of car suits them.
"""
    else:
        user_prompt = f"""
MAX_QUESTIONS = {max_questions}

Conversation history so far:
{history_text}
"""

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": QNA_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=400,
    )

    raw_content = completion.choices[0].message.content

    try:
        result = json.loads(raw_content)
    except json.JSONDecodeError:
        return {
            "done": True,
            "next_question": None,
            "summary": "Sorry, I had trouble generating the next step, "
                       "but based on your answers you likely need a practical, family-friendly car."
        }

    result.setdefault("done", True)
    result.setdefault("next_question", None)
    result.setdefault("summary", "")

    if hard_cap_reached:
        result["done"] = True
        result["next_question"] = None
        if not result.get("summary"):
            result["summary"] = "Based on your answers, you need a car that balances budget, usage and comfort."

    return result


# ---------- Part 2: Rule-based inference for search ----------

def _all_answers_text(history: List[Dict[str, str]]) -> str:
    return " ".join(qa.get("answer", "") for qa in history)


def infer_budget_band(history: List[Dict[str, str]]) -> (Optional[int], Optional[int]):
    """
    Infer budget_min and budget_max in SGD from free-text answers.
    Handles "100k", "80-120k", "80 to 120k", "100,000", etc.
    If one number is given, use ±20% band.
    """
    text = _all_answers_text(history).lower()

    def to_int(num_str: str, is_k: bool = False) -> int:
        num_str = num_str.replace(",", "").strip()
        n = int(num_str)
        return n * 1000 if is_k else n

    # range with k: "80-120k" or "80 to 120k"
    m = re.search(r'(\d{2,3})\s*(?:-|to)\s*(\d{2,3})\s*k', text)
    if m:
        a, b = to_int(m.group(1), True), to_int(m.group(2), True)
        return (min(a, b), max(a, b))

    # range full numbers: "80000-120000" or "80,000 to 120,000"
    m = re.search(r'\$?\s*([\d,]{4,7})\s*(?:-|to)\s*\$?\s*([\d,]{4,7})', text)
    if m:
        a, b = to_int(m.group(1)), to_int(m.group(2))
        return (min(a, b), max(a, b))

    # single with k: "100k"
    m = re.search(r'(\d{2,3})\s*k\b', text)
    if m:
        center = to_int(m.group(1), True)
    else:
        # first 5–7 digit number: "100000" or "120,000"
        m = re.search(r'\$?\s*([\d,]{5,7})', text)
        if m:
            center = to_int(m.group(1))
        else:
            return (None, None)

    # ±20% band
    min_b = int(center * 0.8)
    max_b = int(center * 1.2)
    return (min_b, max_b)


def infer_family_size(history: List[Dict[str, str]]) -> Optional[int]:
    """
    Look for the answer to a 'how many people / family members travel' type question
    and extract the first integer.
    """
    for qa in history:
        q = qa.get("question", "").lower()
        a = qa.get("answer", "").lower()
        if any(word in q for word in ["family", "members", "people", "usually travel", "passengers"]):
            m = re.search(r'\b(\d+)\b', a)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    continue
    # fallback: any stray integer in all answers
    text = _all_answers_text(history).lower()
    m = re.search(r'\b(\d+)\b', text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def infer_condition(history: List[Dict[str, str]]) -> str:
    """
    'used', 'new' or 'both' based on answers (used car, second hand, brand new etc.).
    """
    text = _all_answers_text(history).lower()
    if any(w in text for w in ["used car", "second hand", "pre-owned", "preowned"]):
        return "used"
    if any(w in text for w in ["brand new", "new car", "showroom"]):
        return "new"
    return "both"


def build_search_query(history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Turn Q&A history into:
      - search_query: string suitable for web search
      - budget_min / budget_max in SGD
      - car_condition: "used" | "new" | "both"

    This is rule-based so it's deterministic and uses your answers
    (budget, family size, used/new).
    """
    if not history:
        return {
            "search_query": "used car Singapore site:sgcarmart.com",
            "budget_min": None,
            "budget_max": None,
            "car_condition": "both",
        }

    budget_min, budget_max = infer_budget_band(history)
    family_size = infer_family_size(history)
    condition = infer_condition(history)

    # Body type suggestion based on family size
    if family_size is None:
        body_phrase = "car"
    elif family_size <= 2:
        body_phrase = "small hatchback or compact car"
    elif family_size <= 4:
        # what you mentioned: 4 pax -> hatchback or sedan
        body_phrase = "hatchback or sedan"
    else:
        body_phrase = "MPV or 7-seater SUV"

    # Condition text for query
    if condition == "used":
        cond_phrase = "used"
    elif condition == "new":
        cond_phrase = "new"
    else:
        cond_phrase = ""  # both – let search be flexible

    parts = []
    if cond_phrase:
        parts.append(cond_phrase)
    parts.append(body_phrase)
    parts.append("Singapore")

    # Add budget hint if we have it
    if budget_min is not None and budget_max is not None:
        parts.append(f"${budget_min} to ${budget_max} budget")

    # Force SGCarMart focus
    parts.append("site:sgcarmart.com")

    search_query = " ".join(parts)

    print("[SEARCH_BUILDER] family_size:", family_size)
    print("[SEARCH_BUILDER] budget_min:", budget_min, "budget_max:", budget_max)
    print("[SEARCH_BUILDER] condition:", condition)
    print("[SEARCH_BUILDER] search_query:", search_query)

    return {
        "search_query": search_query,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "car_condition": condition,
    }

# ---------- Part 3: Generic LLM wrapper for summaries / explanations ----------

def run_llm(prompt: str) -> str:
    """
    A generic helper used by summarisation & recommendation modules.
    """
    if client is None:
        return (
            "LLM is not configured (GROQ_API_KEY missing), "
            "so here is a simple placeholder recommendation."
        )

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful SG car-buying advisor."
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=600,
    )

    text = completion.choices[0].message.content
    return text.strip() if text else ""