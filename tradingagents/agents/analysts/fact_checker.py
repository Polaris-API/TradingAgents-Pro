"""
Fact Checker — extracts and verifies key claims from all analyst reports.

Runs AFTER all analysts (including the Macro Analyst) but BEFORE the Bull/Bear
debate.  Uses the LLM to extract verifiable factual claims, then calls the
Polaris ``client.verify()`` endpoint to check each one.  The resulting report
lets the debate agents know which claims are supported, disputed, or
inconclusive.
"""

from langchain_core.messages import HumanMessage, SystemMessage


def create_fact_checker(llm_client):
    """Create a Fact Checker node that verifies key claims before debate.

    Args:
        llm_client: LangChain-compatible LLM used for claim extraction.

    Returns:
        A LangGraph node function that writes to state["fact_check_report"].
    """

    def fact_checker_node(state):
        ticker = state["company_of_interest"]

        # Gather all analyst reports
        reports = {
            "market": state.get("market_report", ""),
            "sentiment": state.get("sentiment_report", ""),
            "news": state.get("news_report", ""),
            "fundamentals": state.get("fundamentals_report", ""),
            "macro": state.get("macro_report", ""),
        }

        combined = "\n\n".join(
            f"=== {k.upper()} ===\n{v}" for k, v in reports.items() if v
        )

        # Step 1: Use LLM to extract verifiable claims
        extract_prompt = (
            f"Review these analyst reports about {ticker} and extract the 8-10 most "
            "important FACTUAL claims that could be verified.\n\n"
            f"REPORTS:\n{combined[:4000]}\n\n"
            "Return each claim on its own line, numbered. Only include specific, "
            "verifiable factual claims (not opinions or predictions). Example:\n"
            "1. NVIDIA GPU demand grew 40% year-over-year\n"
            "2. Data center revenue exceeded $10 billion\n"
            "3. Three major AI companies announced increased GPU orders"
        )

        messages = [SystemMessage(content=extract_prompt), HumanMessage(content=f"Extract verifiable claims about {ticker}.")]
        claims_response = llm_client.invoke(messages)
        claims_text = claims_response.content

        # Step 2: Verify each claim via Polaris
        from tradingagents.dataflows.polaris import _get_client

        client = _get_client()

        lines = [
            l.strip()
            for l in claims_text.split("\n")
            if l.strip() and l.strip()[0].isdigit()
        ]

        verification_results = []
        for line in lines[:8]:
            claim = line.lstrip("0123456789.) ").strip()
            if not claim:
                continue
            try:
                result = client.verify(claim)
                verdict = (
                    result.get("verdict", "unknown")
                    if isinstance(result, dict)
                    else "unknown"
                )
                confidence = (
                    result.get("confidence", 0)
                    if isinstance(result, dict)
                    else 0
                )
                sources = (
                    result.get("sources_checked", 0)
                    if isinstance(result, dict)
                    else 0
                )
                verification_results.append(
                    f"Claim: {claim}\n"
                    f"  Verdict: {verdict} | Confidence: {confidence} | "
                    f"Sources checked: {sources}"
                )
            except Exception as e:
                verification_results.append(
                    f"Claim: {claim}\n  Verification unavailable: {e}"
                )

        report = f"# Fact Check Report: {ticker}\n\n"
        report += f"Claims verified: {len(verification_results)}\n\n"
        report += "\n\n".join(verification_results)

        supported = sum(
            1 for r in verification_results if "supported" in r.lower()
        )
        disputed = sum(
            1
            for r in verification_results
            if "disputed" in r.lower() or "unsupported" in r.lower()
        )
        inconclusive = len(verification_results) - supported - disputed
        report += (
            f"\n\nSummary: {supported} supported, {disputed} disputed, "
            f"{inconclusive} inconclusive"
        )

        return {"fact_check_report": report}

    return fact_checker_node
