import json
import os
import re
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import Request, urlopen


RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "real-time-amazon-data.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "dfe030ca5cmsh6af88aaab3854d3p12faa3jsn228bbc0607e2")
AMAZON_COUNTRY = os.getenv("AMAZON_COUNTRY", "in")
BASE_URL = f"https://{RAPIDAPI_HOST}"

ASIN_PATTERN = re.compile(r"\b([A-Z0-9]{10})\b", re.IGNORECASE)
URL_PATTERNS = (
    re.compile(r"/dp/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/gp/aw/d/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/gp/product/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/product/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/(?:[^/]+/)?dp/([A-Z0-9]{10})", re.IGNORECASE),
)
AMAZON_HOST_MARKERS = ("amazon.", "amzn.", "a.co")
REDIRECT_PARAM_KEYS = ("asin", "url", "u", "redirect", "redirecturl", "path", "destination", "dest")
SEARCH_PARAM_KEYS = ("k", "keyword", "keywords", "field-keywords")
COUNTRY_DOMAIN_MAP = {
    "us": "www.amazon.com",
    "in": "www.amazon.in",
    "uk": "www.amazon.co.uk",
    "de": "www.amazon.de",
    "fr": "www.amazon.fr",
    "it": "www.amazon.it",
    "es": "www.amazon.es",
    "ca": "www.amazon.ca",
    "mx": "www.amazon.com.mx",
    "br": "www.amazon.com.br",
    "au": "www.amazon.com.au",
    "ae": "www.amazon.ae",
    "jp": "www.amazon.co.jp",
    "sg": "www.amazon.sg",
    "nl": "www.amazon.nl",
    "sa": "www.amazon.sa",
    "se": "www.amazon.se",
    "tr": "www.amazon.com.tr",
    "pl": "www.amazon.pl",
    "eg": "www.amazon.eg",
}
DOMAIN_COUNTRY_MAP = {
    "amazon.com": "us",
    "amazon.in": "in",
    "amazon.co.uk": "uk",
    "amazon.de": "de",
    "amazon.fr": "fr",
    "amazon.it": "it",
    "amazon.es": "es",
    "amazon.ca": "ca",
    "amazon.com.mx": "mx",
    "amazon.com.br": "br",
    "amazon.com.au": "au",
    "amazon.ae": "ae",
    "amazon.co.jp": "jp",
    "amazon.sg": "sg",
    "amazon.nl": "nl",
    "amazon.sa": "sa",
    "amazon.se": "se",
    "amazon.com.tr": "tr",
    "amazon.pl": "pl",
    "amazon.eg": "eg",
    "amzn.in": "in",
    "amzn.to": "us",
}


class AmazonAPIError(RuntimeError):
    pass


def _parse_float(value):
    if value in (None, "", "Not available", "No rating available"):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    match = re.search(r"(\d+(?:,\d{3})*(?:\.\d+)?)", str(value))
    if not match:
        return None

    return float(match.group(1).replace(",", ""))


def _parse_int(value):
    numeric = _parse_float(value)
    return int(numeric) if numeric is not None else None


def _clean_text(value, fallback=""):
    if value in (None, "Not available", "No video"):
        return fallback
    return str(value).strip()


def looks_like_url(value):
    parsed = urlparse(str(value).strip())
    return bool(parsed.scheme and parsed.netloc)


def _is_amazon_host(hostname):
    hostname = (hostname or "").lower()
    return any(marker in hostname for marker in AMAZON_HOST_MARKERS)


def _is_short_amazon_host(hostname):
    hostname = (hostname or "").lower()
    return hostname == "a.co" or "amzn." in hostname


def amazon_domain_for_country(country):
    return COUNTRY_DOMAIN_MAP.get((country or AMAZON_COUNTRY).lower(), COUNTRY_DOMAIN_MAP[AMAZON_COUNTRY])


def infer_country_from_value(value, default=AMAZON_COUNTRY):
    if not looks_like_url(value):
        return default

    for candidate in _normalized_candidates(value):
        parsed = urlparse(candidate)
        hostname = parsed.netloc.lower()
        if not _is_amazon_host(hostname):
            continue

        for domain, country in DOMAIN_COUNTRY_MAP.items():
            if hostname.endswith(domain):
                return country

    return default


def _normalized_candidates(value):
    candidates = []
    current = str(value).strip()

    for _ in range(4):
        if current and current not in candidates:
            candidates.append(current)
        decoded = unquote(current)
        if decoded == current:
            break
        current = decoded

    return candidates


def _extract_asin_from_candidate(candidate):
    if not candidate:
        return None

    if ASIN_PATTERN.fullmatch(candidate):
        return candidate.upper()

    for pattern in URL_PATTERNS:
        match = pattern.search(candidate)
        if match:
            return match.group(1).upper()

    if not looks_like_url(candidate):
        return None

    parsed = urlparse(candidate)
    query_params = parse_qs(parsed.query)

    for key, values in query_params.items():
        lowered_key = key.lower()
        for possible in values:
            if lowered_key in REDIRECT_PARAM_KEYS:
                nested_asin = extract_asin(possible)
                if nested_asin:
                    return nested_asin

    for key in ("asin", "ASIN"):
        if key in query_params and query_params[key]:
            possible = query_params[key][0].strip().upper()
            if ASIN_PATTERN.fullmatch(possible):
                return possible

    if _is_amazon_host(parsed.netloc):
        generic = ASIN_PATTERN.search(candidate)
        if generic:
            return generic.group(1).upper()

    return None


def _resolve_short_url_asin(url):
    if not looks_like_url(url):
        return None

    parsed = urlparse(url)
    if not _is_short_amazon_host(parsed.netloc):
        return None

    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    try:
        with urlopen(request, timeout=12) as response:
            final_url = response.geturl()
    except (HTTPError, URLError):
        return None

    if final_url and final_url != url:
        return extract_asin(final_url)

    return None


def extract_asin(value):
    if not value:
        return None

    raw_value = str(value).strip()

    for candidate in _normalized_candidates(raw_value):
        asin = _extract_asin_from_candidate(candidate)
        if asin:
            return asin

    return _resolve_short_url_asin(raw_value)


def extract_search_keyword(value):
    if not looks_like_url(value):
        return ""

    for candidate in _normalized_candidates(value):
        parsed = urlparse(candidate)
        if not _is_amazon_host(parsed.netloc):
            continue

        query_params = parse_qs(parsed.query)
        for key in SEARCH_PARAM_KEYS:
            values = query_params.get(key)
            if values and values[0].strip():
                return values[0].strip().replace("+", " ")

        for key, values in query_params.items():
            if key.lower() in REDIRECT_PARAM_KEYS:
                nested_keyword = extract_search_keyword(values[0])
                if nested_keyword:
                    return nested_keyword

        if _is_short_amazon_host(parsed.netloc):
            return ""

        path_segments = [segment for segment in parsed.path.split("/") if segment]
        cleaned_segments = [
            segment.replace("-", " ")
            for segment in path_segments
            if segment.lower() not in {"dp", "gp", "aw", "s", "sspa", "click", "slredirect", "stores", "product", "d"}
            and not ASIN_PATTERN.fullmatch(segment.upper())
        ]
        if cleaned_segments:
            return cleaned_segments[0].strip()

    return ""


@lru_cache(maxsize=128)
def _cached_api_get(endpoint, query_string):
    if not RAPIDAPI_KEY:
        raise AmazonAPIError("RapidAPI key is missing.")

    url = f"{BASE_URL}/{endpoint}"
    if query_string:
        url = f"{url}?{query_string}"

    request = Request(
        url,
        headers={
            "Content-Type": "application/json",
            "x-rapidapi-host": RAPIDAPI_HOST,
            "x-rapidapi-key": RAPIDAPI_KEY,
        },
    )

    try:
        with urlopen(request, timeout=25) as response:
            raw_body = response.read().decode("utf-8", errors="ignore")
            payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise AmazonAPIError(
            f"Amazon API returned invalid JSON response: {raw_body[:240]}"
        ) from exc
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise AmazonAPIError(f"Amazon API request failed with status {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise AmazonAPIError(f"Amazon API request failed: {exc.reason}") from exc

    if str(payload.get("status") or "").upper() not in ("", "SUCCESS", "OK"):
        message = payload.get("message") or payload.get("error") or "Amazon API returned an unexpected response."
        raise AmazonAPIError(message)

    if payload.get("error"):
        raise AmazonAPIError(str(payload["error"]))

    return payload


def _api_get(endpoint, **params):
    filtered_params = {
        key: value
        for key, value in params.items()
        if value not in (None, "", [])
    }
    query_string = urlencode(sorted(filtered_params.items()))
    return _cached_api_get(endpoint, query_string)


def normalize_search_item(item, country=AMAZON_COUNTRY):
    title = _clean_text(item.get("ProductTitle") or item.get("product_title") or item.get("title"))
    price = _parse_float(item.get("price") or item.get("product_price"))
    original_price = _parse_float(item.get("originalPrice") or item.get("product_original_price"))
    rating = _parse_float(item.get("rating") or item.get("product_star_rating"))
    total_ratings = _parse_int(item.get("totalRatings") or item.get("product_num_ratings"))
    product_url = _clean_text(item.get("productUrl") or item.get("product_url") or item.get("url"))
    product_image = _clean_text(item.get("productImage") or item.get("product_photo") or item.get("imageUrl") or item.get("image"))
    badge = _clean_text(item.get("productBadge") or item.get("product_badge"))
    discount_text = _clean_text(item.get("discount"))
    sales_volume = _clean_text(item.get("salesVolume") or item.get("sales_volume"))

    if original_price and price and original_price > price:
        discount_percent = round(((original_price - price) / original_price) * 100, 2)
    else:
        discount_percent = _parse_float(discount_text) or 0.0

    return {
        "asin": _clean_text(item.get("asin")).upper(),
        "name": title,
        "price": price,
        "originalPrice": original_price,
        "rating": rating or 0.0,
        "ratingCount": total_ratings or 0,
        "url": product_url or (f"https://{amazon_domain_for_country(country)}/dp/{_clean_text(item.get('asin')).upper()}" if item.get("asin") else ""),
        "image": product_image,
        "description": ". ".join(part for part in (badge, sales_volume, discount_text) if part),
        "discountText": discount_text,
        "discount": discount_percent,
        "brand": _clean_text(item.get("brand")),
        "category": _clean_text(item.get("category")),
        "productType": _clean_text(item.get("productType") or item.get("product_type")),
        "salesVolume": sales_volume,
        "isPrime": str(item.get("isPrime") or item.get("is_prime")).lower() == "true",
        "isBestSeller": str(item.get("isBestSellar") or item.get("is_best_seller")).lower() == "true",
        "isAmazonChoice": str(item.get("isAmazonChoice") or item.get("is_amazon_choice")).lower() == "true",
        "platform": "amazon",
    }


def normalize_detail_item(payload, country=AMAZON_COUNTRY):
    images = payload.get("images") or payload.get("product_photos") or []
    if isinstance(images, str):
        images = [images]

    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    about_this_item = payload.get("aboutThisItem") or payload.get("about_product") or []
    if isinstance(about_this_item, str):
        about_this_item = [about_this_item]

    title = _clean_text(payload.get("title") or payload.get("product_title"))
    asin = _clean_text(payload.get("asin") or details.get("ASIN")).upper()
    price = _parse_float(payload.get("price") or payload.get("product_price"))
    original_price = _parse_float(payload.get("originalPrice") or payload.get("product_original_price"))
    rating = _parse_float(payload.get("rating") or payload.get("product_star_rating"))
    rating_count = _parse_int(payload.get("ratingNumber") or payload.get("product_num_ratings"))
    category = _clean_text(payload.get("category"))
    brand = _clean_text(payload.get("brand") or details.get("Brand"))
    main_image = images[0] if images else ""
    color = _clean_text(details.get("Color"))

    if original_price and price and original_price > price:
        discount_percent = round(((original_price - price) / original_price) * 100, 2)
    else:
        discount_percent = _parse_float(payload.get("discountPercentage")) or 0.0

    description_parts = [
        _clean_text(payload.get("productDescription") or payload.get("product_description")),
        " ".join(_clean_text(point) for point in about_this_item[:2] if point),
    ]

    return {
        "asin": asin,
        "name": title,
        "price": price,
        "originalPrice": original_price,
        "rating": rating or 0.0,
        "ratingCount": rating_count or 0,
        "brand": brand,
        "category": category,
        "productType": category.split(",")[-1].strip() if category else "",
        "description": " ".join(part for part in description_parts if part).strip(),
        "availability": _clean_text(payload.get("availability") or payload.get("product_availability")),
        "sellerName": _clean_text(payload.get("sellerName")),
        "sellerId": _clean_text(payload.get("sellerId")),
        "discount": discount_percent,
        "url": f"https://{amazon_domain_for_country(country)}/dp/{asin}" if asin else "",
        "image": main_image,
        "images": images,
        "color": color,
        "details": details,
        "platform": "amazon",
    }


def search_products(keyword, country=AMAZON_COUNTRY, page=1):
    payload = _api_get(
        "search",
        query=keyword,
        country=str(country).upper(),
        page=page,
        sort_by="RELEVANCE",
        product_condition="ALL",
    )
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    items = data.get("details") or data.get("products") or []
    normalized_items = [normalize_search_item(item, country=country) for item in items]
    return {
        "items": [item for item in normalized_items if item.get("asin")],
        "total_results": int(data.get("totalResultsCount") or data.get("total_products") or len(items)),
        "currency": data.get("currency") or "USD",
        "domain": data.get("domain") or "https://www.amazon.com",
    }


def get_product_details(asin, country=AMAZON_COUNTRY):
    payload = _api_get("product-details", asin=asin, country=str(country).upper())
    payload = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    normalized = normalize_detail_item(payload, country=country)
    normalized["asin"] = normalized.get("asin") or _clean_text(asin).upper()
    if normalized["asin"] and not normalized.get("url"):
        normalized["url"] = f"https://{amazon_domain_for_country(country)}/dp/{normalized['asin']}"
    return normalized


def get_best_sellers(category, country=AMAZON_COUNTRY, page=1):
    payload = _api_get("best-sellers", category=category, country=str(country).upper(), page=page)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    items = data.get("products") or data.get("details") or []
    normalized = []
    for item in items:
        normalized.append(
            {
                "asin": _clean_text(item.get("asin")).upper(),
                "name": _clean_text(item.get("title")),
                "price": _parse_float(item.get("price")),
                "originalPrice": None,
                "rating": _parse_float(item.get("rating")) or 0.0,
                "ratingCount": _parse_int(item.get("rating_count")) or 0,
                "url": _clean_text(item.get("link") or item.get("url")),
                "image": _clean_text(item.get("image") or item.get("imageUrl")),
                "description": f"Amazon best seller rank {item.get('rank')}".strip(),
                "discountText": "",
                "discount": 0.0,
                "brand": "",
                "category": category,
                "productType": category,
                "salesVolume": "",
                "isPrime": False,
                "isBestSeller": True,
                "isAmazonChoice": False,
                "platform": "amazon",
            }
        )
    return normalized
