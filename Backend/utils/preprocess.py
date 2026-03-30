from functools import lru_cache
from pathlib import Path

import pandas as pd


PLATFORMS = ("amazon",)
EVENT_BY_MONTH = {
    1: "Republic Day Sale",
    2: "Valentine Picks",
    3: "Holi Specials",
    4: "Summer Refresh",
    5: "Wedding Season",
    6: "Monsoon Deals",
    7: "Prime Style Week",
    8: "Independence Sale",
    9: "Big Billion Prep",
    10: "Diwali Festival",
    11: "Wedding Festive Rush",
    12: "Year End Sale",
}


def _assign_platform(row):
    key = f"{row['product_name']}-{row['brand']}-{row['category']}-{row['date'].strftime('%Y-%m')}"
    platform_index = sum(ord(char) for char in key) % len(PLATFORMS)
    return PLATFORMS[platform_index]


@lru_cache(maxsize=1)
def load_data():
    csv_path = Path(__file__).resolve().parents[1] / "data" / "products.csv"
    df = pd.read_csv(csv_path)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()

    if "platform" not in df.columns:
        df["platform"] = df.apply(_assign_platform, axis=1)

    df["platform"] = df["platform"].astype(str).str.lower()
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["month_label"] = df["date"].dt.strftime("%b %Y")
    df["event"] = df["month"].map(EVENT_BY_MONTH).fillna("Seasonal Drop")

    for column in ["price", "discount", "rating", "stock"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    for column in [
        "product_name",
        "category",
        "product_type",
        "brand",
        "color",
        "size",
        "material",
        "occasion",
        "description",
        "platform",
        "event",
    ]:
        df[column] = df[column].fillna("").astype(str)

    return df.sort_values(["product_name", "date"]).reset_index(drop=True)
