from langchain_core.messages import HumanMessage, SystemMessage
"""
Contradiction Detector — scans all reports for conflicting facts.

This is an LLM-only agent (no API calls).  It gathers every report produced so
far and asks the LLM to identify conflicting statements, inconsistent data, and
single-source claims that lack corroboration.

Runs AFTER the Forecast Agent and BEFORE the Research Manager, so the manager
can weigh data-consistency when making the final recommendation.
"""


def create_contradiction_detector(llm_client):
    """Create a Contradiction Detector node that finds conflicting facts.

    Args:
        llm_client: LangChain-compatible LLM used for contradiction analysis.

    Returns:
        A LangGraph node function that writes to state["contradiction_report"].
    """

    def contradiction_detector_node(state):
        ticker = state["company_of_interest"]

        # Gather ALL reports
        reports = {
            "verified_context": state.get("verified_context", "")[:2000],
            "market": state.get("market_report", "")[:1000],
            "sentiment": state.get("sentiment_report", "")[:1000],
            "news": state.get("news_report", "")[:1000],
            "fundamentals": state.get("fundamentals_report", "")[:1000],
            "macro": state.get("macro_report", "")[:1000],
            "fact_check": state.get("fact_check_report", "")[:1000],
        }

        combined = "\n\n".join(
            f"=== {k.upper()} ===\n{v}" for k, v in reports.items() if v
        )

        system_prompt = (
            f"You are a contradiction detector. Review ALL analysis reports for "
            f"{ticker} and identify any conflicting facts, inconsistent data, or "
            "disagreements between sources.\n\n"
            f"REPORTS:\n{combined}\n\n"
            "For each contradiction found, report:\n"
            "1. The conflicting statements (quote both)\n"
            "2. Which reports contain them\n"
            "3. Which is more likely correct (and why)\n"
            "4. Severity: CRITICAL (affects trade decision), MODERATE (notable), "
            "or MINOR (cosmetic)\n\n"
            "If no contradictions are found, state that clearly.\n\n"
            "Also flag any claims that appear in only one source with no "
            "corroboration -- these are unverified single-source claims and "
            "should be noted.\n\n"
            "End with a summary: number of contradictions found, number critical, "
            "and overall data consistency assessment (HIGH/MEDIUM/LOW)."
        )

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=f"Analyze {ticker} now.")]
        response = llm_client.invoke(messages)

        return {"contradiction_report": response.content}

    return contradiction_detector_node
