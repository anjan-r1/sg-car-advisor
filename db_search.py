# db_search.py
import duckdb
import pandas as pd
from typing import Dict, Any

DB_PATH = "cars.duckdb"


def _connect():
    return duckdb.connect(DB_PATH, read_only=True)


def search_cars_in_duckdb(filters: Dict[str, Any], limit: int = 50) -> pd.DataFrame:
    """
    Search cars in local DuckDB, using only columns that actually exist:
    category, make, model, variant, price_sgd, annual_cost_sgd, year,
    mileage_km, efficiency, efficiency_unit, bhp, gearbox, country,
    dealer_name, dealer_link, listing_url, raw_text, scraped_at,
    coe_left_years, colour.
    """
    # Filters is a plain dict (from build_filters_from_profile)
    brand          = (filters or {}).get("brand")
    min_price      = (filters or {}).get("min_price")
    max_price      = (filters or {}).get("max_price")
    min_year       = (filters or {}).get("min_year")
    max_year       = (filters or {}).get("max_year")
    min_mileage    = (filters or {}).get("min_mileage")
    max_mileage    = (filters or {}).get("max_mileage")

    where = []
    params = []

    if brand:
        where.append("LOWER(make) LIKE ?")
        params.append(f"%{brand.lower()}%")

    if min_price is not None:
        where.append("price_sgd >= ?")
        params.append(int(min_price))

    if max_price is not None:
        where.append("price_sgd <= ?")
        params.append(int(max_price))

    if min_year is not None:
        where.append("year >= ?")
        params.append(int(min_year))

    if max_year is not None:
        where.append("year <= ?")
        params.append(int(max_year))

    if min_mileage is not None:
        where.append("mileage_km >= ?")
        params.append(int(min_mileage))

    if max_mileage is not None:
        where.append("mileage_km <= ?")
        params.append(int(max_mileage))

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    sql = f"""
        SELECT
            category,
            make,
            model,
            variant,
            price_sgd,
            annual_cost_sgd,
            year,
            mileage_km,
            efficiency,
            efficiency_unit,
            bhp,
            gearbox,
            country,
            dealer_name,
            dealer_link,
            listing_url,
            raw_text,
            scraped_at,
            coe_left_years,
            colour
        FROM car_listings
        {where_sql}
        ORDER BY price_sgd ASC
        LIMIT {int(limit)}
    """

    con = _connect()
    print("[DB_SEARCH] SQL:", sql)
    print("[DB_SEARCH] Params:", params)
    df = con.execute(sql, params).df()
    con.close()
    return df


def search_with_fallback(filters: Dict[str, Any], limit: int = 50) -> pd.DataFrame:
    """
    1) Try strict filters.
    2) If empty, drop year & mileage filters.
    3) If still empty, just use price band (or even no filters).
    """
    # 1. strict
    df = search_cars_in_duckdb(filters, limit=limit)
    if not df.empty:
        return df

    # 2. relaxed: drop year & mileage
    relaxed = dict(filters or {})
    relaxed["min_year"] = None
    relaxed["max_year"] = None
    relaxed["min_mileage"] = None
    relaxed["max_mileage"] = None
    df = search_cars_in_duckdb(relaxed, limit=limit)
    if not df.empty:
        return df

    # 3. super-relaxed: only price (and brand if given)
    super_relaxed = {
        "brand": relaxed.get("brand"),
        "min_price": relaxed.get("min_price"),
        "max_price": relaxed.get("max_price"),
    }
    df = search_cars_in_duckdb(super_relaxed, limit=limit)
    if not df.empty:
        return df

    # 4. final fallback: show *some* cars so the app never looks empty
    return search_cars_in_duckdb({}, limit=limit)
