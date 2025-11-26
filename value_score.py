# value_score.py
import numpy as np
import pandas as pd

def compute_value_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Value = weighted balance of Price (lower better), Year (newer better),
            Mileage (lower better), COE_left (higher better),
            plus a small bump for preferred colours/variants.
    Output: adds 'value_score' [0..10] and 'value_band' to df.
    """
    tmp = df.copy()

    # Safe guards for missing values
    for col in ["price", "year", "mileage_km", "coe_left_years"]:
        if col not in tmp.columns:
            tmp[col] = np.nan

    # Normalize (robust) → 0..1
    def rminmax(x):
        q1, q99 = np.nanpercentile(x, [1, 99]) if x.notna().sum() > 0 else (0, 1)
        clipped = np.clip(x, q1, q99)
        return (clipped - q1) / (q99 - q1 + 1e-9)

    price_n = rminmax(tmp["price"].astype(float))
    year_n  = rminmax(tmp["year"].astype(float))
    mile_n  = rminmax(tmp["mileage_km"].astype(float))
    coe_n   = rminmax(tmp["coe_left_years"].astype(float))

    # Scoring: higher is better
    score = (
        (1 - price_n) * 0.40 +    # lower price better
        (year_n)       * 0.20 +    # newer year better
        (1 - mile_n)   * 0.20 +    # lower mileage better
        (coe_n)        * 0.15      # more COE left better
    )

    # Colour/variant bump
    bump = (
        tmp.get("colour","").astype(str).str.contains("White|Black|Grey", case=False).astype(int) * 0.03 +
        tmp.get("variant","").astype(str).str.contains("Luxury|Prestige|Sunroof|Hybrid|Electric", case=False).astype(int) * 0.02
    )
    tmp["value_score"] = (score + bump) * 10
    tmp["value_score"] = tmp["value_score"].clip(0, 10).round(2)

    bins = [0, 6.5, 8, 10]
    labels = ["Fair", "Good", "High"]
    tmp["value_band"] = pd.cut(tmp["value_score"], bins=bins, labels=labels, include_lowest=True)

    return tmp
