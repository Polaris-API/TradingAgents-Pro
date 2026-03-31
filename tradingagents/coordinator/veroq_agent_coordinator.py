"""
VeroQ Agent Coordinator — Lightweight coordination layer for verified trading workflows.

Connects multi-agent teams to the VeroQ verification system. When agents produce outputs
containing tickers, signals, sentiment, or market claims, the coordinator routes them
through VeroQ for automatic verification with evidence chains and confidence scores.

Usage:
    from tradingagents.coordinator import startVeroQTeam

    team = startVeroQTeam({
        "agents": [
            {"name": "Bull Analyst", "role": "bull_analyst"},
            {"name": "Bear Analyst", "role": "bear_analyst"},
            {"name": "Risk Manager", "role": "risk_manager"},
            {"name": "CIO", "role": "cio"},
        ],
        "enableAutoVerification": True,
    })

    result = team.run("Analyze NVDA for a potential long position")
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# ── Types ──


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class AgentConfig:
    name: str
    role: str
    initial_memory: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class TaskConfig:
    id: str
    description: str
    assigned_to: str  # agent id
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str | None = None


@dataclass
class VerificationMetadata:
    confidence_score: int  # 0-100
    evidence_chain: list[dict[str, Any]]
    verification_status: str  # "verified" | "flagged" | "low-confidence"
    prompt_hint: str


@dataclass
class AgentMessage:
    from_agent: str
    to_agent: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    verification: VerificationMetadata | None = None


# ── Verification Patterns ──

# Patterns that trigger auto-verification
TICKER_PATTERN = re.compile(r"\b[A-Z]{1,5}\b")
SIGNAL_KEYWORDS = {
    "buy", "sell", "hold", "bullish", "bearish", "oversold", "overbought",
    "support", "resistance", "breakout", "breakdown", "rally", "crash",
    "upgrade", "downgrade", "beat", "miss", "guidance",
}
SENTIMENT_KEYWORDS = {
    "sentiment", "confidence", "momentum", "fear", "greed", "optimistic",
    "pessimistic", "cautious", "aggressive",
}
MARKET_CLAIM_PATTERN = re.compile(
    r"\b(?:revenue|earnings|EPS|price target|market cap|PE ratio|"
    r"dividend|yield|growth|decline|increase|decrease|billion|million|"
    r"percent|%|\$\d)"
)

# Common non-ticker words that look like tickers
NOT_TICKERS = {
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HAS",
    "WAS", "ONE", "OUR", "OUT", "DAY", "GET", "HOW", "ITS", "MAY", "NEW",
    "NOW", "OLD", "SEE", "WAY", "WHO", "DID", "GOT", "LET", "SAY", "SHE",
    "TOO", "USE", "ANY", "BIG", "LOW", "TOP", "BUY", "IPO", "CEO", "CFO",
    "GDP", "CPI", "RSI", "EPS", "ETF", "SEC", "AI", "IS", "IN", "ON", "UP",
}


def _needs_verification(text: str) -> bool:
    """Check if text contains tickers, signals, sentiment or market claims."""
    words = set(text.upper().split())

    # Check for ticker symbols (2-5 uppercase letters, not common words)
    tickers = TICKER_PATTERN.findall(text)
    has_tickers = any(t not in NOT_TICKERS and len(t) >= 2 for t in tickers)

    # Check for signal keywords
    lower_words = set(text.lower().split())
    has_signals = bool(lower_words & SIGNAL_KEYWORDS)
    has_sentiment = bool(lower_words & SENTIMENT_KEYWORDS)

    # Check for market claims (numbers, percentages, financial terms)
    has_claims = bool(MARKET_CLAIM_PATTERN.search(text))

    return has_tickers or has_signals or has_sentiment or has_claims


def _verify_with_veroq(
    text: str,
    endpoint: str = "https://api.veroq.ai",
    api_key: str | None = None,
) -> VerificationMetadata:
    """Route text through VeroQ /verify for verification metadata."""
    import urllib.request
    import urllib.error

    key = api_key or os.environ.get("VEROQ_API_KEY") or os.environ.get("POLARIS_API_KEY")
    if not key:
        return VerificationMetadata(
            confidence_score=50,
            evidence_chain=[],
            verification_status="low-confidence",
            prompt_hint="No VEROQ_API_KEY set — verification skipped. Set the key for auto-verification.",
        )

    # Extract the most verifiable claim from the text (first sentence with financial content)
    sentences = re.split(r"[.!?\n]", text)
    claim = next(
        (s.strip() for s in sentences if _needs_verification(s) and len(s.strip()) > 15),
        text[:200],
    )

    try:
        req = urllib.request.Request(
            f"{endpoint}/api/v1/verify",
            data=json.dumps({"claim": claim}).encode(),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": key,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        confidence = data.get("confidence", 0)
        confidence_score = round(confidence * 100)
        verdict = data.get("verdict", "unverifiable")
        chain = data.get("evidence_chain", [])
        breakdown = data.get("confidence_breakdown", {})

        status = "verified"
        if verdict in ("unverifiable", "contradicted"):
            status = "flagged"
        if confidence_score < 40:
            status = "low-confidence"

        evidence = [
            {
                "source": e.get("source", "Unknown"),
                "snippet": e.get("snippet", ""),
                "url": e.get("url"),
                "position": e.get("position"),
                "reliability": e.get("reliability"),
                "timestamp": datetime.utcnow().isoformat(),
            }
            for e in chain[:10]
        ]

        hint = f"Verdict: {verdict}. "
        if breakdown:
            hint += (
                f"Agreement: {breakdown.get('source_agreement', '?')}, "
                f"Quality: {breakdown.get('source_quality', '?')}, "
                f"Recency: {breakdown.get('recency', '?')}, "
                f"Corroboration: {breakdown.get('corroboration_depth', '?')}"
            )

        return VerificationMetadata(
            confidence_score=confidence_score,
            evidence_chain=evidence,
            verification_status=status,
            prompt_hint=hint,
        )

    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        return VerificationMetadata(
            confidence_score=30,
            evidence_chain=[],
            verification_status="low-confidence",
            prompt_hint=f"Verification failed: {str(e)[:100]}. Treat claims with caution.",
        )


# ── Planner ──

# Standard trading team roles
STANDARD_ROLES = {
    "bull_analyst": "Make the strongest case FOR the investment. Use specific data.",
    "bear_analyst": "Make the strongest case AGAINST the investment. Identify all risks.",
    "risk_manager": "Assess downside risk, position sizing, and volatility exposure.",
    "cio": "Synthesize all perspectives and make the final investment decision.",
    "fact_checker": "Verify key claims from other agents before the final decision.",
    "technical_analyst": "Analyze chart patterns, indicators, and support/resistance.",
    "sentiment_analyst": "Assess market sentiment from news, social media, and insider activity.",
}

# Simple plan → execute → review workflow
PLAN_STEPS = [
    {"phase": "gather", "roles": ["technical_analyst", "sentiment_analyst"], "description": "Gather data and initial analysis"},
    {"phase": "debate", "roles": ["bull_analyst", "bear_analyst"], "description": "Present bull and bear cases"},
    {"phase": "verify", "roles": ["fact_checker"], "description": "Verify key claims from debate"},
    {"phase": "assess", "roles": ["risk_manager"], "description": "Assess risk profile"},
    {"phase": "decide", "roles": ["cio"], "description": "Final investment decision"},
]


# ── VeroQ Team ──


class VeroQTeam:
    """Coordinated team of agents with automatic VeroQ verification."""

    def __init__(
        self,
        agents: list[AgentConfig],
        enable_auto_verification: bool = True,
        veroq_endpoint: str = "https://api.veroq.ai",
        veroq_api_key: str | None = None,
    ):
        self.agents: dict[str, AgentConfig] = {a.id: a for a in agents}
        self.agents_by_role: dict[str, AgentConfig] = {a.role: a for a in agents}
        self.enable_auto_verification = enable_auto_verification
        self.veroq_endpoint = veroq_endpoint
        self.veroq_api_key = veroq_api_key
        self.tasks: dict[str, TaskConfig] = {}
        self.messages: list[AgentMessage] = []
        self.memory: dict[str, dict[str, Any]] = {a.id: dict(a.initial_memory) for a in agents}
        self._running = True

        # Auto-activate fact checker when verification is enabled
        self.fact_checker = None
        if enable_auto_verification:
            from tradingagents.agents.veroq_fact_checker import VeroQFactChecker
            self.fact_checker = VeroQFactChecker(
                endpoint=veroq_endpoint,
                api_key=veroq_api_key,
            )

    # ── Agent Management ──

    def add_agent(self, config: AgentConfig) -> AgentConfig:
        """Add an agent to the team."""
        self.agents[config.id] = config
        self.agents_by_role[config.role] = config
        self.memory[config.id] = dict(config.initial_memory)
        return config

    def send_message(self, from_id: str, to_id: str, content: str) -> AgentMessage:
        """Send a message between agents, with optional auto-verification."""
        verification = None
        if self.enable_auto_verification and _needs_verification(content):
            verification = _verify_with_veroq(
                content, self.veroq_endpoint, self.veroq_api_key
            )

        msg = AgentMessage(
            from_agent=from_id,
            to_agent=to_id,
            content=content,
            verification=verification,
        )
        self.messages.append(msg)

        # Store in recipient's memory
        if to_id in self.memory:
            inbox = self.memory[to_id].setdefault("inbox", [])
            inbox.append({
                "from": from_id,
                "content": content,
                "verification": {
                    "confidence_score": verification.confidence_score,
                    "verification_status": verification.verification_status,
                    "evidence_count": len(verification.evidence_chain),
                } if verification else None,
            })

        return msg

    # ── Task Management ──

    def create_task(self, description: str, assigned_to: str) -> TaskConfig:
        """Create a task assigned to an agent."""
        task = TaskConfig(
            id=str(uuid.uuid4())[:8],
            description=description,
            assigned_to=assigned_to,
        )
        self.tasks[task.id] = task
        return task

    def update_task(self, task_id: str, status: TaskStatus, result: Any = None, error: str | None = None) -> TaskConfig:
        """Update a task's status."""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        task.status = status
        task.result = result
        task.error = error
        if status in (TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.STOPPED):
            task.completed_at = datetime.utcnow().isoformat()
        return task

    def list_tasks(self, status: TaskStatus | None = None) -> list[TaskConfig]:
        """List tasks, optionally filtered by status."""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def stop_task(self, task_id: str) -> TaskConfig:
        """Stop a running task."""
        return self.update_task(task_id, TaskStatus.STOPPED)

    # ── Run Workflow ──

    def run(self, query: str) -> dict[str, Any]:
        """
        Execute a plan → execute → review workflow.

        Returns structured result with verification metadata.
        """
        start_time = time.time()
        results: dict[str, Any] = {
            "query": query,
            "phases": [],
            "final_decision": None,
            "verification_summary": None,
        }

        for step in PLAN_STEPS:
            if not self._running:
                break

            phase_result = {
                "phase": step["phase"],
                "description": step["description"],
                "outputs": [],
            }

            for role in step["roles"]:
                agent = self.agents_by_role.get(role)
                if not agent:
                    continue

                # Create task
                task_desc = f"{step['description']} — {STANDARD_ROLES.get(role, role)}"
                task = self.create_task(task_desc, agent.id)
                self.update_task(task.id, TaskStatus.RUNNING)

                try:
                    # Simulate agent output (in real usage, this calls the LLM)
                    output = self._execute_agent(agent, query, step["phase"])

                    # Route through fact checker if enabled
                    if self.fact_checker:
                        checked = self.fact_checker.check_agent_output(agent.name, role, output)
                        verification_data = checked.get("verification")
                        formatted_output = checked.get("formatted", output)
                    else:
                        verification_data = None
                        formatted_output = output

                    self.update_task(task.id, TaskStatus.COMPLETE, result=output)

                    phase_result["outputs"].append({
                        "agent": agent.name,
                        "role": role,
                        "output": output,
                        "formatted": formatted_output,
                        "verification": verification_data,
                        "task_id": task.id,
                    })

                    # Share with other agents
                    for other_id in self.agents:
                        if other_id != agent.id:
                            self.send_message(agent.id, other_id, output)

                except Exception as e:
                    self.update_task(task.id, TaskStatus.FAILED, error=str(e))
                    phase_result["outputs"].append({
                        "agent": agent.name,
                        "role": role,
                        "error": str(e),
                        "task_id": task.id,
                    })

            results["phases"].append(phase_result)

            # CIO phase produces the final decision
            if step["phase"] == "decide":
                cio_outputs = [o for o in phase_result["outputs"] if o.get("role") == "cio"]
                if cio_outputs:
                    results["final_decision"] = cio_outputs[0]

        # Verification summary
        all_verifications = [
            o.get("verification")
            for p in results["phases"]
            for o in p["outputs"]
            if o.get("verification")
        ]
        if all_verifications:
            avg_confidence = sum(v["confidenceScore"] for v in all_verifications) / len(all_verifications)
            total_evidence = sum(len(v["evidenceChain"]) for v in all_verifications)
            results["verification_summary"] = {
                "total_verifications": len(all_verifications),
                "average_confidence": round(avg_confidence),
                "total_evidence_items": total_evidence,
                "all_verified": all(v["verificationStatus"] == "verified" for v in all_verifications),
            }

        # Fact checker summary
        if self.fact_checker:
            fc_summary = self.fact_checker.get_summary()
            if results.get("verification_summary"):
                results["verification_summary"]["fact_checker"] = fc_summary
            else:
                results["verification_summary"] = {"fact_checker": fc_summary}

        results["duration_seconds"] = round(time.time() - start_time, 1)
        results["tasks_completed"] = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETE])
        results["tasks_total"] = len(self.tasks)

        return results

    def _execute_agent(self, agent: AgentConfig, query: str, phase: str) -> str:
        """
        Execute an agent's task. Override this in subclasses for real LLM calls.
        Default implementation returns a structured placeholder.
        """
        role_prompt = STANDARD_ROLES.get(agent.role, "Provide your analysis.")

        # Check agent memory for context from previous phases
        inbox = self.memory.get(agent.id, {}).get("inbox", [])
        context = ""
        if inbox:
            context = f"\n\nPrevious context from team:\n" + "\n".join(
                f"- {m['from']}: {m['content'][:200]}" for m in inbox[-3:]
            )

        return (
            f"[{agent.name} — {phase}] Analysis for: {query}\n"
            f"Role: {role_prompt}\n"
            f"This is a placeholder — connect to your LLM for real analysis.{context}"
        )

    def stop(self) -> None:
        """Stop the team workflow."""
        self._running = False
        for task in self.tasks.values():
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.STOPPED


# ── Public API ──


def startVeroQTeam(config: dict[str, Any]) -> VeroQTeam:
    """
    Start a verified trading team.

    Args:
        config: {
            "agents": [{"name": str, "role": str, "initialMemory": dict}],
            "enableAutoVerification": bool (default True),
            "veroqEndpoint": str (default "https://api.veroq.ai"),
        }

    Returns:
        VeroQTeam instance ready to run queries.

    Example:
        team = startVeroQTeam({
            "agents": [
                {"name": "Bull", "role": "bull_analyst"},
                {"name": "Bear", "role": "bear_analyst"},
                {"name": "Risk", "role": "risk_manager"},
                {"name": "CIO", "role": "cio"},
            ],
        })
        result = team.run("Analyze NVDA")
    """
    agents = [
        AgentConfig(
            name=a["name"],
            role=a["role"],
            initial_memory=a.get("initialMemory", {}),
        )
        for a in config.get("agents", [])
    ]

    return VeroQTeam(
        agents=agents,
        enable_auto_verification=config.get("enableAutoVerification", True),
        veroq_endpoint=config.get("veroqEndpoint", "https://api.veroq.ai"),
    )


def addAgentToTeam(team: VeroQTeam, agent_config: dict[str, Any]) -> AgentConfig:
    """Add an agent to an existing team."""
    config = AgentConfig(
        name=agent_config["name"],
        role=agent_config["role"],
        initial_memory=agent_config.get("initialMemory", {}),
    )
    return team.add_agent(config)


def sendMessageBetweenAgents(team: VeroQTeam, from_id: str, to_id: str, content: str) -> AgentMessage:
    """Send a message between two agents."""
    return team.send_message(from_id, to_id, content)


def createTask(team: VeroQTeam, description: str, assigned_to: str) -> TaskConfig:
    """Create a task for an agent."""
    return team.create_task(description, assigned_to)


def updateTask(team: VeroQTeam, task_id: str, status: str, result: Any = None) -> TaskConfig:
    """Update a task status."""
    return team.update_task(task_id, TaskStatus(status), result=result)


def listTasks(team: VeroQTeam, status: str | None = None) -> list[TaskConfig]:
    """List all tasks."""
    return team.list_tasks(TaskStatus(status) if status else None)


def stopTask(team: VeroQTeam, task_id: str) -> TaskConfig:
    """Stop a task."""
    return team.stop_task(task_id)
