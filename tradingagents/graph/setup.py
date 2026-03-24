# TradingAgents/graph/setup.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.agents.utils.agent_states import AgentState

from .conditional_logic import ConditionalLogic


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        portfolio_manager_memory,
        conditional_logic: ConditionalLogic,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.portfolio_manager_memory = portfolio_manager_memory
        self.conditional_logic = conditional_logic

    def setup_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals"]
    ):
        """Set up and compile the agent workflow graph.

        Pipeline order:
            START -> Context Builder -> Macro Analyst ->
            [Market, Sentiment, News, Fundamentals Analysts] ->
            Fact Checker -> Bull/Bear Debate ->
            Bias Auditor -> Forecast Agent -> Contradiction Detector ->
            Research Manager -> Trader -> Risk Debate -> Portfolio Manager -> END

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in selected_analysts:
            analyst_nodes["market"] = create_market_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "social" in selected_analysts:
            analyst_nodes["social"] = create_social_media_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["social"] = create_msg_delete()
            tool_nodes["social"] = self.tool_nodes["social"]

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]

        if "fundamentals" in selected_analysts:
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["fundamentals"] = create_msg_delete()
            tool_nodes["fundamentals"] = self.tool_nodes["fundamentals"]

        # Create researcher and manager nodes
        bull_researcher_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        research_manager_node = create_research_manager(
            self.deep_thinking_llm, self.invest_judge_memory
        )
        trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)

        # Create risk analysis nodes
        aggressive_analyst = create_aggressive_debator(self.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        conservative_analyst = create_conservative_debator(self.quick_thinking_llm)
        portfolio_manager_node = create_portfolio_manager(
            self.deep_thinking_llm, self.portfolio_manager_memory
        )

        # Create the Context Builder node (runs first, no LLM)
        context_builder_node = create_context_builder()

        # Phase 3: Create new agent nodes
        macro_analyst_node = create_macro_analyst(self.quick_thinking_llm)
        fact_checker_node = create_fact_checker(self.quick_thinking_llm)
        bias_auditor_node = create_bias_auditor(self.quick_thinking_llm)
        forecast_agent_node = create_forecast_agent(self.quick_thinking_llm)
        contradiction_detector_node = create_contradiction_detector(self.quick_thinking_llm)

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add Context Builder as the first node
        workflow.add_node("Context Builder", context_builder_node)

        # Add Macro Analyst (runs after Context Builder, before standard analysts)
        workflow.add_node("Macro Analyst", macro_analyst_node)

        # Add standard analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        # Add Fact Checker (runs after all analysts, before debate)
        workflow.add_node("Fact Checker", fact_checker_node)

        # Add debate nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)

        # Add post-debate agents (run after debate, before Research Manager)
        workflow.add_node("Bias Auditor", bias_auditor_node)
        workflow.add_node("Forecast Agent", forecast_agent_node)
        workflow.add_node("Contradiction Detector", contradiction_detector_node)

        # Add remaining nodes
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Aggressive Analyst", aggressive_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Conservative Analyst", conservative_analyst)
        workflow.add_node("Portfolio Manager", portfolio_manager_node)

        # ---------------------------------------------------------------
        # Define edges
        # Pipeline: START -> Context Builder -> Macro Analyst -> [Analysts]
        #           -> Fact Checker -> Bull/Bear Debate
        #           -> Bias Auditor -> Forecast Agent -> Contradiction Detector
        #           -> Research Manager -> Trader -> Risk Debate
        #           -> Portfolio Manager -> END
        # ---------------------------------------------------------------

        # Start with Context Builder, then Macro Analyst, then first standard analyst
        first_analyst = selected_analysts[0]
        workflow.add_edge(START, "Context Builder")
        workflow.add_edge("Context Builder", "Macro Analyst")
        workflow.add_edge("Macro Analyst", f"{first_analyst.capitalize()} Analyst")

        # Connect standard analysts in sequence
        for i, analyst_type in enumerate(selected_analysts):
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            # Add conditional edges for current analyst
            workflow.add_conditional_edges(
                current_analyst,
                getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

            # Connect to next analyst or to Fact Checker if this is the last analyst
            if i < len(selected_analysts) - 1:
                next_analyst = f"{selected_analysts[i+1].capitalize()} Analyst"
                workflow.add_edge(current_clear, next_analyst)
            else:
                workflow.add_edge(current_clear, "Fact Checker")

        # Fact Checker -> Bull/Bear Debate
        workflow.add_edge("Fact Checker", "Bull Researcher")

        # Bull/Bear debate loop
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Bias Auditor",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Bias Auditor",
            },
        )

        # Post-debate chain: Bias Auditor -> Forecast Agent -> Contradiction Detector -> Research Manager
        workflow.add_edge("Bias Auditor", "Forecast Agent")
        workflow.add_edge("Forecast Agent", "Contradiction Detector")
        workflow.add_edge("Contradiction Detector", "Research Manager")

        # Research Manager -> Trader -> Risk Debate -> Portfolio Manager -> END
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Aggressive Analyst")
        workflow.add_conditional_edges(
            "Aggressive Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Conservative Analyst": "Conservative Analyst",
                "Portfolio Manager": "Portfolio Manager",
            },
        )
        workflow.add_conditional_edges(
            "Conservative Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Portfolio Manager": "Portfolio Manager",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Aggressive Analyst": "Aggressive Analyst",
                "Portfolio Manager": "Portfolio Manager",
            },
        )

        workflow.add_edge("Portfolio Manager", END)

        # Compile and return
        return workflow.compile()
