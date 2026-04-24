# Changelog

All notable changes to TradingAgents-Pro are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-04-23

First tagged release. Everything below was landed across the `veroq-ai`
rebrand window in late March 2026.

### Added
- **VeroQ Agent Coordinator** (`tradingagents.coordinator.startVeroQTeam`) —
  orchestrates multi-agent trading workflows with automatic per-output
  verification routing. Every claim with a ticker, signal, or market
  statement is fact-checked before it propagates to the next phase.
- **VeroQ Fact Checker** — verification layer for agent outputs. Returns
  `confidenceScore`, `evidenceChain` (sources with reliability 0-1),
  `verificationStatus`, and a `promptHint` for downstream agents.
- **9 new agents** on top of the original 9 from upstream TradingAgents:
  Fact Checker, Bias Auditor, Forecast Agent, Contradiction Detector,
  Research Evaluator, Sentiment Analyst, Fundamentals Analyst, and two
  specialized Risk Analysts (aggressive / conservative) bracketing the
  neutral analyst. Total: 18 agents.
- **20 technical indicators** exposed through the dataflow layer
  (RSI, MACD, Bollinger Bands, SMA/EMA 20/50/200, ATR, Stochastic, ADX,
  OBV, VWAP, …).
- **`[TradingAgents-Pro Enhancement]` markers** tagging every file added
  or modified relative to upstream, so diffs against original TradingAgents
  are one `grep` away.
- **No-hallucination directive** shared across all agents — explicit
  "only reference data provided" constraint in every agent's system prompt.
- **Executive Summary** output format — verdict, confidence, top risk,
  data-quality average, verification stats, macro context.
- **Demo mode** (`--demo`) — uploads analysis reports to VeroQ and returns
  a shareable URL, useful for stakeholder review without installing the
  framework.
- **Professional PDF report export** for the same analysis.
- **Works with 6 LLM providers**: OpenAI, Anthropic, Google Gemini, xAI Grok,
  Ollama (local), OpenRouter (any model).
- **CLI (`@veroq/cli`)** — `veroq ask`, `veroq screen`, `veroq signal`,
  `veroq compare` for lightweight one-off queries without the full
  18-agent pipeline.

### Relationship to upstream
- **Fork of [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)**
  (Apache 2.0). Original paper: [arXiv:2412.20138](https://arxiv.org/abs/2412.20138).
- Upstream contributions in the data/verification layer are welcomed back
  in principle, though the maintainer pattern of direct-pushing rather
  than merging external PRs makes the fork the practical distribution path.
