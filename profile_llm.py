# profile_llm.py
"""
Convert Q&A history into a structured 'user_profile' dictionary.
This profile is later turned into numeric filters for database search.
"""

def _get_answer(history, keywords):
    """
    Extract an answer that matches any keyword.
    keywords: list of lowercase terms to look for in question text.
    Returns the matching answer or None.
    """
    for qa in history:
        q = qa.get("question", "").lower()
        a = qa.get("answer", "")
        if any(k in q for k in keywords):
            return a.strip()
    return None


def build_profile_from_history(history):
    """
    Convert user's raw Q&A into a structured profile dict.
    If some fields are not explicitly answered, we make reasonable defaults.

    Returns a dict:
    {
        "budget_sgd": ...,
        "family_size": ...,
        "usage": ...,
        "age_preference": ...,
        "running_cost_priority": ...,
        "owner_tolerance": ...,
        "mileage_tolerance": ...,
        "body_type_pref": ...,
        "brand_bias": ...,
        "fuel_pref": ...,
        "risk_tolerance": ...,
        "notes": ...
    }
    """

    # --- Budget -------------------------------------------------------------
    budget_answer = _get_answer(history, ["budget", "afford", "spend"])
    budget_sgd = None
    if budget_answer:
        import re
        nums = re.findall(r"\d+", budget_answer.replace(",", ""))
        if nums:
            budget_sgd = int(nums[-1])  # take largest number as user's budget

    if budget_sgd is None:
        budget_sgd = 100000  # default guess

    # --- Family size --------------------------------------------------------
    family_ans = _get_answer(history, ["family", "passenger", "people"])
    family_size = None
    if family_ans:
        import re
        nums = re.findall(r"\d+", family_ans)
        if nums:
            family_size = int(nums[0])
    if family_size is None:
        family_size = 1

    # --- Usage ---------------------------------------------------------------
    usage = _get_answer(history, ["usage", "drive", "commute", "purpose"])
    if not usage:
        usage = "general"

    # --- Age preference ------------------------------------------------------
    age_pref = _get_answer(history, ["age", "old", "new"])
    if not age_pref:
        age_pref = "balanced"

    # --- Running cost priority ----------------------------------------------
    run_cost = _get_answer(history, ["cost", "running", "depreciation"])
    if not run_cost:
        run_cost = "medium"

    # --- Owner tolerance -----------------------------------------------------
    owner_tol = _get_answer(history, ["owner", "owners"])
    if not owner_tol:
        owner_tol = "medium"

    # --- Mileage tolerance ---------------------------------------------------
    mileage_tol = _get_answer(history, ["mileage", "km"])
    if not mileage_tol:
        mileage_tol = "medium"

    # --- Body type preference ------------------------------------------------
    body_pref = _get_answer(history, ["body", "type", "hatch", "sedan", "suv", "mpv"])
    if not body_pref:
        # infer from family size
        if family_size >= 4:
            body_pref = "suv_or_mpv"
        else:
            body_pref = "sedan_or_hatchback"

    # --- Brand bias ----------------------------------------------------------
    brand_bias = _get_answer(history, ["brand", "maker", "make"])
    if not brand_bias:
        brand_bias = "none"

    # --- Fuel preference -----------------------------------------------------
    fuel_pref = _get_answer(history, ["fuel", "ev", "electric", "hybrid"])
    if not fuel_pref:
        fuel_pref = "any"

    # --- Risk tolerance ------------------------------------------------------
    risk_tol = _get_answer(history, ["risk", "safety"])
    if not risk_tol:
        risk_tol = "medium"

    # --- Notes (free text) ---------------------------------------------------
    notes = " | ".join([f"Q: {qa['question']} / A: {qa['answer']}" for qa in history])

    profile = {
        "budget_sgd": budget_sgd,
        "family_size": family_size,
        "usage": usage,
        "age_preference": age_pref,
        "running_cost_priority": run_cost,
        "owner_tolerance": owner_tol,
        "mileage_tolerance": mileage_tol,
        "body_type_pref": body_pref,
        "brand_bias": brand_bias,
        "fuel_pref": fuel_pref,
        "risk_tolerance": risk_tol,
        "notes": notes,
    }

    return profile
