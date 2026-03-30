from services.market_intelligence import get_analysis_bundle


def get_price_trend(product_name, platform=None):
    analysis = get_analysis_bundle(product_name, platform)
    return {
        "price_data": analysis["price_data"],
        "summary": analysis["summary"],
        "product": analysis["product"],
        "insights": analysis["insights"],
    }
