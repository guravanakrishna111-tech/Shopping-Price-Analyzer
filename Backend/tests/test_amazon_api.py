import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.amazon_api import (
    _cached_api_get,
    extract_asin,
    extract_search_keyword,
    get_product_details,
    infer_country_from_value,
    search_products,
)


class AmazonApiParsingTests(unittest.TestCase):
    def test_extract_asin_from_amazon_india_product_urls(self):
        cases = [
            "https://www.amazon.in/Symbol-Premium-Casual-Cotton-Linen/dp/B0FV2RYGXW/?encoding=UTF8&psc=1",
            "https://www.amazon.in/dp/B0FV2RYGXW",
            "https://amazon.in/gp/product/B0FV2RYGXW",
            "https://www.amazon.in/gp/aw/d/B0FV2RYGXW",
            "B0FV2RYGXW",
        ]

        for value in cases:
            with self.subTest(value=value):
                self.assertEqual(extract_asin(value), "B0FV2RYGXW")
                self.assertEqual(infer_country_from_value(value), "in")

    def test_extract_search_keyword_from_amazon_search_url(self):
        self.assertEqual(
            extract_search_keyword("https://www.amazon.in/s?k=iphone+15"),
            "iphone 15",
        )

    def test_short_share_links_do_not_fall_back_to_link_tokens(self):
        cases = [
            "https://amzn.in/d/3AbCdEf",
            "https://a.co/d/xyz1234",
        ]

        for value in cases:
            with self.subTest(value=value):
                self.assertEqual(extract_search_keyword(value), "")

    def test_get_product_details_preserves_requested_asin_when_api_omits_it(self):
        payload = {
            "title": "Demo Product",
            "price": "Rs. 1,199",
            "images": [],
        }

        with patch("services.amazon_api._api_get", return_value=payload):
            product = get_product_details("B0FV2RYGXW", country="in")

        self.assertEqual(product["asin"], "B0FV2RYGXW")
        self.assertEqual(product["url"], "https://www.amazon.in/dp/B0FV2RYGXW")

    def test_search_products_accepts_new_api_data_shape(self):
        payload = {
            "status": "OK",
            "data": {
                "total_products": 2,
                "domain": "www.amazon.in",
                "products": [
                    {
                        "asin": "B0FV2RYGXW",
                        "product_title": "Demo Product",
                        "product_price": "Rs. 1,199",
                        "product_photo": "https://example.com/demo.jpg",
                    }
                ],
            },
        }

        with patch("services.amazon_api._api_get", return_value=payload):
            result = search_products("demo product", country="in", page=1)

        self.assertEqual(result["total_results"], 2)
        self.assertEqual(result["items"][0]["asin"], "B0FV2RYGXW")
        self.assertEqual(result["items"][0]["name"], "Demo Product")

    def test_cached_api_get_accepts_ok_status(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{\"status\":\"OK\",\"data\":{\"products\":[]}}'

        _cached_api_get.cache_clear()
        with patch("services.amazon_api.urlopen", return_value=FakeResponse()):
            payload = _cached_api_get("search", "country=IN&page=1&query=demo")

        self.assertEqual(payload["status"], "OK")


if __name__ == "__main__":
    unittest.main()
