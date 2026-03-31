"""Tests for VeroQ Agent Coordinator."""

import pytest
from tradingagents.coordinator import (
    startVeroQTeam,
    addAgentToTeam,
    sendMessageBetweenAgents,
    createTask,
    updateTask,
    listTasks,
    stopTask,
    VeroQTeam,
    TaskStatus,
)


@pytest.fixture
def team():
    """Create a basic 4-agent team with verification disabled (no API calls)."""
    return startVeroQTeam({
        "agents": [
            {"name": "Bull", "role": "bull_analyst"},
            {"name": "Bear", "role": "bear_analyst"},
            {"name": "Risk", "role": "risk_manager"},
            {"name": "CIO", "role": "cio"},
        ],
        "enableAutoVerification": False,
    })


@pytest.fixture
def full_team():
    """Create a full team with all standard roles."""
    return startVeroQTeam({
        "agents": [
            {"name": "Tech", "role": "technical_analyst"},
            {"name": "Sentiment", "role": "sentiment_analyst"},
            {"name": "Bull", "role": "bull_analyst"},
            {"name": "Bear", "role": "bear_analyst"},
            {"name": "Fact Check", "role": "fact_checker"},
            {"name": "Risk", "role": "risk_manager"},
            {"name": "CIO", "role": "cio"},
        ],
        "enableAutoVerification": False,
    })


class TestTeamCreation:
    def test_start_team(self, team):
        assert isinstance(team, VeroQTeam)
        assert len(team.agents) == 4

    def test_agents_by_role(self, team):
        assert "bull_analyst" in team.agents_by_role
        assert "cio" in team.agents_by_role

    def test_add_agent(self, team):
        new = addAgentToTeam(team, {"name": "Fact Checker", "role": "fact_checker"})
        assert new.name == "Fact Checker"
        assert new.role == "fact_checker"
        assert len(team.agents) == 5

    def test_initial_memory(self):
        team = startVeroQTeam({
            "agents": [{"name": "A", "role": "cio", "initialMemory": {"context": "tech sector"}}],
            "enableAutoVerification": False,
        })
        agent = list(team.agents.values())[0]
        assert team.memory[agent.id]["context"] == "tech sector"


class TestMessaging:
    def test_send_message(self, team):
        ids = list(team.agents.keys())
        msg = sendMessageBetweenAgents(team, ids[0], ids[1], "NVDA looks bullish")
        assert msg.from_agent == ids[0]
        assert msg.to_agent == ids[1]
        assert msg.content == "NVDA looks bullish"
        assert len(team.messages) == 1

    def test_message_stored_in_memory(self, team):
        ids = list(team.agents.keys())
        sendMessageBetweenAgents(team, ids[0], ids[1], "Buy signal on AAPL")
        inbox = team.memory[ids[1]].get("inbox", [])
        assert len(inbox) == 1
        assert inbox[0]["from"] == ids[0]

    def test_no_verification_when_disabled(self, team):
        ids = list(team.agents.keys())
        msg = sendMessageBetweenAgents(team, ids[0], ids[1], "NVDA earnings beat by 20%")
        assert msg.verification is None  # Auto-verification disabled


class TestTasks:
    def test_create_task(self, team):
        agent_id = list(team.agents.keys())[0]
        task = createTask(team, "Analyze NVDA technicals", agent_id)
        assert task.status == TaskStatus.PENDING
        assert task.description == "Analyze NVDA technicals"

    def test_update_task(self, team):
        agent_id = list(team.agents.keys())[0]
        task = createTask(team, "Test", agent_id)
        updated = updateTask(team, task.id, "complete", result="Done")
        assert updated.status == TaskStatus.COMPLETE
        assert updated.result == "Done"
        assert updated.completed_at is not None

    def test_list_tasks(self, team):
        agent_id = list(team.agents.keys())[0]
        createTask(team, "Task 1", agent_id)
        createTask(team, "Task 2", agent_id)
        assert len(listTasks(team)) == 2

    def test_list_tasks_by_status(self, team):
        agent_id = list(team.agents.keys())[0]
        t1 = createTask(team, "Task 1", agent_id)
        createTask(team, "Task 2", agent_id)
        updateTask(team, t1.id, "complete")
        assert len(listTasks(team, "complete")) == 1
        assert len(listTasks(team, "pending")) == 1

    def test_stop_task(self, team):
        agent_id = list(team.agents.keys())[0]
        task = createTask(team, "Task", agent_id)
        stopped = stopTask(team, task.id)
        assert stopped.status == TaskStatus.STOPPED


class TestWorkflow:
    def test_run_produces_result(self, full_team):
        result = full_team.run("Analyze NVDA for a potential long position")
        assert "query" in result
        assert result["query"] == "Analyze NVDA for a potential long position"
        assert "phases" in result
        assert len(result["phases"]) > 0
        assert "duration_seconds" in result

    def test_run_has_all_phases(self, full_team):
        result = full_team.run("Should I buy AAPL?")
        phase_names = [p["phase"] for p in result["phases"]]
        assert "gather" in phase_names
        assert "debate" in phase_names
        assert "verify" in phase_names
        assert "assess" in phase_names
        assert "decide" in phase_names

    def test_run_produces_final_decision(self, full_team):
        result = full_team.run("TSLA analysis")
        assert result["final_decision"] is not None
        assert result["final_decision"]["role"] == "cio"

    def test_run_tracks_tasks(self, full_team):
        result = full_team.run("BTC analysis")
        assert result["tasks_total"] > 0
        assert result["tasks_completed"] > 0

    def test_stop_team(self, full_team):
        full_team.stop()
        assert full_team._running is False

    def test_no_verification_summary_when_disabled(self, full_team):
        result = full_team.run("Test query")
        # With verification disabled, no verification metadata
        assert result["verification_summary"] is None


class TestVerificationDetection:
    """Test that _needs_verification correctly identifies financial content."""

    def test_detects_tickers(self):
        from tradingagents.coordinator.veroq_agent_coordinator import _needs_verification
        assert _needs_verification("NVDA is trading at $167")
        assert _needs_verification("Buy AAPL and MSFT")

    def test_detects_signals(self):
        from tradingagents.coordinator.veroq_agent_coordinator import _needs_verification
        assert _needs_verification("The stock looks bullish")
        assert _needs_verification("I would sell here")
        assert _needs_verification("RSI shows oversold conditions")

    def test_detects_market_claims(self):
        from tradingagents.coordinator.veroq_agent_coordinator import _needs_verification
        assert _needs_verification("Revenue grew 15% year over year")
        assert _needs_verification("Market cap exceeded $3 billion")
        assert _needs_verification("EPS of $2.50 beats consensus")

    def test_ignores_generic_text(self):
        from tradingagents.coordinator.veroq_agent_coordinator import _needs_verification
        assert not _needs_verification("Hello, how are you today?")
        assert not _needs_verification("The weather is nice")
