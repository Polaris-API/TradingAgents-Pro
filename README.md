# TradingAgents-Pro

[![Release](https://img.shields.io/github/v/release/Veroq-ai/TradingAgents-Pro?display_name=tag&color=2EE89A)](https://github.com/Veroq-ai/TradingAgents-Pro/releases)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Powered by VeroQ](https://img.shields.io/badge/Powered%20by-VeroQ-2EE89A)](https://veroq.ai)

Enhanced multi-agent trading framework with verified intelligence, bias detection, and forward-looking predictions. **Built with [VeroQ](https://veroq.ai).**

> 18 AI agents. 20 technical indicators. Every claim fact-checked. Every source bias-scored. Every prediction comes with invalidation criteria.

**Fork of [TradingAgents](https://github.com/TauricResearch/TradingAgents)** (Apache-2.0) — adds a runtime verification layer and 9 new agents on top of the original framework. See [CHANGELOG.md](CHANGELOG.md) for what's in v0.1.0.

## Verified Trading Workflow

The VeroQ Agent Coordinator connects your trading team to automatic fact-checking. When any agent produces output with tickers, signals, or market claims, it's routed through VeroQ for verification.

```python
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
```

**Output with verification metadata:**

```json
{
  "query": "Analyze NVDA for a potential long position",
  "phases": [
    {
      "phase": "debate",
      "outputs": [
        {
          "agent": "Bull Analyst",
          "role": "bull_analyst",
          "output": "NVDA trades at $167 with RSI 35...",
          "verification": {
            "confidenceScore": 85,
            "evidenceChain": [
              {"source": "Reuters", "position": "supports", "reliability": 0.95},
              {"source": "Bloomberg", "position": "supports", "reliability": 0.94}
            ],
            "verificationStatus": "verified",
            "promptHint": "Verdict: supported. Agreement: 0.92, Quality: 0.88"
          }
        }
      ]
    }
  ],
  "verification_summary": {
    "total_verifications": 5,
    "average_confidence": 78,
    "total_evidence_items": 12,
    "all_verified": true
  }
}
```

> Advanced verification and enterprise features powered by VeroQ — visit [veroq.ai](https://veroq.ai) for details and plans.

## Or Just /ask Veroq

Don't need the full 18-agent pipeline? Get instant answers:

```bash
npm install -g @veroq/cli
export VEROQ_API_KEY=pr_live_xxx

veroq ask "Should I buy NVDA?"
veroq screen "oversold semiconductors"
veroq signal MSFT
veroq compare AAPL MSFT GOOGL
```

Or use the Python SDK:

```python
from veroq import Agent

agent = Agent()
result = agent.ask("Should I buy NVDA?")
print(result.summary)       # Bottom line + technicals + sentiment + earnings
print(result.trade_signal)  # { action: "hold", score: 50, factors: [...] }
```

One line. Complete analysis. [Get a free API key](https://thepolarisreport.com/pricing). [Try it live](https://thepolarisreport.com/ask).

## What's Different

| Feature | TradingAgents | TradingAgents-Pro |
|---------|--------------|-------------------|
| Agents | 9 | 18 |
| Data quality signal | None | Every source scored 0-1 |
| Fact checking | None | Claims verified before debate |
| Bias detection | None | Source distribution + framing analysis |
| Predictions | None | Forward outlook with invalidation criteria |
| Contradictions | None | Flagged and quantified |
| Technical indicators | Basic (via yfinance) | 20 indicators + composite signal |
| Sentiment | String labels | Numeric -1.0 to 1.0 + trend |
| Data sources | yfinance + Alpha Vantage | Veroq (primary) + yfinance (supplementary) |
| NLP screener | N/A | Natural language → analysis |
| Evidence weighting | Equal | Confidence-weighted debate |
| Executive summary | Buried | First section, 10-second answer |
| Macro analysis | None | Economy, yields, VIX, sector rotation |
| Backtest | None | Historical strategy replay |
| Portfolio mode | None | Multi-ticker with correlations |

## Safety & Accuracy Improvements

TradingAgents-Pro includes several safety enhancements not present in the original framework:

| Risk | Original | TradingAgents-Pro |
|------|----------|-------------------|
| **LLM hallucination** | No safeguards — agents can fabricate numbers, prices, and claims | Every agent includes `[TradingAgents-Pro Enhancement]` accuracy directives: never fabricate, report N/A for missing data, attribute every number |
| **Unverified claims** | All claims treated as equally valid | Fact Checker agent verifies claims against source corpus before debate — verified claims carry more weight |
| **Source bias** | No assessment of source diversity or framing | Bias Auditor agent flags skewed source distribution, framing divergences, and blind spots |
| **Data contradictions** | Not detected | Contradiction Detector catches conflicting facts across analyst reports, rates severity |
| **Confidence transparency** | No data quality signal | Confidence Dashboard shows sources consulted, verification rate, contradiction count, bias assessment |
| **Missing data handling** | Agents may guess or omit silently | Agents explicitly state "Data unavailable" — gaps are visible, not hidden |

All safety enhancements are tagged in the source code with `[TradingAgents-Pro Enhancement]` so they're easy to identify in diffs against the original.

## Quick Start

```bash
# Clone
git clone https://github.com/Polaris-API/TradingAgents-Pro.git
cd TradingAgents-Pro

# Install
pip install -e .

# Set your API keys
export VEROQ_API_KEY=pr_live_xxx     # Free: thepolarisreport.com/pricing (POLARIS_API_KEY also works)
export OPENAI_API_KEY=sk-xxx         # Or use Anthropic, Google, etc.

# Run
python run.py NVDA
```

## Usage

```bash
# Full 18-agent analysis
python run.py NVDA

# Quick mode — skip debate, ~30 seconds
python run.py NVDA --quick

# Compare multiple tickers
python run.py --compare NVDA AAPL TSLA

# AI-powered stock screener → analysis
python run.py --screen "oversold tech stocks with rising sentiment"

# Portfolio analysis with correlations
python run.py --portfolio NVDA:40,AAPL:30,BTC:30

# Backtest sentiment signals
python run.py NVDA --backtest

# Pre-built strategies
python run.py --preset oversold_bounce

# Deep analysis (uses most capable model)
python run.py NVDA --depth deep
```

## Pipeline Architecture

```
Context Builder (market summary + events + macro snapshot)
→ Macro Analyst (economy, yields, VIX, sector rotation)
→ Market Analyst (20 indicators + composite signal)
→ News Analyst (confidence-scored briefs + counter-arguments)
→ Sentiment Analyst (numeric -1.0→1.0 + social + trend)
→ Fundamentals Analyst (financials + earnings + SEC filings)
→ Fact Checker (verifies claims BEFORE debate)
→ Bull Advocate ↔ Bear Advocate (evidence-weighted debate)
→ Bias Auditor (source distribution + framing analysis)
→ Forecast Agent (predictions + invalidation criteria)
→ Contradiction Detector (flags conflicting facts)
→ Research Evaluator (evidence-weighted scoring)
→ Trader (executive summary + confidence dashboard)
→ Risk Analysts (aggressive/conservative/neutral with macro + invalidation)
→ Portfolio Manager (final decision with full evidence trail)
```

## Sample Output

See [examples/NVDA_pro.md](examples/NVDA_pro.md) for a complete analysis report, and [examples/NVDA_original.md](examples/NVDA_original.md) for the same ticker analyzed by the original TradingAgents framework.

### Executive Summary (from a real run)

```
## Executive Summary
Verdict: BUY | Confidence: 78% | Top Risk: China export restrictions
Data Quality: 0.84 avg confidence | 23 sources | balanced bias

Verified Claims: 7/8 supported | 1 disputed
Contradictions: 1 (minor — layoff count discrepancy)
Macro: FAVORABLE (low VIX, strong GDP, sector rotation into tech)
```

## Configuration

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()

# LLM provider (OpenAI, Anthropic, Google, xAI, Ollama, OpenRouter)
config["llm_provider"] = "anthropic"
config["deep_think_llm"] = "claude-sonnet-4-20250514"

# Debate rounds
config["max_debate_rounds"] = 2      # More rounds = deeper analysis
config["max_risk_discuss_rounds"] = 2

ta = TradingAgentsGraph(config=config)
state, decision = ta.propagate("NVDA", "2026-03-24")
```

## LLM Providers

Works with any major LLM provider:

| Provider | Models | Setup |
|----------|--------|-------|
| OpenAI | GPT-5.2, GPT-5-mini | `OPENAI_API_KEY` |
| Anthropic | Claude Opus, Sonnet | `ANTHROPIC_API_KEY` |
| Google | Gemini 3.1 Pro | `GOOGLE_API_KEY` |
| xAI | Grok | `XAI_API_KEY` |
| Ollama | Any local model | `OLLAMA_BASE_URL` |
| OpenRouter | Any model | `OPENROUTER_API_KEY` |

## Powered by Veroq

Built on the [Veroq Knowledge API](https://thepolarisreport.com) — financial intelligence for AI agents.

- **300+ endpoints** — equities, crypto, forex, commodities, SEC filings, insider trades, analyst ratings
- **`/ask`** — one endpoint answers any financial question
- **Agent Marketplace** — build, share, and monetize trading agents
- **8 SDKs + CLI** — Python, TypeScript, LangChain, CrewAI, Vercel AI, MCP, n8n, [CLI](https://www.npmjs.com/package/@veroq/cli)
- **Free tier** — 1,000 credits/month, no credit card required

## Credits

Built on [TradingAgents](https://github.com/TauricResearch/TradingAgents) by Tauric Research — the original multi-agent LLM trading framework that introduced collaborative analyst, researcher, and risk management agents for market analysis. TradingAgents-Pro replaces the data layer with verified intelligence and adds 9 new agents for a fundamentally better analysis pipeline. The original paper is available at [arXiv:2412.20138](https://arxiv.org/abs/2412.20138).

## Disclaimer

This software is for educational and research purposes only. It is not financial advice. Do not make investment decisions based solely on the output of this system. Past performance does not guarantee future results. Always consult a qualified financial advisor.
