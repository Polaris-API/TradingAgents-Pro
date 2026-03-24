import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low"
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration — Polaris is the primary vendor
    # yfinance kept as supplementary for options, analyst consensus, institutional holdings
    "data_vendors": {
        "core_stock_apis": "polaris",            # Polaris multi-provider (Yahoo/TwelveData/FMP)
        "technical_indicators": "polaris",       # 20 indicators + signal summary
        "fundamental_data": "polaris",           # Full financials in one call
        "news_data": "polaris",                  # Confidence-scored, bias-analyzed briefs
        "sentiment_analysis": "polaris",         # Polaris-exclusive: composite signals, sector analysis, news impact
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # yfinance supplementary — data Polaris doesn't have yet
        "get_insider_transactions": "yfinance",  # Form 4 insider trades
    },
}
