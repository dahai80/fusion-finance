# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fusion-Finance is a local AI-powered financial analysis platform — a domestic alternative to Claude Financial. 100% offline, zero data upload, powered by fusion-mlx. All LLM inference routes through `http://localhost:11434/v1` via `fusion-core`'s `FusionMLXClient`.

## Build & Test

```bash
cd /Users/dahai/fusion
source .venv/bin/activate
cd fusion-finance

pip install -e ".[test]"          # Install with test deps
pytest tests/ -v                  # Run all tests
pytest tests/test_core.py -v      # Core tests only
pytest tests/test_coverage.py -v  # Coverage tests (advanced models, portfolio, bond, tech indicators)
pytest tests/ --cov=fusion_finance --cov-report=html
```

Single test: `pytest tests/test_core.py::TestDCFModel::test_dcf_calculation -v`

## CLI

Entry point: `fusion-finance` → `fusion_finance.cli:main`

```bash
fusion-finance model dcf "Apple" 100 120 140 160       # DCF valuation
fusion-finance statement analyze "Apple" --revenue 1000  # Financial metrics
fusion-finance risk kyc "Company"                        # KYC screening
fusion-finance report valuation "Apple" -o ./reports     # Valuation report
```

CLI uses Click groups (`model`, `statement`, `risk`, `report`). AI-backed commands are async — they use `asyncio.run()` wrappers in the CLI layer.

## Architecture

### Three-Layer Stack

1. **CLI** (`cli.py`) — Click commands, `asyncio.run()` bridges to async engine methods
2. **Engine Layer** — Four domain modules, each with an `*Engine` class that accepts `MLXClient` via constructor injection
3. **AI Backend** — `fusion-mlx` at `localhost:11434`, accessed through `MLXClient` wrapper in `ai_client.py`

### Module Structure

```
fusion_finance/
├── ai_client.py          # MLXClient — thin wrapper around fusion_core.FusionMLXClient
├── cli.py                # Click CLI entry point
├── modeling/
│   ├── engine.py         # FinancialModelingEngine, DCFModel, CompsAnalysis
│   ├── advanced.py       # AdvancedModelingEngine, LBOModel, DDMModel, MergerModel
│   ├── valuation.py      # APVModel, EVAModel, RIModel (pure dataclass models, no AI)
│   ├── portfolio.py      # PortfolioOptimizer, BlackLittermanOptimizer, Bond, NelsonSiegelCurve, TechnicalIndicators
│   └── scenarios.py      # ScenarioManager (bear/base/bull)
├── statements/
│   └── analyzer.py       # StatementAnalyzer, FinancialStatement, FinancialAnalysis
├── risk/
│   ├── engine.py         # RiskComplianceEngine, KYCCheck, CreditAssessment
│   ├── advanced_risk.py  # RiskModelingEngine, VaRResult, StressTestResult (pure math)
│   ├── sanctions.py      # SanctionsEngine (Levenshtein + keyword + exact matching)
│   └── entity_resolution.py  # EntityGraph, UBO tracing, PEP scanning
├── report/
│   └── reports.py        # ReportGenerator — Markdown report templates + AI research
├── copilot/
│   ├── engine.py         # CopilotEngine, ToolRegistry, ConversationMemory
│   └── prompts.py        # Scenario prompts (5), insight prompts (3), build_system_prompt()
├── chart/
│   ├── renderer.py       # ChartRenderer facade
│   ├── heatmap.py        # render_heatmap()
│   ├── candlestick.py    # render_candlestick()
│   ├── waterfall.py      # render_waterfall()
│   └── sensitivity.py    # render_sensitivity_tornado()
├── data/
│   ├── adapter.py        # DataAdapter, CSVLoader, DataValidator
│   ├── market_feed.py    # MarketFeedSimulator (A-stock/HK-stock simulated quotes)
│   └── cache.py          # compute_cache decorator (LRU + TTL)
├── project/
│   └── manager.py        # ProjectManager, VersionControl, ProjectExporter
├── api/
│   ├── app.py            # FastAPI app with middleware stack
│   ├── middleware.py      # AuditMiddleware, RateLimitMiddleware, APIKeyMiddleware
│   ├── sse.py            # EventBus, SSE routes (/events/insights, /events/alerts)
│   └── routes/           # API route modules (copilot, chart, project, data, audit)
└── utils/
    └── audit.py          # AuditTrail — JSONL-based audit logging to ~/.fusion/finance/
```

### Key Patterns

- **MLXClient injection**: Every engine class accepts `Optional[MLXClient]` in `__init__`, defaulting to `MLXClient()`. Tests inject a mock with `chat = AsyncMock(return_value='{"test":"ok"}')`.
- **Dual-path computation**: Models have pure `calculate()` methods (synchronous, deterministic) and AI-augmented `build_*()` methods (async, call LLM for parameter estimation). If LLM fails, `build_*()` falls back to pure computation with defaults.
- **_parse_json()**: Repeated utility in each engine — strips markdown fences (`\`\`\`json ... \`\`\``) then `json.loads()`. Returns `None` on failure.
- **Dataclass models**: All financial models (DCFModel, LBOModel, Bond, etc.) are `@dataclass` with a `calculate() -> Dict` method. They carry both input fields and output fields on the same object.

### AI-Dependent vs Pure-Math Code

AI-dependent (requires fusion-mlx running):
- `FinancialModelingEngine.build_dcf()`, `build_comps()`, `sensitivity_analysis()`, `monte_carlo()`
- `AdvancedModelingEngine.build_lbo()`
- `StatementAnalyzer.analyze_statements()`
- `RiskComplianceEngine.kyc_screening()`, `credit_assessment()`, `compliance_check()`
- `ReportGenerator.generate_research_report()`

Pure math (no AI needed, runs offline):
- All `*.calculate()` methods on dataclass models
- `PortfolioOptimizer`, `BlackLittermanOptimizer`, `Bond`, `NelsonSiegelCurve`, `TechnicalIndicators` (portfolio.py)
- `APVModel`, `EVAModel`, `RIModel` (valuation.py)
- `SanctionsEngine` screening (sanctions.py)
- `EntityGraph` resolution, UBO/PEP tracing (entity_resolution.py)
- `RiskModelingEngine.calculate_var()`, `monte_carlo_var()`, `stress_test_scenarios()`
- `MarketFeedSimulator` quote generation (market_feed.py)
- `compute_cache` decorator (cache.py)
- `StatementAnalyzer.calculate_metrics()`, `validate_balance_sheet()`
- `ReportGenerator.generate_valuation_report()`, `generate_pitchbook()`, `save_report()`
- `AuditTrail` operations

## Dependencies

- `fusion-core>=0.1.0` — provides `FusionMLXClient` (the only AI interface)
- `httpx>=0.27.0`, `pydantic>=2.0.0`
- `click` (implicit, used by CLI)
- Test: `pytest`, `pytest-asyncio` (`asyncio_mode=auto`), `pytest-cov`
- Python ≥3.11, setuptools build backend

## Test Conventions

- Core test files: `test_core.py`, `test_coverage.py`, `test_api.py`
- Phase test files: `test_phase2.py` (copilot, chart, data), `test_phase3.py` (report templates, project, audit), `test_phase3plus.py` (prompts, middleware, SSE, chart modules), `test_phase5.py` (BL, yield curve, sanctions, entity, market feed, batch DCF, cache)
- Coverage boost: `test_coverage_boost.py` (scenarios, tools, formatter, API routes)
- 308 tests total, 80%+ coverage
- AI-dependent tests use `MockMLX` with `chat = AsyncMock(return_value='{"test":"ok"}')` — they don't require fusion-mlx running
- Pure math tests call `.calculate()` directly
- API route tests use `httpx.AsyncClient` with `ASGITransport(app=create_app())`
