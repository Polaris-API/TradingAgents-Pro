"""
Forecast Agent — generates forward-looking predictions with invalidation criteria.

Calls the Polaris ``client.forecast()`` endpoint for external forecast data,
then synthesizes it with all prior analysis to produce structured predictions,
signals to watch, wildcards, and specific invalidation criteria.

Runs AFTER the Bias Auditor and BEFORE the Contradiction Detector.
"""


def create_forecast_agent(llm_client):
    """Create a Forecast Agent node that generates forward-looking predictions.

    Args:
        llm_client: LangChain-compatible LLM used for forecast synthesis.

    Returns:
        A LangGraph node function that writes to state["forecast_report"].
    """

    def forecast_agent_node(state):
        ticker = state["company_of_interest"]

        # Get forecast from Polaris
        from tradingagents.dataflows.polaris import _get_client

        client = _get_client()

        forecast_data = ""
        try:
            result = client.forecast(f"{ticker} stock", depth="standard")
            if isinstance(result, dict):
                forecast_data = str(result)
            else:
                forecast_data = str(result)
        except Exception as e:
            forecast_data = f"Forecast unavailable: {e}"

        # Gather all prior analysis
        context = state.get("verified_context", "")
        market = state.get("market_report", "")
        macro = state.get("macro_report", "")
        fact_check = state.get("fact_check_report", "")

        system_prompt = (
            f"You are a forward-looking forecast analyst for {ticker}. Using all "
            "available analysis and the Polaris forecast data, produce a structured "
            "forward outlook.\n\n"
            f"POLARIS FORECAST DATA:\n{forecast_data[:2000]}\n\n"
            f"VERIFIED CONTEXT:\n{context[:2000]}\n\n"
            f"MARKET ANALYSIS:\n{market[:1000]}\n\n"
            f"MACRO ANALYSIS:\n{macro[:1000]}\n\n"
            f"FACT CHECK RESULTS:\n{fact_check[:1000]}\n\n"
            "Produce a forecast report with these exact sections:\n\n"
            "## Predictions (ranked by confidence)\n"
            "List 3-5 predictions, each with:\n"
            "- Prediction statement\n"
            "- Confidence level (HIGH/MEDIUM/LOW with percentage)\n"
            "- Timeframe\n"
            "- Key evidence\n\n"
            "## Signals to Watch\n"
            "List 3-5 specific, measurable signals that would confirm or deny "
            "the predictions.\n\n"
            "## Wildcards\n"
            "List 2-3 low-probability, high-impact scenarios.\n\n"
            "## Invalidation Criteria\n"
            "List 3-5 specific conditions under which this entire analysis would "
            "be WRONG. These should be measurable and specific (e.g., "
            '"RSI breaks below 25", "Revenue misses by >10%").\n\n'
            "Be specific with numbers and timeframes. Every prediction needs a "
            "confidence level."
        )

        messages = [{"role": "system", "content": system_prompt}]
        response = llm_client.invoke(messages)

        return {"forecast_report": response.content}

    return forecast_agent_node
