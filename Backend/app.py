from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from services.amazon_api import AmazonAPIError
from services.market_intelligence import get_analysis_bundle

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return "Welcome to GetOne4u API"


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.errorhandler(Exception)
def handle_global_error(error):
    status_code = error.code if isinstance(error, HTTPException) else 500
    return jsonify({"error": str(error)}), status_code


@app.route("/search")
def search():
    product = request.args.get("product", "").strip()
    platform = "amazon"

    if not product:
        return jsonify({"error": "Product is required"}), 400

    try:
        analysis = get_analysis_bundle(product, platform, months_ahead=3)
    except AmazonAPIError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(
        {
            "query": product,
            "platform": platform,
            "product": analysis["product"],
            "priceData": analysis["price_data"],
            "summary": analysis["summary"],
            "insights": analysis["insights"],
            "recommendations": analysis["recommendations"],
            "prediction": analysis["prediction"],
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
