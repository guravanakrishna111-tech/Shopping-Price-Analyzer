import math
import re
from datetime import datetime
from functools import lru_cache
from statistics import mean, pstdev

import pandas as pd
from sklearn.linear_model import LinearRegression

from services.amazon_api import (
    AMAZON_COUNTRY,
    AmazonAPIError,
    extract_asin,
    extract_search_keyword,
    get_best_sellers,
    get_product_details,
    infer_country_from_value,
    looks_like_url,
    search_products,
)


EVENT_BY_MONTH = {
    1: "New Year Reset",
    2: "Valentine Offers",
    3: "Spring Drop",
    4: "Mid-Season Refresh",
    5: "Summer Preview",
    6: "Monsoon Electronics Push",
    7: "Prime Day Window",
    8: "Back to School",
    9: "Season Switch",
    10: "Holiday Build-Up",
    11: "Black Friday and Cyber Monday",
    12: "Year-End Deals",
}

SEASONAL_FACTORS = {
    1: 0.99,
    2: 1.01,
    3: 1.0,
    4: 1.02,
    5: 1.01,
    6: 0.98,
    7: 0.95,
    8: 0.99,
    9: 1.0,
    10: 0.97,
    11: 0.91,
    12: 0.94,
}


def _empty_analysis():
    return {
        "product": None,
        "price_data": [],
        "prediction": {"nextPrice": None, "forecast": [], "confidence": "low"},
        "recommendations": [],
        "summary": {},
        "insights": [],
    }


def _tokenize(value):
    return set(re.findall(r"[a-z0-9]+", str(value).lower()))


def _safe_price(item):
    return item.get("price") or item.get("originalPrice") or 0.0


def _slugify_category(category):
    if not category:
        return ""

    tail = category.split(",")[-1].strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", tail).strip("-")


def _merge_product_data(search_item, detail_item):
    if not search_item:
        return detail_item

    merged = {**search_item, **detail_item}
    merged["price"] = detail_item.get("price") or search_item.get("price")
    merged["originalPrice"] = detail_item.get("originalPrice") or search_item.get("originalPrice")
    merged["image"] = detail_item.get("image") or search_item.get("image")
    merged["description"] = detail_item.get("description") or search_item.get("description")
    merged["url"] = detail_item.get("url") or search_item.get("url")
    return merged


def _resolve_keyword_context(query, country):
    search_payload = search_products(query, country=country)
    items = search_payload["items"]
    if not items:
        return None

    primary_search_item = items[0]
    detail_item = get_product_details(primary_search_item["asin"], country=country)
    product = _merge_product_data(primary_search_item, detail_item)

    return {
        "product": product,
        "candidates": items,
        "result_count": search_payload["total_results"],
        "query_type": "keyword",
        "resolved_query": query.strip(),
    }


def _resolve_asin_or_url_context(query, country):
    asin = extract_asin(query)
    if not asin:
        return None

    product = get_product_details(asin, country=country)
    search_queries = [product.get("name", ""), f"{product.get('brand', '')} {product.get('productType', '')}".strip()]

    candidates = []
    result_count = 0
    for search_query in search_queries:
        if not search_query:
            continue
        payload = search_products(search_query, country=country)
        if payload["items"]:
            candidates = payload["items"]
            result_count = payload["total_results"]
            break

    return {
        "product": product,
        "candidates": candidates,
        "result_count": result_count or len(candidates),
        "query_type": "url" if looks_like_url(query) else "asin",
        "resolved_query": product.get("name") or query.strip(),
    }


def _resolve_context(query, country):
    if not query or not query.strip():
        return None

    if extract_asin(query) or looks_like_url(query):
        resolved = _resolve_asin_or_url_context(query, country)
        if resolved:
            return resolved

        keyword_from_url = extract_search_keyword(query)
        if keyword_from_url:
            resolved = _resolve_keyword_context(keyword_from_url, country)
            if resolved:
                return resolved

    return _resolve_keyword_context(query, country)


def _similarity_score(primary, candidate):
    primary_tokens = _tokenize(primary.get("name"))
    candidate_tokens = _tokenize(candidate.get("name"))
    token_score = len(primary_tokens & candidate_tokens) / len(primary_tokens | candidate_tokens) if primary_tokens and candidate_tokens else 0.0

    price_gap = abs(_safe_price(candidate) - _safe_price(primary)) / max(_safe_price(primary), 1)
    price_score = max(0.0, 1 - min(price_gap, 1.2))

    rating_gap = abs((candidate.get("rating") or 0) - (primary.get("rating") or 0)) / 5
    rating_score = max(0.0, 1 - rating_gap)

    same_brand = 1.0 if candidate.get("brand") and candidate.get("brand") == primary.get("brand") else 0.0
    premium_flags = 0.15 if candidate.get("isAmazonChoice") or candidate.get("isBestSeller") else 0.0

    score = (token_score * 0.55) + (price_score * 0.2) + (rating_score * 0.1) + (same_brand * 0.15) + premium_flags
    return round(min(score * 100, 99.5), 1)


def _build_recommendations(product, candidates, country):
    recommendations = []
    seen_asins = {product.get("asin")}

    for item in candidates:
        asin = item.get("asin")
        if not asin or asin in seen_asins:
            continue

        recommendations.append(
            {
                **item,
                "brand": item.get("brand") or product.get("brand") or "Amazon",
                "category": item.get("category") or product.get("category") or "Amazon catalogue",
                "productType": item.get("productType") or product.get("productType") or "Amazon result",
                "description": item.get("description") or "Live Amazon catalogue result.",
                "similarity": _similarity_score(product, item),
                "color": item.get("color") or product.get("color") or "Mixed",
                "material": item.get("material") or "Not listed",
                "platform": "amazon",
            }
        )
        seen_asins.add(asin)

    if len(recommendations) < 6:
        category_slug = _slugify_category(product.get("category"))
        if category_slug:
            try:
                for item in get_best_sellers(category_slug, country=country):
                    asin = item.get("asin")
                    if not asin or asin in seen_asins:
                        continue
                    recommendations.append(
                        {
                            **item,
                            "brand": item.get("brand") or product.get("brand") or "Amazon",
                            "category": item.get("category") or product.get("category") or category_slug.replace("-", " ").title(),
                            "productType": item.get("productType") or product.get("productType") or "Best seller",
                            "description": item.get("description") or "Amazon best seller fallback.",
                            "similarity": _similarity_score(product, item),
                            "color": product.get("color") or "Mixed",
                            "material": "Not listed",
                            "platform": "amazon",
                        }
                    )
                    seen_asins.add(asin)
                    if len(recommendations) >= 6:
                        break
            except AmazonAPIError:
                pass

    recommendations.sort(key=lambda item: (item.get("similarity", 0), item.get("rating", 0), -(item.get("price") or 0)), reverse=True)
    return recommendations[:6]


def _build_history(product, recommendations, months_back=8):
    current_price = _safe_price(product)
    peer_prices = [_safe_price(item) for item in recommendations if _safe_price(item) > 0]
    peer_baseline = mean(peer_prices) if peer_prices else current_price or 1
    peer_volatility = pstdev(peer_prices) / peer_baseline if len(peer_prices) > 1 and peer_baseline else 0.06
    peer_volatility = min(max(peer_volatility, 0.03), 0.18)

    original_price = product.get("originalPrice") or max(current_price * 1.08, peer_baseline * 1.03)
    rating = product.get("rating") or mean([item.get("rating", 0) for item in recommendations] or [4.0]) or 4.0

    current_month = pd.Timestamp(datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0))
    months = pd.date_range(end=current_month, periods=months_back, freq="MS")
    history = []

    for index, point_date in enumerate(months):
        progress = index / max(months_back - 1, 1)
        seasonal_factor = SEASONAL_FACTORS[point_date.month]
        baseline = original_price - ((original_price - current_price) * progress)
        peer_pull = (peer_baseline - current_price) * 0.12 * (1 - progress)
        cyclical = current_price * peer_volatility * math.sin((index + 1) * 0.9) * 0.45
        rating_adjustment = (4.3 - rating) * current_price * 0.01
        inferred_price = max(1, round((baseline * seasonal_factor) + peer_pull + cyclical + rating_adjustment, 2))

        if index == len(months) - 1:
            inferred_price = round(current_price or inferred_price, 2)

        inferred_discount = max(0, round(((max(original_price, inferred_price) - inferred_price) / max(original_price, inferred_price)) * 100, 2))
        history.append(
            {
                "date": point_date.strftime("%b %Y"),
                "price": inferred_price,
                "discount": inferred_discount,
                "rating": round(rating, 2),
                "event": EVENT_BY_MONTH[point_date.month],
                "kind": "historical",
                "year": point_date.year,
                "month": point_date.month,
            }
        )

    return history


def _predict_prices(price_data, product, recommendations, months_ahead):
    if not price_data:
        return {"nextPrice": None, "forecast": [], "confidence": "low"}

    monthly = pd.DataFrame(price_data).copy()
    monthly["time_index"] = range(len(monthly))
    monthly["seasonal_factor"] = monthly["month"].map(SEASONAL_FACTORS)
    monthly["month_sin"] = monthly["month"].apply(lambda value: math.sin((2 * math.pi * value) / 12))
    monthly["month_cos"] = monthly["month"].apply(lambda value: math.cos((2 * math.pi * value) / 12))
    monthly["discount_signal"] = monthly["discount"] / 100

    model = LinearRegression()
    model.fit(
        monthly[["time_index", "seasonal_factor", "month_sin", "month_cos", "discount_signal"]],
        monthly["price"],
    )

    last_date = pd.Timestamp(year=int(monthly.iloc[-1]["year"]), month=int(monthly.iloc[-1]["month"]), day=1)
    future_dates = pd.date_range(last_date + pd.offsets.MonthBegin(1), periods=months_ahead, freq="MS")
    baseline_discount = float(monthly["discount"].tail(3).mean())
    price_anchor = _safe_price(product)
    peer_avg = mean([_safe_price(item) for item in recommendations if _safe_price(item) > 0] or [price_anchor or 1])

    future_rows = []
    for index, future_date in enumerate(future_dates, start=len(monthly)):
        future_rows.append(
            {
                "time_index": index,
                "seasonal_factor": SEASONAL_FACTORS[future_date.month],
                "month_sin": math.sin((2 * math.pi * future_date.month) / 12),
                "month_cos": math.cos((2 * math.pi * future_date.month) / 12),
                "discount_signal": baseline_discount / 100,
                "date": future_date.strftime("%b %Y"),
                "event": EVENT_BY_MONTH[future_date.month],
            }
        )

    future_frame = pd.DataFrame(future_rows)
    predictions = model.predict(future_frame[["time_index", "seasonal_factor", "month_sin", "month_cos", "discount_signal"]])

    forecast = []
    for row, predicted in zip(future_rows, predictions):
        peer_adjustment = (peer_avg - price_anchor) * 0.08
        modeled_price = max(1, round(float(predicted + peer_adjustment), 2))
        forecast.append(
            {
                "date": row["date"],
                "price": modeled_price,
                "event": row["event"],
                "kind": "forecast",
            }
        )

    signal_count = len(recommendations) + int(bool(product.get("originalPrice"))) + int(bool(product.get("rating")))
    confidence = "high" if signal_count >= 7 else "medium" if signal_count >= 4 else "low"

    return {
        "nextPrice": forecast[0]["price"] if forecast else None,
        "forecast": forecast,
        "confidence": confidence,
    }


def _build_summary(product, price_data, prediction, result_count):
    if not price_data:
        return {}

    all_points = price_data + (prediction.get("forecast") or [])
    historical_prices = [point["price"] for point in price_data]
    projected_low = min(all_points, key=lambda item: item["price"]) if all_points else None
    historical_low = min(price_data, key=lambda item: item["price"])

    current_price = round(float(price_data[-1]["price"]), 2)
    headline = (
        f"ML suggests the strongest buy window is {projected_low['date']} around Rs. {projected_low['price']:,.2f}; "
        f"today's Amazon price is Rs. {current_price:,.2f} and the modeled floor is closest during {projected_low['event']}."
        if projected_low
        else f"Today's Amazon price is Rs. {current_price:,.2f}."
    )

    return {
        "currentPrice": current_price,
        "lowestPrice": round(float(min(historical_prices)), 2),
        "highestPrice": round(float(max(historical_prices)), 2),
        "averagePrice": round(float(mean(historical_prices)), 2),
        "averageDiscount": round(float(mean(point.get("discount", 0) for point in price_data)), 2),
        "bestBuyingMonth": projected_low["date"] if projected_low else historical_low["date"],
        "bestBuyingEvent": projected_low["event"] if projected_low else historical_low["event"],
        "lowestPriceMonth": historical_low["date"],
        "lowestProjectedMonth": projected_low["date"] if projected_low else None,
        "lowestProjectedPrice": projected_low["price"] if projected_low else None,
        "resultCount": int(result_count),
        "recommendationLine": headline,
        "currentAvailability": product.get("availability") or "Availability not listed",
    }


def _build_insights(product, recommendations, summary, prediction, query_type):
    peer_prices = [_safe_price(item) for item in recommendations if _safe_price(item) > 0]
    peer_average = mean(peer_prices) if peer_prices else summary.get("currentPrice", 0)
    query_label = {
        "keyword": "keyword search",
        "url": "Amazon URL",
        "asin": "ASIN lookup",
    }.get(query_type, "search")

    return [
        f"Resolved from live Amazon data using {query_label}.",
        f"The model blends the live Amazon price, list price, rating, and {len(recommendations)} peer listings.",
        f"Peer products average Rs. {peer_average:,.2f}, compared with the focus item at Rs. {summary.get('currentPrice', 0):,.2f}.",
        f"The lowest modeled window appears in {summary.get('bestBuyingMonth', 'N/A')} during {summary.get('bestBuyingEvent', 'seasonal activity')}.",
        f"Forecast confidence is {prediction.get('confidence', 'low')} because the signal is inferred from current Amazon marketplace data rather than stored historical tracking.",
    ]


@lru_cache(maxsize=64)
def get_analysis_bundle(query, platform=None, months_ahead=3):
    if platform and platform.lower() != "amazon":
        return _empty_analysis()

    country = infer_country_from_value(query, AMAZON_COUNTRY)

    try:
        resolved = _resolve_context(query, country)
    except AmazonAPIError:
        raise
    except Exception as exc:
        raise AmazonAPIError(f"Unable to resolve Amazon product data: {exc}") from exc

    if not resolved or not resolved["product"]:
        return _empty_analysis()

    product = {**resolved["product"], "platform": "amazon", "country": country}
    recommendations = _build_recommendations(product, resolved["candidates"], country)
    price_data = _build_history(product, recommendations)
    prediction = _predict_prices(price_data, product, recommendations, months_ahead)
    summary = _build_summary(product, price_data, prediction, resolved["result_count"])
    insights = _build_insights(product, recommendations, summary, prediction, resolved["query_type"])

    return {
        "product": product,
        "price_data": [
            {
                "date": point["date"],
                "price": point["price"],
                "discount": point["discount"],
                "rating": point["rating"],
                "event": point["event"],
                "kind": point["kind"],
            }
            for point in price_data
        ],
        "prediction": prediction,
        "recommendations": recommendations,
        "summary": summary,
        "insights": insights,
    }
