"""Tests for VeroQ Fact Checker — automatic verification layer."""

import pytest
import sys
import os
import types

# Stub the agents package to avoid langchain imports but allow submodule discovery
_agents_dir = os.path.join(os.path.dirname(__file__), "..", "tradingagents", "agents")
agents_stub = types.ModuleType("tradingagents.agents")
agents_stub.__path__ = [os.path.abspath(_agents_dir)]
agents_stub.__package__ = "tradingagents.agents"
sys.modules["tradingagents.agents"] = agents_stub

from tradingagents.agents.veroq_fact_checker import (  # noqa: E402
    VeroQFactChecker,
    FactCheckResult,
    format_verification,
)
from tradingagents.coordinator import (  # noqa: E402
    startVeroQTeam,
    VerificationMetadata,
)


@pytest.fixture
def checker():
    """Fact checker with verification disabled (no API calls)."""
    return VeroQFactChecker(api_key=None)


class TestFactCheckDetection:
    def test_detects_ticker_claims(self, checker):
        result = checker.check("NVDA is trading at $167 with strong momentum")
        assert result.needs_check is True

    def test_detects_signal_claims(self, checker):
        result = checker.check("The stock looks bullish with oversold RSI")
        assert result.needs_check is True

    def test_detects_market_claims(self, checker):
        result = checker.check("Revenue grew 15% and EPS beat by $0.20")
        assert result.needs_check is True

    def test_ignores_non_financial(self, checker):
        result = checker.check("The weather is nice today")
        assert result.needs_check is False
        assert result.metadata is None

    def test_ignores_empty_text(self, checker):
        result = checker.check("")
        assert result.needs_check is False


class TestFactCheckFormatting:
    def test_format_verified(self):
        meta = VerificationMetadata(
            confidence_score=85,
            evidence_chain=[
                {"source": "Reuters", "position": "supports", "reliability": 0.95, "snippet": "NVDA beat earnings"},
            ],
            verification_status="verified",
            prompt_hint="Verdict: supported",
        )
        output = format_verification("NVDA beat Q4 earnings", meta)
        assert "[✓ VERIFIED]" in output
        assert "85/100" in output
        assert "Reuters" in output
        assert "NVDA beat earnings" in output

    def test_format_flagged(self):
        meta = VerificationMetadata(
            confidence_score=45,
            evidence_chain=[],
            verification_status="flagged",
            prompt_hint="Verdict: contradicted",
        )
        output = format_verification("Some claim", meta)
        assert "[⚠ FLAGGED]" in output
        assert "45/100" in output

    def test_format_low_confidence(self):
        meta = VerificationMetadata(
            confidence_score=25,
            evidence_chain=[],
            verification_status="low-confidence",
            prompt_hint="Treat with caution",
        )
        output = format_verification("Unverified claim", meta)
        assert "[? LOW CONFIDENCE]" in output
        assert "⚠ LOW CONFIDENCE" in output  # warning footer


class TestFactCheckAgentOutput:
    def test_check_agent_output_structure(self, checker):
        result = checker.check_agent_output(
            agent_name="Bull Analyst",
            role="bull_analyst",
            output="NVDA trades at $167 with bullish momentum",
        )
        assert result["agent"] == "Bull Analyst"
        assert result["role"] == "bull_analyst"
        assert result["fact_checked"] is True
        assert "formatted" in result

    def test_check_agent_output_no_check_needed(self, checker):
        result = checker.check_agent_output(
            agent_name="CIO",
            role="cio",
            output="Thank you for the analysis team",
        )
        assert result["fact_checked"] is False
        assert result["verification"] is None


class TestFactCheckSummary:
    def test_summary_empty(self, checker):
        summary = checker.get_summary()
        assert summary["total_outputs_seen"] == 0
        assert summary["total_checked"] == 0
        assert summary["all_verified"] is True

    def test_summary_after_checks(self, checker):
        checker.check("NVDA is bullish at $167")
        checker.check("The weather is nice")
        checker.check("Revenue grew 20% with strong earnings")
        summary = checker.get_summary()
        assert summary["total_outputs_seen"] == 3
        assert summary["total_checked"] == 2  # 2 financial, 1 non-financial


class TestFactCheckerInTeam:
    def test_team_has_fact_checker_when_enabled(self):
        team = startVeroQTeam({
            "agents": [{"name": "A", "role": "cio"}],
            "enableAutoVerification": True,
        })
        assert team.fact_checker is not None

    def test_team_no_fact_checker_when_disabled(self):
        team = startVeroQTeam({
            "agents": [{"name": "A", "role": "cio"}],
            "enableAutoVerification": False,
        })
        assert team.fact_checker is None

    def test_full_workflow_with_fact_checker(self):
        """Run full workflow and verify fact checker is invoked."""
        team = startVeroQTeam({
            "agents": [
                {"name": "Tech", "role": "technical_analyst"},
                {"name": "Sent", "role": "sentiment_analyst"},
                {"name": "Bull", "role": "bull_analyst"},
                {"name": "Bear", "role": "bear_analyst"},
                {"name": "FC", "role": "fact_checker"},
                {"name": "Risk", "role": "risk_manager"},
                {"name": "CIO", "role": "cio"},
            ],
            "enableAutoVerification": True,
        })
        result = team.run("Analyze NVDA")

        # Fact checker should have processed outputs
        assert team.fact_checker is not None
        summary = team.fact_checker.get_summary()
        assert summary["total_outputs_seen"] > 0

        # Result should have formatted outputs
        for phase in result["phases"]:
            for output in phase["outputs"]:
                assert "formatted" in output

        # Should have verification summary with fact_checker stats
        vs = result.get("verification_summary")
        assert vs is not None
        assert "fact_checker" in vs

    def test_workflow_outputs_include_formatted(self):
        team = startVeroQTeam({
            "agents": [
                {"name": "Bull", "role": "bull_analyst"},
                {"name": "CIO", "role": "cio"},
            ],
            "enableAutoVerification": True,
        })
        result = team.run("Should I buy AAPL?")

        for phase in result["phases"]:
            for output in phase["outputs"]:
                # Every output should have a formatted field
                assert "formatted" in output
                # Formatted should not be empty
                assert len(output["formatted"]) > 0
