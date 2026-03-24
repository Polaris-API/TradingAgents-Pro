import functools
import time
import json

from tradingagents.agents.utils.agent_utils import build_instrument_context


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(company_name)
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # Phase 4: Pull enhanced reports from state (safe defaults)
        fact_check_report = state.get("fact_check_report", "")
        forecast_report = state.get("forecast_report", "")
        bias_report = state.get("bias_report", "")
        contradiction_report = state.get("contradiction_report", "")
        macro_report = state.get("macro_report", "")

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        # Phase 4: Build enhanced context sections
        enhanced_sections = ""
        if fact_check_report:
            enhanced_sections += f"\n\nVerified Claims Report:\n{fact_check_report}"
        if forecast_report:
            enhanced_sections += f"\n\nForward Outlook & Forecast:\n{forecast_report}"
        if bias_report:
            enhanced_sections += f"\n\nSource Bias Profile:\n{bias_report}"
        if contradiction_report:
            enhanced_sections += f"\n\nContradictions & Data Conflicts:\n{contradiction_report}"
        if macro_report:
            enhanced_sections += f"\n\nMacroeconomic Context:\n{macro_report}"

        context = {
            "role": "user",
            "content": f"Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. {instrument_context} This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.\n\nProposed Investment Plan: {investment_plan}{enhanced_sections}\n\nLeverage these insights to make an informed and strategic decision.",
        }

        messages = [
            {
                "role": "system",
                "content": f"""IMPORTANT: Start your analysis with an EXECUTIVE SUMMARY section:

## Executive Summary
**Verdict:** [BUY/HOLD/SELL] | **Confidence:** [X%] | **Top Risk:** [one line]
**Data Quality:** [avg confidence across sources] | **Sources:** [count] | **Bias:** [balanced/skewed]

This should give a trader the answer in 10 seconds. Then proceed with your detailed analysis.

You are a trading agent analyzing market data to make investment decisions. Based on your analysis, provide a specific recommendation to buy, sell, or hold. End with a firm decision and always conclude your response with 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**' to confirm your recommendation. Apply lessons from past decisions to strengthen your analysis. Here are reflections from similar situations you traded in and the lessons learned: {past_memory_str}""",
            },
            context,
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
