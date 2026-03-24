from typing import Annotated

# ── Polaris (primary vendor) ──
from .polaris import (
    get_stock_data as get_polaris_stock,
    get_indicators as get_polaris_indicators,
    get_fundamentals as get_polaris_fundamentals,
    get_balance_sheet as get_polaris_balance_sheet,
    get_cashflow as get_polaris_cashflow,
    get_income_statement as get_polaris_income_statement,
    get_sec_filings as get_polaris_sec_filings,
    get_news as get_polaris_news,
    get_global_news as get_polaris_global_news,
    get_sentiment_score as get_polaris_sentiment_score,
    get_sector_analysis as get_polaris_sector_analysis,
    get_news_impact as get_polaris_news_impact,
    get_technicals as get_polaris_technicals,
)

# ── yfinance (supplementary — options, analyst consensus, insider transactions) ──
from .y_finance import (
    get_YFin_data_online,
    get_stock_stats_indicators_window,
    get_fundamentals as get_yfinance_fundamentals,
    get_balance_sheet as get_yfinance_balance_sheet,
    get_cashflow as get_yfinance_cashflow,
    get_income_statement as get_yfinance_income_statement,
    get_insider_transactions as get_yfinance_insider_transactions,
)
from .yfinance_news import get_news_yfinance, get_global_news_yfinance

# Configuration and routing logic
from .config import get_config

# Tools organized by category
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": [
            "get_stock_data",
        ],
    },
    "technical_indicators": {
        "description": "Technical analysis indicators (20 indicators + signal summary)",
        "tools": [
            "get_indicators",
            "get_technicals",
        ],
    },
    "fundamental_data": {
        "description": "Company fundamentals, financials, and SEC filings",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement",
            "get_sec_filings",
        ],
    },
    "news_data": {
        "description": "Verified intelligence briefs with confidence and bias scoring",
        "tools": [
            "get_news",
            "get_global_news",
            "get_insider_transactions",
        ],
    },
    "sentiment_analysis": {
        "description": "Polaris-exclusive: composite signals, sector analysis, news impact",
        "tools": [
            "get_sentiment_score",
            "get_sector_analysis",
            "get_news_impact",
        ],
    },
}

VENDOR_LIST = [
    "polaris",
    "yfinance",
]

# Mapping of methods to their vendor-specific implementations
# Polaris is primary for everything; yfinance is fallback + supplementary
VENDOR_METHODS = {
    # core_stock_apis
    "get_stock_data": {
        "polaris": get_polaris_stock,
        "yfinance": get_YFin_data_online,
    },
    # technical_indicators
    "get_indicators": {
        "polaris": get_polaris_indicators,
        "yfinance": get_stock_stats_indicators_window,
    },
    "get_technicals": {
        "polaris": get_polaris_technicals,
    },
    # fundamental_data
    "get_fundamentals": {
        "polaris": get_polaris_fundamentals,
        "yfinance": get_yfinance_fundamentals,
    },
    "get_balance_sheet": {
        "polaris": get_polaris_balance_sheet,
        "yfinance": get_yfinance_balance_sheet,
    },
    "get_cashflow": {
        "polaris": get_polaris_cashflow,
        "yfinance": get_yfinance_cashflow,
    },
    "get_income_statement": {
        "polaris": get_polaris_income_statement,
        "yfinance": get_yfinance_income_statement,
    },
    "get_sec_filings": {
        "polaris": get_polaris_sec_filings,
    },
    # news_data
    "get_news": {
        "polaris": get_polaris_news,
        "yfinance": get_news_yfinance,
    },
    "get_global_news": {
        "polaris": get_polaris_global_news,
        "yfinance": get_global_news_yfinance,
    },
    "get_insider_transactions": {
        "yfinance": get_yfinance_insider_transactions,
    },
    # sentiment_analysis (Polaris-exclusive)
    "get_sentiment_score": {
        "polaris": get_polaris_sentiment_score,
    },
    "get_sector_analysis": {
        "polaris": get_polaris_sector_analysis,
    },
    "get_news_impact": {
        "polaris": get_polaris_news_impact,
    },
}


def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")


def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "polaris")


def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation with fallback support."""
    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)
    primary_vendors = [v.strip() for v in vendor_config.split(',')]

    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    # Build fallback chain: primary vendors first, then remaining available vendors
    all_available_vendors = list(VENDOR_METHODS[method].keys())
    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    for vendor in fallback_vendors:
        if vendor not in VENDOR_METHODS[method]:
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl

        try:
            return impl_func(*args, **kwargs)
        except Exception as e:
            # Log and try next vendor
            continue

    raise RuntimeError(f"No available vendor for '{method}'")
