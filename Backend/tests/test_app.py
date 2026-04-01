import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as backend_app


class SearchRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = backend_app.app.test_client()

    def test_search_uses_one_analysis_bundle(self):
        mock_analysis = {
            "product": {"name": "Demo Product", "asin": "B0FV2RYGXW"},
            "price_data": [{"date": "Apr 2026", "price": 1199.0, "discount": 0, "rating": 4.2, "event": "Mid-Season Refresh", "kind": "historical"}],
            "summary": {"currentPrice": 1199.0, "resultCount": 1},
            "insights": ["Resolved from live Amazon data using Amazon URL."],
            "recommendations": [{"asin": "B000000001", "name": "Related Product"}],
            "prediction": {"nextPrice": 1149.0, "forecast": [], "confidence": "medium"},
        }

        with patch.object(backend_app, "get_analysis_bundle", return_value=mock_analysis) as mocked_bundle:
            response = self.client.get("/search?product=https://www.amazon.in/dp/B0FV2RYGXW")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["product"]["name"], "Demo Product")
        mocked_bundle.assert_called_once_with("https://www.amazon.in/dp/B0FV2RYGXW", "amazon", months_ahead=3)


if __name__ == "__main__":
    unittest.main()
