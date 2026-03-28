#!/usr/bin/env python3
"""
TradingAgents-Pro -- Enhanced multi-agent trading framework.

Usage:
    python run.py NVDA                              # Full analysis
    python run.py NVDA --quick                      # Skip debate, fast verdict
    python run.py --compare NVDA AAPL TSLA          # Compare multiple tickers
    python run.py --screen "oversold tech stocks"   # NLP screener -> analysis
    python run.py NVDA --backtest                   # Include backtest results
    python run.py --portfolio NVDA:40,AAPL:30,BTC:30  # Portfolio analysis
    python run.py NVDA --demo                       # Save + get shareable URL
    python run.py NVDA --depth deep                 # Opus-powered deep forecast
    python run.py --preset oversold_bounce           # Pre-built screener strategy
"""

import argparse
import sys
import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; env vars can be set directly


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today() -> str:
    """Return today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def _print_header(title: str) -> None:
    """Print a visible section header."""
    width = max(len(title) + 6, 60)
    print()
    print("=" * width)
    print(f"   {title}")
    print("=" * width)
    print()


def _print_subheader(title: str) -> None:
    """Print a subsection header."""
    print()
    print(f"--- {title} ---")
    print()


def _build_config(args) -> dict:
    """Build a config dict from defaults + CLI flags."""
    from tradingagents.default_config import DEFAULT_CONFIG

    config = DEFAULT_CONFIG.copy()

    # Quick mode: skip debate rounds entirely
    if getattr(args, "quick", False):
        config["max_debate_rounds"] = 0
        config["max_risk_discuss_rounds"] = 0

    # Depth mode: swap forecast agent to deep_think_llm
    depth = getattr(args, "depth", None)
    if depth == "deep":
        # Use the deep thinking model for both roles so the forecast
        # agent gets the most capable model available.
        # (The graph already uses deep_think_llm for the forecast agent,
        #  but we bump the quick_think_llm to the deep model as well
        #  when --depth deep is requested.)
        config["quick_think_llm"] = config["deep_think_llm"]

    return config


def _run_pipeline(ticker: str, date: str, config: dict, quiet: bool = False):
    """Run the full TradingAgents pipeline and return (state, decision)."""
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    if not quiet:
        mode = "quick" if config.get("max_debate_rounds") == 0 else "full"
        print(f"  Ticker:  {ticker}")
        print(f"  Date:    {date}")
        print(f"  Mode:    {mode} pipeline")
        print(f"  Deep LLM:  {config.get('deep_think_llm', 'default')}")
        print(f"  Quick LLM: {config.get('quick_think_llm', 'default')}")
        print()

    ta = TradingAgentsGraph(debug=True, config=config)
    state, decision = ta.propagate(ticker, date)
    return state, decision


def _get_polaris_client():
    """Get a Veroq client for direct API calls (screener, backtest, etc.)."""
    try:
        from veroq import PolarisClient
    except ImportError:
        print("ERROR: veroq is required for this feature.")
        print("       Install it with: pip install veroq")
        sys.exit(1)

    api_key = os.environ.get("VEROQ_API_KEY") or os.environ.get("POLARIS_API_KEY")
    if not api_key:
        print("ERROR: VEROQ_API_KEY environment variable is required.")
        print("       Get a free key at https://thepolarisreport.com/pricing")
        sys.exit(1)

    return PolarisClient(api_key=api_key)


def _extract_verdict_info(state: dict, decision: str) -> dict:
    """Extract verdict, confidence, signal, and top risk from a pipeline result.

    Parses the final_trade_decision and related state fields to build
    a summary row for the comparison table.
    """
    text = state.get("final_trade_decision", decision or "")
    text_upper = text.upper()

    # Extract verdict
    verdict = "HOLD"
    for v in ["BUY", "SELL", "OVERWEIGHT", "UNDERWEIGHT", "HOLD"]:
        if v in text_upper:
            verdict = v
            break

    # Extract confidence -- look for patterns like "78%", "confidence: 78%",
    # "confidence of 78%", "78 percent"
    confidence = "N/A"
    conf_match = re.search(
        r"confidence[:\s]+(\d{1,3})%|(\d{1,3})\s*%\s*confidence|(\d{1,3})%",
        text, re.IGNORECASE,
    )
    if conf_match:
        confidence = f"{conf_match.group(1) or conf_match.group(2) or conf_match.group(3)}%"

    # Extract signal from sentiment report or decision text
    signal = "neutral"
    sentiment = state.get("sentiment_report", "")
    combined = (text + " " + sentiment).lower()
    if "bullish" in combined:
        signal = "bullish"
    elif "bearish" in combined:
        signal = "bearish"

    # Extract top risk from risk debate or decision text
    top_risk = "N/A"
    risk_state = state.get("risk_debate_state", {})
    risk_text = risk_state.get("judge_decision", "") if isinstance(risk_state, dict) else ""
    if not risk_text:
        risk_text = text
    # Look for common risk keywords
    risk_patterns = [
        r"(?:top|key|primary|main|biggest)\s+risk[:\s]+([^\n.]{5,40})",
        r"risk[:\s]+([^\n.]{5,40})",
    ]
    for pattern in risk_patterns:
        m = re.search(pattern, risk_text, re.IGNORECASE)
        if m:
            top_risk = m.group(1).strip()[:20]
            break

    return {
        "verdict": verdict,
        "confidence": confidence,
        "signal": signal,
        "top_risk": top_risk,
    }


def _print_comparison_table(rows: list) -> None:
    """Print a formatted comparison table.

    Each row is a dict with keys: ticker, verdict, confidence, signal, top_risk.
    """
    # Column widths
    cols = [
        ("Ticker", "ticker", 8),
        ("Verdict", "verdict", 12),
        ("Confidence", "confidence", 12),
        ("Signal", "signal", 9),
        ("Top Risk", "top_risk", 20),
    ]

    # Build border and header
    top_border = "+" + "+".join("-" * (w + 2) for _, _, w in cols) + "+"
    header = "|" + "|".join(f" {name:<{w}} " for name, _, w in cols) + "|"
    sep = "+" + "+".join("-" * (w + 2) for _, _, w in cols) + "+"

    print()
    print(top_border)
    print(header)
    print(sep)

    for row in rows:
        line = "|" + "|".join(
            f" {str(row.get(key, 'N/A')):<{w}} " for _, key, w in cols
        ) + "|"
        print(line)

    print(top_border)
    print()


def _save_report(ticker: str, date: str, report: str) -> str:
    """Save a markdown report to the results directory. Returns the file path."""
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{ticker}_pro_{date}.md"
    filepath = results_dir / filename
    filepath.write_text(report, encoding="utf-8")
    return str(filepath)


# ---------------------------------------------------------------------------
# Mode implementations
# ---------------------------------------------------------------------------

def mode_standard(args) -> None:
    """Standard mode: full 18-agent pipeline on a single ticker."""
    ticker = args.ticker.upper()
    date = args.date or _today()
    config = _build_config(args)

    label = "Quick Analysis" if getattr(args, "quick", False) else "Full Analysis"
    _print_header(f"TradingAgents-Pro | {label}: {ticker}")

    state, decision = _run_pipeline(ticker, date, config)

    _print_subheader("Decision")
    print(decision)
    print()

    # Save report
    from tradingagents.output.formatter import format_pro_report
    report = format_pro_report(state)
    path = _save_report(ticker, date, report)
    print(f"Report saved to: {path}")


def mode_compare(args) -> None:
    """Compare mode: run analysis on multiple tickers, then print comparison table."""
    tickers = [t.upper() for t in args.compare]
    date = args.date or _today()
    config = _build_config(args)

    _print_header(f"TradingAgents-Pro | Compare: {', '.join(tickers)}")

    rows = []
    for i, ticker in enumerate(tickers, 1):
        _print_subheader(f"Analyzing {ticker} ({i}/{len(tickers)})")

        try:
            state, decision = _run_pipeline(ticker, date, config, quiet=False)
            info = _extract_verdict_info(state, decision)
            info["ticker"] = ticker
            rows.append(info)

            # Save individual report
            from tradingagents.output.formatter import format_pro_report
            report = format_pro_report(state)
            path = _save_report(ticker, date, report)
            print(f"  Report saved to: {path}")
        except Exception as e:
            print(f"  ERROR analyzing {ticker}: {e}")
            rows.append({
                "ticker": ticker,
                "verdict": "ERROR",
                "confidence": "N/A",
                "signal": "N/A",
                "top_risk": str(e)[:20],
            })

    _print_header("Comparison Summary")
    _print_comparison_table(rows)


def mode_screen(args) -> None:
    """Screen mode: NLP screener -> quick analysis on top results."""
    query = args.screen
    date = args.date or _today()

    _print_header(f"TradingAgents-Pro | Screen: \"{query}\"")

    client = _get_polaris_client()

    # Run NLP screener
    _print_subheader("Screener Results")
    try:
        results = client.screener_natural(query)
    except Exception as e:
        print(f"ERROR: Screener failed: {e}")
        sys.exit(1)

    matches = results.get("matches", results.get("results", []))
    if not matches:
        print("No matches found for that query.")
        return

    # Print screener results
    for i, match in enumerate(matches[:10], 1):
        ticker = match.get("ticker", match.get("symbol", "???"))
        name = match.get("name", match.get("entity_name", ""))
        score = match.get("score", match.get("match_score", ""))
        price = match.get("price", "")
        print(f"  {i}. {ticker:<8} {name:<30} score={score}  price={price}")

    # Run quick analysis on top 3
    top_tickers = []
    for match in matches[:3]:
        t = match.get("ticker", match.get("symbol"))
        if t:
            top_tickers.append(t.upper())

    if not top_tickers:
        print("\nNo tickers to analyze from screener results.")
        return

    # Force quick mode for screener analysis
    config = _build_config(args)
    config["max_debate_rounds"] = 0
    config["max_risk_discuss_rounds"] = 0

    rows = []
    for i, ticker in enumerate(top_tickers, 1):
        _print_subheader(f"Quick Analysis: {ticker} ({i}/{len(top_tickers)})")

        try:
            state, decision = _run_pipeline(ticker, date, config, quiet=False)
            info = _extract_verdict_info(state, decision)
            info["ticker"] = ticker
            rows.append(info)
            print(f"  Verdict: {info['verdict']}")
        except Exception as e:
            print(f"  ERROR analyzing {ticker}: {e}")
            rows.append({
                "ticker": ticker,
                "verdict": "ERROR",
                "confidence": "N/A",
                "signal": "N/A",
                "top_risk": str(e)[:20],
            })

    _print_header("Screener Analysis Summary")
    _print_comparison_table(rows)


def mode_backtest(args) -> None:
    """Backtest mode: standard analysis + Polaris backtest results."""
    ticker = args.ticker.upper()
    date = args.date or _today()
    config = _build_config(args)

    _print_header(f"TradingAgents-Pro | Analysis + Backtest: {ticker}")

    # Run the standard pipeline first
    state, decision = _run_pipeline(ticker, date, config)

    _print_subheader("Decision")
    print(decision)

    # Run Polaris backtest
    _print_subheader("Backtest Results")
    client = _get_polaris_client()

    try:
        backtest = client.backtest(
            ticker,
            strategy="sentiment_momentum",
            period="1y",
        )

        # Print backtest summary
        summary = backtest.get("summary", backtest)
        print(f"  Strategy:        {summary.get('strategy', 'sentiment_momentum')}")
        print(f"  Period:          {summary.get('period', '1y')}")
        print(f"  Total Return:    {summary.get('total_return', 'N/A')}")
        print(f"  Sharpe Ratio:    {summary.get('sharpe_ratio', 'N/A')}")
        print(f"  Max Drawdown:    {summary.get('max_drawdown', 'N/A')}")
        print(f"  Win Rate:        {summary.get('win_rate', 'N/A')}")
        print(f"  Total Trades:    {summary.get('total_trades', 'N/A')}")

        # Append to report
        from tradingagents.output.formatter import format_pro_report
        report = format_pro_report(state)
        report += "\n\n---\n## Backtest Results\n\n"
        report += f"Strategy: sentiment_momentum\n"
        report += f"Period: 1y\n"
        for k, v in summary.items():
            report += f"{k}: {v}\n"
    except Exception as e:
        print(f"  WARNING: Backtest failed: {e}")
        print("  (Continuing with standard report)")
        from tradingagents.output.formatter import format_pro_report
        report = format_pro_report(state)

    path = _save_report(ticker, date, report)
    print()
    print(f"Report saved to: {path}")


def mode_portfolio(args) -> None:
    """Portfolio mode: analyze holdings, get correlations, produce portfolio report."""
    raw = args.portfolio
    date = args.date or _today()
    config = _build_config(args)

    _print_header("TradingAgents-Pro | Portfolio Analysis")

    # Parse holdings: "NVDA:40,AAPL:30,BTC:30"
    holdings = {}
    for item in raw.split(","):
        item = item.strip()
        if ":" in item:
            ticker, weight = item.split(":", 1)
            try:
                holdings[ticker.strip().upper()] = float(weight.strip())
            except ValueError:
                print(f"WARNING: Invalid weight for {ticker}, skipping")
        else:
            holdings[item.strip().upper()] = 0

    if not holdings:
        print("ERROR: No valid holdings parsed from input.")
        sys.exit(1)

    total_weight = sum(holdings.values())
    print("  Holdings:")
    for ticker, weight in holdings.items():
        pct = f"{weight}%" if weight > 0 else "unweighted"
        print(f"    {ticker:<8} {pct}")
    if total_weight > 0:
        print(f"    Total:   {total_weight}%")
    print()

    # Analyze each holding
    tickers = list(holdings.keys())
    results = {}
    rows = []

    # Force quick mode for portfolio (many tickers)
    config["max_debate_rounds"] = 0
    config["max_risk_discuss_rounds"] = 0

    for i, ticker in enumerate(tickers, 1):
        _print_subheader(f"Analyzing {ticker} ({i}/{len(tickers)})")
        try:
            state, decision = _run_pipeline(ticker, date, config, quiet=False)
            results[ticker] = (state, decision)
            info = _extract_verdict_info(state, decision)
            info["ticker"] = ticker
            info["weight"] = f"{holdings[ticker]}%"
            rows.append(info)
        except Exception as e:
            print(f"  ERROR analyzing {ticker}: {e}")
            rows.append({
                "ticker": ticker,
                "verdict": "ERROR",
                "confidence": "N/A",
                "signal": "N/A",
                "top_risk": str(e)[:20],
                "weight": f"{holdings[ticker]}%",
            })

    # Get correlation matrix from Polaris
    _print_subheader("Correlation Matrix")
    client = _get_polaris_client()

    correlation_text = ""
    try:
        corr = client.correlation(tickers, period="6mo")
        matrix = corr.get("matrix", corr.get("correlations", {}))

        if isinstance(matrix, dict):
            # Print header row
            header = f"{'':>8}" + "".join(f"{t:>10}" for t in tickers)
            print(header)
            for t1 in tickers:
                row_data = matrix.get(t1, {})
                row_str = f"{t1:>8}"
                for t2 in tickers:
                    val = row_data.get(t2, "N/A")
                    if isinstance(val, (int, float)):
                        row_str += f"{val:>10.3f}"
                    else:
                        row_str += f"{str(val):>10}"
                print(row_str)
            correlation_text = f"Correlation matrix for {', '.join(tickers)} (6mo period)\n"
            for t1 in tickers:
                row_data = matrix.get(t1, {})
                for t2 in tickers:
                    val = row_data.get(t2, "N/A")
                    correlation_text += f"  {t1} vs {t2}: {val}\n"
        elif isinstance(matrix, list):
            for entry in matrix:
                print(f"  {entry}")
            correlation_text = str(matrix)
        else:
            print(f"  {matrix}")
            correlation_text = str(matrix)
    except Exception as e:
        print(f"  WARNING: Correlation data unavailable: {e}")
        correlation_text = f"Correlation data unavailable: {e}"

    # Print summary table
    _print_header("Portfolio Summary")
    _print_comparison_table(rows)

    # Build combined report
    report_lines = [
        f"# TradingAgents-Pro Portfolio Analysis",
        f"*Generated {date} | Powered by Veroq Knowledge API*\n",
        "## Holdings",
        "",
    ]
    for ticker, weight in holdings.items():
        report_lines.append(f"- **{ticker}**: {weight}%")

    report_lines.append("\n## Individual Verdicts\n")
    for row in rows:
        report_lines.append(
            f"- **{row['ticker']}**: {row['verdict']} "
            f"(confidence={row['confidence']}, signal={row['signal']})"
        )

    report_lines.append(f"\n## Correlation Analysis\n\n{correlation_text}")

    # Append individual reports
    report_lines.append("\n---\n## Individual Reports\n")
    for ticker, (state, decision) in results.items():
        from tradingagents.output.formatter import format_pro_report
        report_lines.append(f"\n### {ticker}\n")
        report_lines.append(format_pro_report(state))

    combined_report = "\n".join(report_lines)
    path = _save_report("PORTFOLIO", date, combined_report)
    print(f"Report saved to: {path}")


def mode_demo(args) -> None:
    """Demo mode: full analysis + save locally + upload to Polaris for shareable URL."""
    ticker = args.ticker.upper()
    date = args.date or _today()
    config = _build_config(args)

    _print_header(f"TradingAgents-Pro | Demo Report: {ticker}")

    state, decision = _run_pipeline(ticker, date, config)

    _print_subheader("Decision")
    print(decision)
    print()

    # Save report locally
    from tradingagents.output.formatter import format_pro_report
    report = format_pro_report(state)
    path = _save_report(ticker, date, report)
    print(f"Report saved to: {path}")

    # Upload to Polaris for shareable URL
    _print_subheader("Sharing")
    try:
        import requests
        api_key = os.environ.get("VEROQ_API_KEY") or os.environ.get("POLARIS_API_KEY", "")
        if not api_key:
            print("Set VEROQ_API_KEY to upload reports. Skipping upload.")
            return

        resp = requests.post(
            "https://api.thepolarisreport.com/api/v1/reports/upload",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json={"ticker": ticker, "tier": "cli", "markdown": report},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            report_id = data.get("report_id", data.get("id", ""))
            url = f"https://thepolarisreport.com/reports/{report_id}"
            print(f"Shareable URL: {url}")
            print(f"Report ID: {report_id}")
        else:
            print(f"Upload failed ({resp.status_code}). Report saved locally at {path}")
    except Exception as e:
        print(f"Upload failed: {e}. Report saved locally at {path}")


def mode_preset(args) -> None:
    """Preset mode: run a pre-built screener strategy, then analyze top results."""
    preset_id = args.preset
    date = args.date or _today()

    _print_header(f"TradingAgents-Pro | Preset Strategy: {preset_id}")

    client = _get_polaris_client()

    # If preset_id is "list", show available presets
    if preset_id.lower() == "list":
        _print_subheader("Available Presets")
        try:
            presets = client.screener_presets()
            preset_list = presets.get("presets", presets.get("results", []))
            if isinstance(preset_list, list):
                for p in preset_list:
                    pid = p.get("id", p.get("preset_id", "???"))
                    name = p.get("name", p.get("label", ""))
                    desc = p.get("description", "")[:60]
                    print(f"  {pid:<25} {name:<30} {desc}")
            else:
                print(f"  {preset_list}")
        except Exception as e:
            print(f"ERROR: Could not fetch presets: {e}")
        return

    # Run the specific preset
    _print_subheader(f"Running preset: {preset_id}")
    try:
        results = client.screener_preset(preset_id)
    except Exception as e:
        print(f"ERROR: Preset '{preset_id}' failed: {e}")
        sys.exit(1)

    matches = results.get("matches", results.get("results", []))
    if not matches:
        print(f"No matches found for preset '{preset_id}'.")
        return

    # Print screener results
    print("  Screener matches:")
    for i, match in enumerate(matches[:10], 1):
        ticker = match.get("ticker", match.get("symbol", "???"))
        name = match.get("name", match.get("entity_name", ""))
        score = match.get("score", match.get("match_score", ""))
        print(f"    {i}. {ticker:<8} {name:<30} score={score}")

    # Analyze top 3
    top_tickers = []
    for match in matches[:3]:
        t = match.get("ticker", match.get("symbol"))
        if t:
            top_tickers.append(t.upper())

    if not top_tickers:
        print("\nNo tickers to analyze.")
        return

    config = _build_config(args)
    config["max_debate_rounds"] = 0
    config["max_risk_discuss_rounds"] = 0

    rows = []
    for i, ticker in enumerate(top_tickers, 1):
        _print_subheader(f"Quick Analysis: {ticker} ({i}/{len(top_tickers)})")
        try:
            state, decision = _run_pipeline(ticker, date, config, quiet=False)
            info = _extract_verdict_info(state, decision)
            info["ticker"] = ticker
            rows.append(info)
            print(f"  Verdict: {info['verdict']}")
        except Exception as e:
            print(f"  ERROR analyzing {ticker}: {e}")
            rows.append({
                "ticker": ticker,
                "verdict": "ERROR",
                "confidence": "N/A",
                "signal": "N/A",
                "top_risk": str(e)[:20],
            })

    _print_header(f"Preset '{preset_id}' Summary")
    _print_comparison_table(rows)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="TradingAgents-Pro -- Enhanced multi-agent trading framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py NVDA                              Full 18-agent analysis
  python run.py NVDA --quick                      Skip debate, fast verdict
  python run.py --compare NVDA AAPL TSLA          Compare multiple tickers
  python run.py --screen "oversold tech stocks"   NLP screener -> analysis
  python run.py NVDA --backtest                   Include backtest results
  python run.py --portfolio NVDA:40,AAPL:30,BTC:30  Portfolio analysis
  python run.py NVDA --demo                       Save + shareable report URL
  python run.py NVDA --depth deep                 Opus-powered deep forecast
  python run.py --preset oversold_bounce           Pre-built screener strategy
  python run.py --preset list                      Show available presets
""",
    )

    # Positional: ticker (optional because some modes don't need it)
    parser.add_argument(
        "ticker",
        nargs="?",
        default=None,
        help="Ticker symbol to analyze (e.g., NVDA, AAPL, BTC)",
    )

    # Analysis date
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Analysis date in YYYY-MM-DD format (default: today)",
    )

    # Quick mode
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip debate rounds for faster analysis (~30s)",
    )

    # Compare mode
    parser.add_argument(
        "--compare",
        nargs="+",
        metavar="TICKER",
        help="Compare multiple tickers side-by-side",
    )

    # Screen mode
    parser.add_argument(
        "--screen",
        type=str,
        metavar="QUERY",
        help="Natural-language screener query (e.g., 'oversold tech stocks')",
    )

    # Backtest mode
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Include Polaris backtest results after analysis",
    )

    # Portfolio mode
    parser.add_argument(
        "--portfolio",
        type=str,
        metavar="HOLDINGS",
        help="Portfolio analysis (e.g., 'NVDA:40,AAPL:30,BTC:30')",
    )

    # Demo mode
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Save report and generate shareable URL",
    )

    # Depth mode
    parser.add_argument(
        "--depth",
        type=str,
        choices=["standard", "deep"],
        default="standard",
        help="Analysis depth: 'standard' or 'deep' (uses most capable LLM)",
    )

    # Preset mode
    parser.add_argument(
        "--preset",
        type=str,
        metavar="PRESET_ID",
        help="Run a pre-built screener preset (use 'list' to see available)",
    )

    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse arguments and dispatch to the appropriate mode."""
    parser = build_parser()
    args = parser.parse_args()

    # Determine which mode to run
    if args.compare:
        mode_compare(args)
    elif args.screen:
        mode_screen(args)
    elif args.portfolio:
        mode_portfolio(args)
    elif args.preset:
        mode_preset(args)
    elif args.ticker:
        if args.backtest:
            mode_backtest(args)
        elif args.demo:
            mode_demo(args)
        else:
            mode_standard(args)
    else:
        # No ticker and no special mode -- show help
        parser.print_help()
        print()
        print("Tip: Run 'python run.py NVDA' to get started with a full analysis.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted. Partial results may have been saved.")
        sys.exit(130)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        print("Run with PYTHONDONTWRITEBYTECODE=1 for cleaner output.")
        sys.exit(1)
