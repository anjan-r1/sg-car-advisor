# app.py

import os
from datetime import timedelta

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
)
# top of app.py
from db_search import search_with_fallback

from dotenv import load_dotenv
import pandas as pd
import duckdb

# --- Load env, configure Flask -------------------------------------------------

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.permanent_session_lifetime = timedelta(minutes=60)

# --- Project imports -----------------------------------------------------------

# LLM that asks the NEXT QUESTION
from question_llm import run_question_llm as get_next_question

# Build user_profile from Q&A history
from profile_llm import build_profile_from_history

# Turn user_profile into numeric filters (budget, years, mileage, owners, etc.)
from filters import build_filters_from_profile

# Query DuckDB car_listings table
from db_search import search_cars_in_duckdb

# Compute value_score for each listing
from value_model import compute_value_scores

# Generate natural-language explanation for recommendations
from llm_summary import summarize_recommendations


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Landing page – show a start button."""
    # reset session for a fresh run
    session.clear()
    return render_template("index.html")


MAX_QUESTIONS = 5  # we cap at 5 questions even if LLM wants more


@app.route("/questions", methods=["GET", "POST"])
def questions():
    """
    Interactive Q&A flow.
    - Stores history in session["qa_history"]
    - When finished, builds profile + redirects to /recommendations
    """
    history = session.get("qa_history", [])
    q_index = session.get("q_index", 0)

    if request.method == "POST":
        # Save previous Q&A
        answer = request.form.get("answer", "").strip()
        prev_q = request.form.get("question_text", "").strip()

        if prev_q and answer:
            history.append({"question": prev_q, "answer": answer})
            session["qa_history"] = history
            q_index += 1
            session["q_index"] = q_index

    # --- Stop conditions -------------------------------------------------------

    # 1) Hard cap by number of questions
    if q_index >= MAX_QUESTIONS:
        profile = build_profile_from_history(history)
        session["user_profile"] = profile
        return redirect(url_for("recommendations"))

    # 2) Ask LLM for the NEXT question
    next_q = get_next_question(history)

    # If LLM says DONE or gives empty output -> stop asking more
    if not next_q or next_q.strip().upper() == "DONE":
        profile = build_profile_from_history(history)
        session["user_profile"] = profile
        return redirect(url_for("recommendations"))

    # Keep question in session (for display + POST round-trip)
    session["current_question"] = next_q

    return render_template(
        "questions.html",
        question=next_q,
        question_index=q_index + 1,
        total_questions=MAX_QUESTIONS,
        history=history,
    )


@app.route("/recommendations")
def recommendations():
    """
    Uses:
    - session["user_profile"] built from the Q&A
    - filters.build_filters_from_profile(profile)
    - db_search.search_cars_in_duckdb(filters)
    - value_model.compute_value_scores(df)
    - llm_summary.summarize_recommendations(history, df_top_n)

    Renders: templates/recommendations.html
    """
    history = session.get("qa_history", [])
    profile = session.get("user_profile")

    if profile is None:
        # If user jumps here directly, build profile on the fly
        profile = build_profile_from_history(history)
        session["user_profile"] = profile

    # Build numeric / categorical filters from profile
    car_filters = build_filters_from_profile(profile)
    print("[PROFILE] ", profile)
    print("[FILTERS] ", car_filters)

    # Query DuckDB for matching cars
    df_raw = search_with_fallback(car_filters, limit=80)
    if df_raw is None or df_raw.empty:
        return render_template(
            "recommendations.html",
            profile=profile,
            filters=car_filters,
            explanation="No cars matched your preferences in the local dataset.",
            cars=[],
        )

    # Compute value scores and rank
    df_scored = compute_value_scores(df_raw)
    df_scored = df_scored.sort_values("value_score", ascending=False).reset_index(drop=True)

    # Use top 10 for explanation and display
    top_cars = df_scored.head(10).copy()

    # LLM summary (one big block at the top)
    explanation = summarize_recommendations(history, top_cars)

    # Convert to list of dicts for Jinja
    cars_list = top_cars.to_dict(orient="records")

    return render_template(
        "recommendations.html",
        profile=profile,
        filters=car_filters,
        explanation=explanation,
        cars=cars_list,
    )


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
