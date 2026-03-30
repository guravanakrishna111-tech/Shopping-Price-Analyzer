from services.market_intelligence import get_analysis_bundle


def predict_price(product_name, platform=None, months_ahead=3):
    analysis = get_analysis_bundle(product_name, platform, months_ahead=months_ahead)
    return analysis["prediction"]
