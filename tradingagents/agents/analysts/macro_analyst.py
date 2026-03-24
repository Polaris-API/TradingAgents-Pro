"""
Macro Analyst — assesses the macroeconomic environment and its implications.

This is an LLM agent that fetches macro data directly from Polaris (economy,
yields, market summary) and then uses the LLM to produce a structured macro
assessment.  It runs AFTER the Context Builder and BEFORE the four standard
analysts so that its report is available during the Bull/Bear debate.
"""


def create_macro_analyst(llm_client):
    """Create a Macro Analyst node that assesses macroeconomic conditions.

    Args:
        llm_client: LangChain-compatible LLM used for analysis.

    Returns:
        A LangGraph node function that writes to state["macro_report"].
    """

    def macro_analyst_node(state):
        ticker = state["company_of_interest"]

        # Fetch macro data directly from Polaris
        from tradingagents.dataflows.polaris import _get_client

        client = _get_client()

        macro_parts = []
        try:
            economy = client.economy()
            macro_parts.append(f"Economic Indicators:\n{economy}")
        except Exception:
            pass
        try:
            yields = client.economy_yields()
            macro_parts.append(f"Yield Curve:\n{yields}")
        except Exception:
            pass
        try:
            summary = client.market_summary()
            macro_parts.append(f"Market Summary:\n{summary}")
        except Exception:
            pass

        macro_data = "\n\n".join(macro_parts) if macro_parts else "Macro data unavailable."

        system_prompt = (
            f"You are a macroeconomic analyst. Assess the current macro environment "
            f"and its implications for {ticker}.\n\n"
            f"MACRO DATA:\n{macro_data}\n\n"
            f"VERIFIED CONTEXT:\n{state.get('verified_context', 'Not available')}\n\n"
            "Produce a macro report covering:\n"
            "1. Market regime (bull/bear/neutral) with evidence\n"
            "2. Interest rate environment and implications\n"
            "3. Sector rotation signals\n"
            "4. Key risks (recession, inflation, geopolitical)\n"
            f"5. How the macro environment specifically affects {ticker}\n"
            "6. Overall macro verdict: FAVORABLE, NEUTRAL, or UNFAVORABLE for this trade\n\n"
            "Be specific with numbers. Reference the data provided."
        )

        messages = [{"role": "system", "content": system_prompt}]
        response = llm_client.invoke(messages)

        return {"macro_report": response.content}

    return macro_analyst_node
