from flask import Flask, jsonify, request
from flask_cors import CORS

from services.amazon_api import AmazonAPIError
from services.analysis import get_price_trend
from services.prediction import predict_price
from services.recommendation import get_recommendations

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return "Welcome to GetOne4u API"


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/search")
def search():
    product = request.args.get("product", "").strip()
    platform = "amazon"

    if not product:
        return jsonify({"error": "Product is required"}), 400

    try:
        analysis = get_price_trend(product, platform)
        recommendations = get_recommendations(product, platform)
        prediction = predict_price(product, platform)
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
            "recommendations": recommendations,
            "prediction": prediction,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
