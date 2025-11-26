# question_llm.py
"""
LLM helper dedicated ONLY to generating the NEXT QUESTION in the Q&A flow.

This is intentionally separate from llm.run_llm(history, top_rows_markdown)
which is used for explaining recommendations.
"""

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

_client = Groq(api_key=GROQ_API_KEY)


def _history_to_text(history):
    """
    history: list of {"question": ..., "answer": ...}
    """
    if not history:
        return "(no previous questions asked yet)"

    lines = []
    for idx, qa in enumerate(history, start=1):
        q = qa.get("question", "").strip()
        a = qa.get("answer", "").strip()
        if q or a:
            lines.append(f"Q{idx}: {q}\nA{idx}: {a}\n")
    return "\n".join(lines)


def run_question_llm(history):
    """
    Call Groq LLaMA to get ONE next question.

    Returns:
        - a string with the next question, or
        - the literal string "DONE" if no more questions are needed.
    """
    convo_text = _history_to_text(history)

    prompt = f"""
You are a helpful car-purchase advisor in Singapore.

You are running an interview-style Q&A to understand the user's needs
before recommending a car (new or used). You must decide the NEXT single
question to ask the user.

Conversation so far:
{convo_text}

Guidelines:
- Ask exactly ONE concise question.
- Focus on practical factors: budget, family size, main usage, comfort,
  safety, fuel / EV preference, running cost, risk tolerance, parking, etc.
- Avoid repeating the same information.
- Do NOT ask technical filters like exact mileage, number of owners,
  engine CC, unless it flows naturally.
- If the user has already answered enough (about 5–7 solid answers)
  to determine a car profile, respond with exactly: DONE

Output format:
- If you are asking another question: return ONLY the question text.
- If you are finished: return ONLY the word DONE.
"""

    resp = _client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You write only the next question or DONE."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )

    text = resp.choices[0].message.content.strip()
    return text
