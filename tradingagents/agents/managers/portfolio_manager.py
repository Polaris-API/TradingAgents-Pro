from tradingagents.agents.utils.agent_utils import build_instrument_context


def create_portfolio_manager(llm, memory):
    def portfolio_manager_node(state) -> dict:

        instrument_context = build_instrument_context(state["company_of_interest"])

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

        # Phase 4: Pull enhanced reports from state (safe defaults)
        fact_check_report = state.get("fact_check_report", "")
        forecast_report = state.get("forecast_report", "")
        bias_report = state.get("bias_report", "")
        contradiction_report = state.get("contradiction_report", "")
        macro_report = state.get("macro_report", "")

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # Phase 4: Build enhanced context sections for the prompt
        enhanced_context = ""
        if fact_check_report:
            enhanced_context += f"\n\n**Fact Check Report (Verified Claims):**\n{fact_check_report}"
        if forecast_report:
            enhanced_context += f"\n\n**Forecast Report (Forward Outlook):**\n{forecast_report}"
        if bias_report:
            enhanced_context += f"\n\n**Bias Audit Report:**\n{bias_report}"
        if contradiction_report:
            enhanced_context += f"\n\n**Contradiction Report:**\n{contradiction_report}"
        if macro_report:
            enhanced_context += f"\n\n**Macro Context Report:**\n{macro_report}"

        prompt = f"""As the Portfolio Manager, synthesize the risk analysts' debate and deliver the final trading decision.

{instrument_context}

---

**Rating Scale** (use exactly one):
- **Buy**: Strong conviction to enter or add to position
- **Overweight**: Favorable outlook, gradually increase exposure
- **Hold**: Maintain current position, no action needed
- **Underweight**: Reduce exposure, take partial profits
- **Sell**: Exit position or avoid entry

**Context:**
- Trader's proposed plan: **{trader_plan}**
- Lessons from past decisions: **{past_memory_str}**
{enhanced_context}

**Required Output Structure:**
1. **Rating**: State one of Buy / Overweight / Hold / Underweight / Sell.
2. **Executive Summary**: A concise action plan covering entry strategy, position sizing, key risk levels, and time horizon.
3. **Investment Thesis**: Detailed reasoning anchored in the analysts' debate and past reflections.

In addition to your investment decision, include these sections in your final report:

## Confidence Dashboard
- Sources consulted: [number]
- Average confidence: [X.XX]
- Verified claims: [X/Y supported]
- Contradictions: [count, severity]
- Bias distribution: [summary]

## Verified Claims
[Table of key claims with verdict and confidence from the fact check report]

## Forward Outlook
[Key predictions from forecast report with confidence levels and timeframes]

## What Invalidates This Trade
[Specific conditions from forecast invalidation criteria]

## Signals to Watch
[From forecast wildcards and key signals]

## Macro Context
[Key macro findings and their impact on this trade]

If any of these reports are empty or unavailable, note "Data not available" for that section.

---

**Risk Analysts Debate History:**
{history}

---

Be decisive and ground every conclusion in specific evidence from the analysts."""

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response.content,
        }

    return portfolio_manager_node
