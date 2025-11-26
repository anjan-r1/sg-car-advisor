# llm_summary.py
"""
Use Groq (Llama) to summarise car recommendations
based on:
- the full Q&A history (user answers)
- the list of top cars (with value scores, year, mileage, etc.)

You can call `summarize_recommendations(qa_history, cars)`
from your Flask / Streamlit route after you have computed the top cars.
"""

import os
import pandas as pd
from llm import run_llm
import pandas as pd

from typing import List, Dict, Any

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
_groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def _format_qa_history(qa_history: List[Dict[str, str]]) -> str:
    """Pretty-print Q&A pairs for the prompt."""
    if not qa_history:
        return "No explicit Q&A were collected."

    lines = []
    for i, qa in enumerate(qa_history, start=1):
        q = qa.get("question", "").strip()
        a = qa.get("answer", "").strip()
        lines.append(f"{i}. Q: {q}\n   A: {a}")
    return "\n".join(lines)


import math

def _format_cars(df):
    parts = []

    for _, c in df.iterrows():
        make = c.get("make", "")
        model = c.get("model", "")
        price = c.get("price_sgd", "")
        mileage = c.get("mileage_km", "")
        year = c.get("year", "")
        dep = c.get("depreciation_per_year", 0)

        # Safe conversions
        price = f"${int(price):,}" if pd.notna(price) else "N/A"
        mileage = f"{int(mileage):,} km" if pd.notna(mileage) else "N/A"
        year = int(year) if pd.notna(year) else "N/A"
        dep = f"${int(dep):,}/yr" if pd.notna(dep) else "N/A"

        parts.append(
            f"- **{make} {model} ({year})** — Price: {price}, Mileage: {mileage}, Depreciation: {dep}"
        )

    return "\n".join(parts)



def summarize_recommendations(history, cars):
    import pandas as pd

    if cars is None or (isinstance(cars, pd.DataFrame) and cars.empty):
        return "No cars matched your preferences in the local dataset."

    # use the existing helper name
    history_text = _format_qa_history(history)
    cars_text = _format_cars(cars)

    prompt = f"""
    You are an SG car-buying assistant.

    The user shared the following preferences:
    {history_text}

    The following cars matched the user's needs:
    {cars_text}

    Please provide a concise recommendation summary highlighting:
    - Why these cars match the user's needs
    - Strengths of each car
    - Any important trade-offs
    - Final advice to help user choose
    """

    return run_llm(prompt)



# llm_summary.py
import json
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def explain_each_car(user_history, cars):
    """
    Returns a dict keyed by listing_url (or index) with a short AI note
    for each car.
    """
    if cars is None or cars.empty:
        return "No cars matched your preferences in the local dataset."


    # Build a compact description for each car
    car_items = []
    for idx, c in enumerate(cars, start=1):
        car_items.append({
            "id": idx,
            "title": c.get("title"),
            "price": c.get("price_sgd"),
            "mileage": c.get("mileage_km"),
            "year": c.get("year"),
            "value_score": c.get("value_score"),
        })

    prompt = f"""
You are a Singapore car consultant.

User profile and needs:
{user_history}

Here is a list of candidate cars (as JSON):
{json.dumps(car_items, default=str)}

For EACH car, write a SHORT explanation (2–3 sentences) that MUST:
- Explicitly mention which user inputs you are using (e.g. budget, family size, daily commute, EV preference, low running cost, risk tolerance).
- Say why the car is a good or bad fit for THIS user, using those inputs.
- Mention key pros/cons: price vs budget, mileage vs age, fuel type (EV/hybrid/petrol), and owners if relevant.
- Provide justification of the value score given

Return ONLY JSON in this format:

{{
  "cars": [
    {{
      "id": 1,
      "summary": "short explanation here"
    }},
    {{
      "id": 2,
      "summary": "short explanation here"
    }}
  ]
}}
"""

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    content = resp.choices[0].message.content.strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {}

    mapping = {}
    for item in data.get("cars", []):
        cid = item.get("id")
        summary = item.get("summary")
        if cid is not None and summary:
            mapping[cid] = summary

    return mapping
