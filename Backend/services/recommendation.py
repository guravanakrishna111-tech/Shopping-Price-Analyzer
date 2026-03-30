from services.market_intelligence import get_analysis_bundle


def get_recommendations(product_name, platform=None, limit=6):
    analysis = get_analysis_bundle(product_name, platform)
    return analysis["recommendations"][:limit]
