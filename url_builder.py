# url_builder.py
"""
Build SGCarMart used-car listing URLs from numeric filters.
This is NOT official API — we simply format the URL exactly like SGCarMart expects.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CarFilters:
    """Filters extracted from LLM profile & rules."""
    brand: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    max_mileage: Optional[int] = None
    max_owners: Optional[int] = None


def build_used_cars_url(f: CarFilters, limit: int = 20) -> str:
    """
    Build an SGCarMart used-car listing URL.
    Example final URLs:
    https://www.sgcarmart.com/used-cars/listing?limit=20&q=honda&pr1=50000&pr2=90000&fr=2015&to=2023&mil2=120000&own=2
    """
    base = "https://www.sgcarmart.com/used-cars/listing?"

    params = [
        f"limit={limit}",
        "veh=15",          # 15 = used cars
    ]

    # Brand → SGCarMart "q"
    if f.brand:
        params.append(f"q={f.brand.lower()}")

    # Price range
    if f.min_price:
        params.append(f"pr1={f.min_price}")
    if f.max_price:
        params.append(f"pr2={f.max_price}")

    # Year range
    if f.min_year:
        params.append(f"fr={f.min_year}")
    if f.max_year:
        params.append(f"to={f.max_year}")

    # Mileage
    if f.max_mileage:
        params.append(f"mil2={f.max_mileage}")

    # Owners
    if f.max_owners:
        params.append(f"own={f.max_owners}")

    return base + "&".join(params)
