# filters.py
"""
Convert a structured user profile (from profile_llm.build_user_profile)
into numeric / categorical filters that match SGCarMart's used-car listing
parameters.

This does NOT build the URL itself. It only returns a `filters` dict like:

{
  "brand": "toyota",
  "min_price": 80000,
  "max_price": 120000,
  "min_year": 2018,
  "max_year": 2025,
  "min_mileage": 0,
  "max_mileage": 150000,
  "max_owners": 2,
  "engine_cc_category": 2,
  "body_type_code": 4,
  "min_depreciation": None,
  "max_depreciation": None,
}

A separate url_builder will convert this into the SGCarMart query string.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


CURRENT_YEAR = datetime.now().year


@dataclass
class CarFilters:
    brand: str = ""                 # maps to q=
    min_price: Optional[int] = None # pr1
    max_price: Optional[int] = None # pr2
    min_year: Optional[int] = None  # fr
    max_year: Optional[int] = None  # to
    min_mileage: Optional[int] = None  # mil1
    max_mileage: Optional[int] = None  # mil2
    max_owners: Optional[int] = None   # own (with own_c = "<")
    engine_cc_category: Optional[int] = None  # eng (1..5)
    body_type_code: int = 15         # veh (1=hatchback,4=sedan,5=suv,9=mpv,15=all)
    min_depreciation: Optional[int] = None  # dp1
    max_depreciation: Optional[int] = None  # dp2


def _derive_price_band(budget_sgd: Optional[int]) -> (Optional[int], Optional[int]):
    """
    Given a rough budget (e.g. 100000), create a price band around it.
    For now we use ±20%.
    """
    if not budget_sgd or budget_sgd <= 0:
        return None, None

    min_p = int(budget_sgd * 0.8)
    max_p = int(budget_sgd * 1.2)
    return min_p, max_p


def _derive_year_range(age_pref: str) -> (Optional[int], Optional[int]):
    """
    Map age_preference into a year range.
    - "latest_tech"     → last 6 years
    - "balanced"        → last 10 years
    - "value_for_money" → last 15 years
    """
    max_year = CURRENT_YEAR
    age_pref = (age_pref or "").lower()

    if age_pref == "latest_tech":
        min_year = CURRENT_YEAR - 6
    elif age_pref == "value_for_money":
        min_year = CURRENT_YEAR - 15
    else:  # balanced / default
        min_year = CURRENT_YEAR - 10

    # Don't go below 2000 to avoid very old odd cases
    if min_year < 2000:
        min_year = 2000

    return min_year, max_year


def _derive_mileage_limit(mileage_tolerance: str) -> (Optional[int], Optional[int]):
    """
    Map mileage tolerance into max mileage.
    - "low"    → up to 120,000 km
    - "medium" → up to 160,000 km
    - "high"   → up to 220,000 km
    """
    mt = (mileage_tolerance or "").lower()
    if mt == "low":
        return 0, 120_000
    elif mt == "high":
        return 0, 220_000
    else:  # medium / default
        return 0, 160_000


def _derive_owner_limit(owner_tolerance: str) -> Optional[int]:
    """
    Map owner_tolerance into max number of previous owners.
    """
    ot = (owner_tolerance or "").lower()
    if ot == "low":
        return 2
    elif ot == "high":
        return 4
    else:  # medium / default
        return 3


def _derive_engine_category(running_cost_priority: str) -> Optional[int]:
    """
    Very rough mapping of running-cost concern into engine category:
    1 = <1000cc, 2 = 1001–1600cc, 3 = 1601–2000cc, 4 = 2001–3000cc, 5 = >3000cc
    """
    rcp = (running_cost_priority or "").lower()
    if rcp == "high":
        return 2          # aim for ≤1600cc
    elif rcp == "low":
        return None       # open to anything
    else:                 # medium
        return 3          # up to 2000cc


def _derive_body_type_code(body_type_pref: str, family_size: Optional[int]) -> int:
    """
    Map body_type_pref into SGCarMart veh code.
    If unclear, use family_size as a hint.
    """
    pref = (body_type_pref or "").lower()
    if pref == "small":
        return 1   # hatchback
    if pref == "suv":
        return 5
    if pref in ("mpv_7_seater", "mpv", "7-seater"):
        return 9
    if pref == "sedan_or_hatchback":
        return 4   # sedan as a decent middle-ground

    # fallback based on family size
    if family_size is not None:
        if family_size <= 2:
            return 1
        elif family_size <= 4:
            return 4
        else:
            return 9

    # generic: all body types
    return 15


def profile_to_filters(profile: Dict[str, Any], brand: Optional[str] = None) -> CarFilters:
    """
    Convert a structured user profile into CarFilters.

    `brand` can be passed explicitly from a separate user input
    (e.g. “Preferred brand” field in your form). If omitted,
    we will leave it empty and leave SGCarMart free to match multiple brands.
    """
    budget = profile.get("budget_sgd")
    family_size = profile.get("family_size")
    age_pref = profile.get("age_preference") or "balanced"
    running_cost_priority = profile.get("running_cost_priority") or "medium"
    owner_tol = profile.get("owner_tolerance") or "medium"
    mileage_tol = profile.get("mileage_tolerance") or "medium"
    body_pref = profile.get("body_type_pref") or "sedan_or_hatchback"

    # If brand is not explicitly provided, we could try a very light inference
    # from profile["brand_bias"], but to avoid hallucinating brand names,
    # we keep brand="" by default.
    brand_bias = (profile.get("brand_bias") or "").lower()
    if not brand and any(x in brand_bias for x in ["toyota", "honda", "mazda"]):
        brand = "toyota"  # you can refine this heuristic if you like

    min_price, max_price = _derive_price_band(budget)
    min_year, max_year = _derive_year_range(age_pref)
    min_mileage, max_mileage = _derive_mileage_limit(mileage_tol)
    max_owners = _derive_owner_limit(owner_tol)
    engine_cat = _derive_engine_category(running_cost_priority)
    body_code = _derive_body_type_code(body_pref, family_size)

    return CarFilters(
        brand=(brand or "").strip().lower(),
        min_price=min_price,
        max_price=max_price,
        min_year=min_year,
        max_year=max_year,
        min_mileage=min_mileage,
        max_mileage=max_mileage,
        max_owners=max_owners,
        engine_cc_category=engine_cat,
        body_type_code=body_code,
        min_depreciation=None,
        max_depreciation=None,
    )


def filters_to_dict(filters: CarFilters) -> Dict[str, Any]:
    """
    Convenience: convert CarFilters dataclass into a plain dict.
    Useful for logging / passing into other functions.
    """
    return {
        "brand": filters.brand,
        "min_price": filters.min_price,
        "max_price": filters.max_price,
        "min_year": filters.min_year,
        "max_year": filters.max_year,
        "min_mileage": filters.min_mileage,
        "max_mileage": filters.max_mileage,
        "max_owners": filters.max_owners,
        "engine_cc_category": filters.engine_cc_category,
        "body_type_code": filters.body_type_code,
        "min_depreciation": filters.min_depreciation,
        "max_depreciation": filters.max_depreciation,
    }

# filters.py

def build_filters_from_profile(profile: dict) -> dict:
    """
    Converts the interpreted user profile into structured numeric filters
    usable for DuckDB car_listings search.

    Output fields:
      - brand
      - min_price, max_price
      - min_year, max_year
      - min_mileage, max_mileage
      - max_owners
      - engine_cc_category
      - body_type_code
      - min_depreciation, max_depreciation
    """

    # 1. Budget
    budget = profile.get("budget_sgd", 0)
    min_price = int(budget * 0.8)          # user budget minus 20%
    max_price = int(budget * 1.2)          # allow 20% upper room

    # 2. Year range → depends on age preference
    age_pref = profile.get("age_preference", "balanced")

    if age_pref == "newest":
        min_year, max_year = 2020, 2025
    elif age_pref == "older_ok":
        min_year, max_year = 2012, 2025
    else:  # balanced
        min_year, max_year = 2015, 2025

    # 3. Mileage tolerance
    mileage_pref = profile.get("mileage_tolerance", "medium")

    if mileage_pref == "low":
        max_mileage = 60000
    elif mileage_pref == "high":
        max_mileage = 180000
    else:
        max_mileage = 120000

    # 4. Owners
    owner_tol = profile.get("owner_tolerance", "medium")
    if owner_tol == "low":
        max_owners = 1
    elif owner_tol == "high":
        max_owners = 5
    else:
        max_owners = 3

    # 5. Brand preference (may be empty string)
    brand = profile.get("brand_bias", "")
    if brand and "prefer" in brand.lower():
        brand = brand.replace("prefers", "").replace("prefer", "").strip()
    else:
        brand = ""

    # 6. Body type → map to simple code (you can refine if needed)
    body_pref = profile.get("body_type_pref", "")
    if body_pref == "sedan_or_hatchback":
        body_code = 4      # your internal code mapping
    elif body_pref == "mpv":
        body_code = 7
    elif body_pref == "suv":
        body_code = 3
    else:
        body_code = None

    # 7. Depreciation priority
    dep_pref = profile.get("running_cost_priority", "medium")
    min_dep = None
    max_dep = None
    if dep_pref == "low":
        max_dep = 15000
    elif dep_pref == "high":
        min_dep = 15000

    # 8. Engine category (crude logic for EV)
    engine_cc_category = None
    if profile.get("fuel_pref", "") == "ev":
        engine_cc_category = 0  # EV category in your db if exists

    # 9. Family size logic: widen search for 6+ seats
    if profile.get("family_size", 0) >= 5:
        # allow MPV/SUV
        if body_code is None:
            body_code = 7

    return {
        "brand": brand,
        "min_price": min_price,
        "max_price": max_price,
        "min_year": min_year,
        "max_year": max_year,
        "min_mileage": 0,
        "max_mileage": max_mileage,
        "max_owners": max_owners,
        "engine_cc_category": engine_cc_category,
        "body_type_code": body_code,
        "min_depreciation": min_dep,
        "max_depreciation": max_dep,
    }

# filters.py

def build_filters_from_profile(profile: dict) -> dict:
    """
    Converts interpreted user profile into structured numeric filters
    for DuckDB search.
    """

    # --- 1. Budget ---
    budget = profile.get("budget_sgd", 0)
    min_price = int(budget * 0.8)
    max_price = int(budget * 1.2)

    # --- 2. Year preference ---
    age_pref = profile.get("age_preference", "balanced")
    if age_pref == "newest":
        min_year, max_year = 2020, 2025
    elif age_pref == "older_ok":
        min_year, max_year = 2012, 2025
    else:
        min_year, max_year = 2015, 2025

    # --- 3. Mileage ---
    mileage_pref = profile.get("mileage_tolerance", "medium")
    if mileage_pref == "low":
        max_mileage = 60000
    elif mileage_pref == "high":
        max_mileage = 180000
    else:
        max_mileage = 120000

    # --- 4. Owners ---
    owner_pref = profile.get("owner_tolerance", "medium")
    if owner_pref == "low":
        max_owners = 1
    elif owner_pref == "high":
        max_owners = 5
    else:
        max_owners = 3

    # --- 5. Brand ---
    brand = profile.get("brand_bias", "")
    if "prefer" in brand.lower():
        brand = brand.lower().replace("prefers", "").replace("prefer", "").strip()
    else:
        brand = ""

    # --- 6. Body type ---
    body_pref = profile.get("body_type_pref", "")
    if body_pref == "sedan_or_hatchback":
        body_code = 4
    elif body_pref == "mpv":
        body_code = 7
    elif body_pref == "suv":
        body_code = 3
    else:
        body_code = None

    # --- 7. Depreciation ---
    dep_pref = profile.get("running_cost_priority", "medium")
    min_dep = None
    max_dep = None
    if dep_pref == "low":
        max_dep = 15000
    elif dep_pref == "high":
        min_dep = 15000

    # --- 8. EV engine code ---
    engine_cc_category = 0 if profile.get("fuel_pref") == "ev" else None

    # --- 9. Family size override ---
    if profile.get("family_size", 0) >= 5 and body_code is None:
        body_code = 7

    return {
        "brand": brand,
        "min_price": min_price,
        "max_price": max_price,
        "min_year": min_year,
        "max_year": max_year,
        "min_mileage": 0,
        "max_mileage": max_mileage,
        "max_owners": max_owners,
        "engine_cc_category": engine_cc_category,
        "body_type_code": body_code,
        "min_depreciation": min_dep,
        "max_depreciation": max_dep,
    }
