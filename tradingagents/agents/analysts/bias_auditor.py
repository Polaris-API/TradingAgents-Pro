"""
Bias Auditor — analyzes source distribution and framing across all briefs.

This is an LLM-only agent (no API calls).  It runs AFTER the Bull/Bear debate
and BEFORE the Research Manager so that the manager can factor source-bias
awareness into the final recommendation.
"""


def create_bias_auditor(llm_client):
    """Create a Bias Auditor node that audits source distribution and bias.

    Args:
        llm_client: LangChain-compatible LLM used for bias analysis.

    Returns:
        A LangGraph node function that writes to state["bias_report"].
    """

    def bias_auditor_node(state):
        ticker = state["company_of_interest"]
        verified_context = state.get("verified_context", "")
        news_report = state.get("news_report", "")

        system_prompt = (
            f"You are a bias auditor. Analyze the sources used in this {ticker} "
            "analysis for bias and framing.\n\n"
            "VERIFIED CONTEXT (contains source data):\n"
            f"{verified_context[:3000]}\n\n"
            "NEWS ANALYST REPORT:\n"
            f"{news_report[:2000]}\n\n"
            "Produce a bias audit report:\n"
            "1. Source count and distribution (how many sources, which outlets)\n"
            "2. Political/ideological lean distribution (center, center-left, "
            "center-right, etc.)\n"
            "3. Any framing divergences (same event described differently by "
            "different outlets)\n"
            "4. Potential blind spots (perspectives not represented)\n"
            "5. Overall bias assessment: BALANCED, SLIGHT SKEW, or SIGNIFICANT SKEW\n"
            "6. Recommendation: any additional sources that should be consulted\n\n"
            "Be objective and specific. Reference actual sources from the data."
        )

        messages = [{"role": "system", "content": system_prompt}]
        response = llm_client.invoke(messages)

        return {"bias_report": response.content}

    return bias_auditor_node
