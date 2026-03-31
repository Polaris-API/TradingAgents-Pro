"""
VeroQ Fact Checker — Automatic verification layer for agent outputs.

Monitors agent outputs for financial claims (tickers, signals, sentiment,
market data) and routes them through VeroQ /verify for evidence-backed
verification. Attaches confidenceScore, evidenceChain, and verificationStatus
to every flagged output.

This module does NOT duplicate verification logic — it relies entirely on
the coordinator's _verify_with_veroq() and _needs_verification() functions.

Usage:
    Automatically activated inside startVeroQTeam when enableAutoVerification=True.
    Can also be used standalone:

        from tradingagents.agents.veroq_fact_checker import VeroQFactChecker

        checker = VeroQFactChecker(endpoint="https://api.veroq.ai")
        result = checker.check("NVDA revenue grew 40% year over year")
        print(result.formatted)  # [✓ VERIFIED] Confidence: 85/100 ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Import verification logic from the coordinator — single source of truth
from tradingagents.coordinator.veroq_agent_coordinator import (
    _needs_verification,
    _verify_with_veroq,
    VerificationMetadata,
)


@dataclass
class FactCheckResult:
    """Result of a fact check with formatted output."""
    original_text: str
    needs_check: bool
    metadata: Optional[VerificationMetadata] = None
    formatted: str = ""

    def __post_init__(self):
        if not self.formatted and self.metadata:
            self.formatted = format_verification(self.original_text, self.metadata)


def format_verification(text: str, meta: VerificationMetadata) -> str:
    """Format agent output with verification metadata in clean style."""
    lines = []

    # Status header
    if meta.verification_status == "verified":
        emoji, label = "✓", "VERIFIED"
    elif meta.verification_status == "flagged":
        emoji, label = "⚠", "FLAGGED"
    else:
        emoji, label = "?", "LOW CONFIDENCE"

    lines.append(f"[{emoji} {label}] Confidence: {meta.confidence_score}/100")
    lines.append("")

    # Original output
    lines.append(text)

    # Evidence chain
    if meta.evidence_chain:
        lines.append("")
        lines.append(f"Evidence ({len(meta.evidence_chain)} sources):")
        for ev in meta.evidence_chain[:5]:
            pos = f"[{ev.get('position', '?')}]" if ev.get("position") else ""
            rel = f"({round(ev['reliability'] * 100)}% reliable)" if ev.get("reliability") else ""
            lines.append(f"  {pos} {ev.get('source', 'Unknown')} {rel}".strip())
            if ev.get("snippet"):
                lines.append(f'    "{ev["snippet"][:100]}"')

    # Low confidence warning
    if meta.confidence_score < 50:
        lines.append("")
        lines.append(f"⚠ LOW CONFIDENCE — {meta.prompt_hint}")

    return "\n".join(lines)


class VeroQFactChecker:
    """
    Automatic fact-checking layer for agent teams.

    Monitors text for financial claims and verifies them through VeroQ.
    Designed to be plugged into the VeroQTeam coordinator.
    """

    def __init__(
        self,
        endpoint: str = "https://api.veroq.ai",
        api_key: str | None = None,
        auto_flag_threshold: int = 50,
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.auto_flag_threshold = auto_flag_threshold
        self.checks_performed: int = 0
        self.flags_raised: int = 0
        self.history: list[FactCheckResult] = []

    def check(self, text: str) -> FactCheckResult:
        """
        Check text for financial claims and verify if needed.

        Returns FactCheckResult with verification metadata and formatted output.
        """
        needs_check = _needs_verification(text)

        if not needs_check:
            result = FactCheckResult(
                original_text=text,
                needs_check=False,
            )
            self.history.append(result)
            return result

        # Route through VeroQ
        metadata = _verify_with_veroq(text, self.endpoint, self.api_key)
        self.checks_performed += 1

        if metadata.confidence_score < self.auto_flag_threshold:
            self.flags_raised += 1

        result = FactCheckResult(
            original_text=text,
            needs_check=True,
            metadata=metadata,
        )
        self.history.append(result)
        return result

    def check_agent_output(
        self, agent_name: str, role: str, output: str
    ) -> dict[str, Any]:
        """
        Check an agent's output and return structured result.

        Used by the coordinator to process agent outputs during workflow execution.
        """
        result = self.check(output)

        return {
            "agent": agent_name,
            "role": role,
            "output": output,
            "fact_checked": result.needs_check,
            "verification": {
                "confidenceScore": result.metadata.confidence_score,
                "evidenceChain": result.metadata.evidence_chain,
                "verificationStatus": result.metadata.verification_status,
                "promptHint": result.metadata.prompt_hint,
            } if result.metadata else None,
            "formatted": result.formatted if result.formatted else output,
        }

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all fact checks performed."""
        checked = [r for r in self.history if r.needs_check]
        return {
            "total_outputs_seen": len(self.history),
            "total_checked": self.checks_performed,
            "flags_raised": self.flags_raised,
            "average_confidence": (
                round(sum(r.metadata.confidence_score for r in checked if r.metadata) / len(checked))
                if checked else 0
            ),
            "all_verified": all(
                r.metadata.verification_status == "verified"
                for r in checked if r.metadata
            ) if checked else True,
        }
