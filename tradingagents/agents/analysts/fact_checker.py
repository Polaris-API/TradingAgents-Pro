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
            "important FACTUAL claims that could be verified against news sources.\n\n"
            f"REPORTS:\n{combined[:4000]}\n\n"
            "IMPORTANT: Only extract NEWS and BUSINESS claims — things that would appear "
            "in Reuters, Bloomberg, or financial news articles. DO NOT extract:\n"
            "- Technical indicator values (RSI, MACD, SMA, Bollinger Bands, etc.)\n"
            "- Stock price levels or trading volumes\n"
            "- Mathematical calculations or ratios\n\n"
            "Focus on claims like partnerships, product launches, earnings results, "
            "strategic decisions, market events, and competitive developments.\n\n"
            "Return each claim on its own line, numbered. Example:\n"
            "1. NVIDIA partnered with Roche to build an AI-powered drug discovery platform\n"
            "2. NVIDIA launched a security platform with CrowdStrike and Palo Alto Networks\n"
            "3. Micron CEO reported inability to meet memory demand\n"
            "4. NVIDIA revenue grew 73% year-over-year to $68 billion\n"
            "5. AWS announced partnership with Cerebras for AI chips"
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
            if l.strip() and len(l.strip()) > 20  # Skip short/empty lines
            and not l.strip().startswith('#')       # Skip markdown headers
            and not l.strip().lower().startswith('note')  # Skip explanatory notes
            and not l.strip().lower().startswith('based on')  # Skip preambles
            and 'verifiable' not in l.lower()       # Skip meta-commentary
            and 'technical indicator' not in l.lower()  # Skip tech indicator mentions
        ]

        verification_results = []
        for line in lines[:8]:
            claim = line.lstrip("0123456789.)-•* ").strip()
            if not claim:
                continue
            try:
                result = client.verify(claim)
                # Handle both dict and typed response objects
                if isinstance(result, dict):
                    verdict = result.get("verdict", "unknown")
                    confidence = result.get("confidence", 0)
                    sources = result.get("sources_analyzed", result.get("sources_checked", 0))
                else:
                    verdict = getattr(result, "verdict", "unknown")
                    confidence = getattr(result, "confidence", 0)
                    sources = getattr(result, "sources_analyzed", getattr(result, "sources_checked", 0))
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
