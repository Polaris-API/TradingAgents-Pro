# TradingAgents/graph/signal_processing.py

from langchain_openai import ChatOpenAI

from tradingagents.output.formatter import format_pro_report


class SignalProcessor:
    """Processes trading signals to extract actionable decisions."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Initialize with an LLM for processing."""
        self.quick_thinking_llm = quick_thinking_llm

    def process_signal(self, full_signal: str) -> str:
        """
        Process a full trading signal to extract the core decision.

        Args:
            full_signal: Complete trading signal text

        Returns:
            Extracted rating (BUY, OVERWEIGHT, HOLD, UNDERWEIGHT, or SELL)
        """
        messages = [
            (
                "system",
                "You are an efficient assistant that extracts the trading decision from analyst reports. "
                "Extract the rating as exactly one of: BUY, OVERWEIGHT, HOLD, UNDERWEIGHT, SELL. "
                "Output only the single rating word, nothing else.",
            ),
            ("human", full_signal),
        ]

        return self.quick_thinking_llm.invoke(messages).content

    def format_report(self, final_state: dict) -> str:
        """
        Generate the full TradingAgents-Pro markdown report from the final state.

        Args:
            final_state: Complete LangGraph AgentState after graph execution.

        Returns:
            Formatted markdown report string.
        """
        return format_pro_report(final_state)
