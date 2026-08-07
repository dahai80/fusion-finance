<div align="center">
  <h1>💰 Fusion-Finance</h1>
  <p><strong>Local AI-powered financial analysis platform for macOS Apple Silicon</strong></p>
  <p><em>100% offline, zero data upload, powered by fusion-mlx. The domestic alternative to Claude Financial.</em></p>
  <p><a href="./README_CN.md">中文文档</a></p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/macOS-Apple%20Silicon-brightgreen" alt="macOS">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="License">
  <img src="https://img.shields.io/badge/AI-MLX%20Native-orange" alt="MLX">
  <img src="https://img.shields.io/badge/Offline-First-important" alt="Offline">
  <img src="https://img.shields.io/badge/tests-497%20passed-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-88%25-brightgreen" alt="Coverage">
  <img src="https://img.shields.io/badge/API-FastAPI-blue" alt="API">
</p>

---

## 📋 Overview

**Fusion-Finance** is a local AI-powered financial analysis platform, designed as a domestic alternative to **Claude Financial (CFS)**. Built on `fusion-mlx`, it provides comprehensive financial modeling, statement analysis, risk management, and report generation — all **100% offline** with zero data uploaded.

v0.5.2: **Production acceptance hardening** — 4 verified bug fixes (MACD IndexError on short series, stress-test mitigations type, export fallback return paths, start.sh health path), dedicated exception + regression test suites (+25 tests, 522 total, 86% coverage), `exceptions.py` coverage 44%→100%.

v0.5.1: **Port migration** — service port 8200→11446 (issue #4), MLX base URL 11434→11432 (issue #3), aligning with the fusion ecosystem 114xx port allocation.

v0.5.0: **Custom exception hierarchy** (6 typed error responses), **Dashboard aggregation endpoints** (company overview, market overview, service status), **Ruff lint clean**, **Test consolidation**, **fusion-studio GUI integration** (FinanceBridge + 8 views, PR [#87](https://github.com/dahai80/fusion-studio/pull/87)).

### Claude Financial Comparison

| Capability | Claude Financial | Fusion-Finance | Module |
|------------|-----------------|----------------|--------|
| **Data residency** | ❌ Cloud-only | ✅ **100% local** | — |
| **China accessible** | ❌ Blocked | ✅ **Fully accessible** | — |
| DCF Valuation | ✅ | ✅ | `modeling/engine.py` |
| Comps Analysis | ✅ | ✅ | `modeling/engine.py` |
| Sensitivity Analysis | ✅ | ✅ | `modeling/engine.py` |
| Monte Carlo Simulation | ✅ | ✅ | `modeling/engine.py` |
| **Interactive DCF Session** | ❌ | ✅ | `modeling/engine.py` |
| **Scenario Manager** | ❌ | ✅ | `modeling/scenarios.py` |
| **LBO Model** | ✅ | ✅ | `modeling/advanced.py` |
| **DDM Model** | ✅ | ✅ | `modeling/advanced.py` |
| **Merger Model** | ✅ | ✅ | `modeling/advanced.py` |
| **APV / EVA / RI** | ❌ | ✅ | `modeling/valuation.py` |
| **Portfolio Optimizer** | ❌ | ✅ | `modeling/portfolio.py` |
| **Black-Litterman** | ❌ | ✅ | `modeling/portfolio.py` |
| **Bond / Yield Curve** | ❌ | ✅ | `modeling/portfolio.py` |
| **Technical Indicators** | ❌ | ✅ | `modeling/portfolio.py` |
| Financial Metrics | ✅ | ✅ | `statements/analyzer.py` |
| Balance Sheet Validation | ✅ | ✅ | `statements/analyzer.py` |
| **Statement Normalizer** | ❌ | ✅ | `statements/normalizer.py` |
| **Financial Screener** | ❌ | ✅ | `statements/screener.py` |
| KYC Screening | ✅ | ✅ | `risk/engine.py` |
| Credit Assessment | ✅ | ✅ | `risk/engine.py` |
| Compliance Check | ✅ | ✅ | `risk/engine.py` |
| **Sanctions Screening** | ❌ | ✅ | `risk/sanctions.py` |
| **Entity Resolution** | ❌ | ✅ | `risk/entity_resolution.py` |
| **VaR Calculation** | ✅ | ✅ | `risk/advanced_risk.py` |
| **Stress Testing** | ✅ | ✅ | `risk/advanced_risk.py` |
| Valuation Report | ✅ | ✅ | `report/reports.py` |
| PitchBook | ✅ | ✅ | `report/reports.py` |
| Research Report | ✅ | ✅ | `report/reports.py` |
| **AI Copilot** | ❌ | ✅ | `api/routes/copilot.py` |
| **SVG Charts** | ❌ | ✅ | `api/routes/chart.py` |
| **Project Management** | ❌ | ✅ | `api/routes/project.py` |
| **Market Feed Simulator** | ❌ | ✅ | `data/market_feed.py` |
| **Compute Cache** | ❌ | ✅ | `data/cache.py` |
| **Audit Trail** | ✅ | ✅ | `utils/audit.py` |
| **License** | Enterprise | ✅ **Apache 2.0 (free)** | — |

---

## 🚀 Quick Start

```bash
# Install
pip install -e "."

# CLI Usage
fusion-finance model dcf "Apple" 100 120 140 160
fusion-finance statement analyze "Apple" --revenue 1000
fusion-finance risk kyc "Company"
fusion-finance report valuation "Apple" -o ./reports

# Start API server
fusion-finance serve --port 11446
# Or use start.sh
./start.sh start
```

---

## 🌐 API Server

### Start / Stop

```bash
./start.sh start    # Start on port 11446
./start.sh stop     # Stop
./start.sh restart  # Restart
./start.sh status   # Check status
./start.sh log      # View logs
```

### API Endpoints

| Prefix | Module | Endpoints |
|--------|--------|-----------|
| `/api/v1/` | Health | `GET /` health, `GET /ready` readiness |
| `/api/v1/modeling` | Modeling | DCF, comps, sensitivity, Monte Carlo, LBO, DDM, merger, APV, EVA, RI, portfolio, sessions, scenarios |
| `/api/v1/statements` | Statements | analyze, metrics, validate, screener, screener-presets, normalize, trend, standards |
| `/api/v1/risk` | Risk | KYC, credit, compliance, VaR, stress test |
| `/api/v1/report` | Reports | valuation, pitchbook, research, export, formats |
| `/api/v1/copilot` | AI Copilot | chat, history, sessions |
| `/api/v1/chart` | Charts | candlestick, heatmap, waterfall, sensitivity tornado |
| `/api/v1/project` | Projects | CRUD, snapshots, versions, diff, history, export |
| `/api/v1/data` | Data | import, validate balance, validate completeness, cache |
| `/api/v1/audit` | Audit | record, query, stats, file-stats |
| `/api/v1/dashboard` | Dashboard | company overview, market overview, service status |
| `/ws` | WebSocket | `/ws/copilot` streaming chat, `/ws/modeling/progress` |
| `/events` | SSE | `/events/insights`, `/events/alerts` streams, `/events/publish` |

### Example API Calls

```bash
# Calculate DCF
curl -X POST http://localhost:11446/api/v1/modeling/dcf/calculate \
  -H "Content-Type: application/json" \
  -d '{"company":"Apple","revenue":[100,120,140],"wacc":0.10,"terminal_growth":0.03}'

# Screen stocks with growth preset
curl -X POST http://localhost:11446/api/v1/statements/screener \
  -H "Content-Type: application/json" \
  -d '{"filters":{"preset":"growth"},"limit":5}'

# Normalize A-stock financial data
curl -X POST http://localhost:11446/api/v1/statements/normalize \
  -H "Content-Type: application/json" \
  -d '{"data":{"营业收入":1000,"净利润":200},"standard":"A","company":"TestCo","period":"2024"}'

# Health check
curl http://localhost:11446/api/v1/

# Dashboard: company overview
curl -X POST http://localhost:11446/api/v1/dashboard/company \
  -H "Content-Type: application/json" \
  -d '{"company":"Apple","revenue":[100,120,140],"ebit_margin":[0.2,0.22,0.24],"wacc":0.10}'

# Dashboard: market overview
curl http://localhost:11446/api/v1/dashboard/market?preset=quality&limit=5

# Dashboard: service status
curl http://localhost:11446/api/v1/dashboard/status

# AI Copilot chat
curl -X POST http://localhost:11446/api/v1/copilot/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"分析Apple的DCF估值","session_id":"demo"}'
```

Swagger docs: `http://localhost:11446/docs`

---

## 📖 Modules

### 1. Financial Modeling (`modeling/`)

| Component | Description |
|-----------|-------------|
| `DCFModel` | Discounted cash flow valuation with terminal value |
| `CompsAnalysis` | Comparable company analysis with peer multiples |
| `InteractiveDCFSession` | Real-time slider-driven DCF recalculation |
| `ScenarioManager` | Bear/Base/Bull scenario comparison |
| `LBOModel` | Leveraged buyout model with IRR/MOIC |
| `DDMModel` | Dividend discount model for fair value |
| `MergerModel` | Merger accretion/dilution analysis |
| `APVModel` | Adjusted present value |
| `EVAModel` | Economic value added |
| `RIModel` | Residual income model |
| `PortfolioOptimizer` | Mean-variance portfolio optimization |
| `BlackLittermanOptimizer` | Black-Litterman posterior returns + mean-variance |
| `Bond` | Bond pricing and yield calculation |
| `YieldCurve` | Nelson-Siegel yield curve with random search calibration |
| `TechnicalIndicators` | SMA, EMA, RSI, MACD, Bollinger Bands |

### 2. Statement Analysis (`statements/`)

| Component | Description |
|-----------|-------------|
| `FinancialStatement` | Income statement, balance sheet, cash flow data |
| `FinancialAnalysis` | Calculated metrics: margins, ROE, ROA, debt ratio |
| `calculate_metrics()` | Compute financial ratios from raw data |
| `validate_balance_sheet()` | Check assets = liabilities + equity |
| `analyze_statements()` | AI-powered deep financial analysis |
| `StatementNormalizer` | Multi-standard normalization (A股/港股/US GAAP), YoY/QoQ, trend analysis |
| `FinancialScreener` | Multi-dimensional stock screening with 4 presets (value/growth/dividend/quality) |

### 3. Risk & Compliance (`risk/`)

| Component | Description |
|-----------|-------------|
| `KYCCheck` | KYC due diligence screening |
| `CreditAssessment` | Credit scoring and rating |
| `SanctionsEngine` | Sanctions list matching (Levenshtein + keyword + exact) |
| `EntityGraph` | Entity resolution, UBO tracing, PEP scanning |
| `VaRResult` | Value at Risk calculation (95%/99%) |
| `StressTestResult` | Stress test scenario definitions |
| `calculate_var()` | Historical VaR from return series |
| `monte_carlo_var()` | Monte Carlo VaR simulation |
| `stress_test_scenarios()` | Predefined stress test scenarios |

### 4. Report Generation (`report/`)

| Component | Description |
|-----------|-------------|
| `ReportGenerator` | Markdown report generation with AI research |
| `ReportFormatter` | Jinja2 template rendering + multi-format export |
| Templates | `valuation.html`, `pitchbook.html`, `research.html`, `board_material.html` |
| Export formats | HTML, PDF, PPTX, XLSX, JSON, Markdown |
| `save_report()` | Save report to file |

### 5. AI Copilot (`copilot/`)

| Component | Description |
|-----------|-------------|
| `CopilotEngine` | ReAct loop engine with max 3 tool rounds |
| `ToolRegistry` | 18 financial tools (DCF, comps, sensitivity, VaR, BL, sanctions, bond, etc.) |
| `ConversationMemory` | Session-based memory (max 50 msgs, 100 sessions) |
| `chat()` | Full copilot chat with tool execution |
| `chat_stream()` | AsyncIterator for WebSocket streaming |
| Scenario Prompts | 5 scenario-aware system prompts (modeling, risk, report, statements, data) |
| Insight Prompts | Proactive detection (valuation_alert, risk_alert, data_alert) |

### 6. Chart Rendering (`chart/`)

| Component | Description |
|-----------|-------------|
| `ChartRenderer` | SVG chart rendering engine (facade) |
| `render_candlestick()` | K-line (OHLCV) chart (standalone module) |
| `render_heatmap()` | Sensitivity matrix heatmap (standalone module) |
| `render_waterfall()` | Bridge/waterfall chart (standalone module) |
| `render_sensitivity_tornado()` | Tornado chart for sensitivity analysis (standalone module) |

### 7. Data Adapter (`data/`)

| Component | Description |
|-----------|-------------|
| `DataAdapter` | Unified CSV import + validation + cache |
| `CSVLoader` | CSV/TSV loading with auto-encoding and delimiter detection |
| `DataCache` | LRU cache with TTL expiration |
| `DataValidator` | Row validation, balance sheet check, completeness scoring |
| `MarketFeedSimulator` | A-stock/HK-stock simulated quotes, OHLCV generation |
| `compute_cache` | Decorator-based LRU cache with TTL for expensive computations |

### 8. Shared Utilities (`utils/`)

| Component | Description |
|-----------|-------------|
| `AuditTrail` | JSONL-based audit logging with structured query & statistics |
| `parse_json()` | Unified JSON parsing with regex fallback |

### 9. Project Management (`project/`)

| Component | Description |
|-----------|-------------|
| `ProjectManager` | CRUD, snapshot, restore for analysis projects |
| `VersionControl` | SHA256 hashing, diff/patch, cherry-pick, history summary |
| `ProjectExporter` | JSON/ZIP export and import |

### 10. API Middleware & SSE (`api/`)

| Component | Description |
|-----------|-------------|
| `AuditMiddleware` | Auto-records every request to AuditTrail |
| `RateLimitMiddleware` | Per-IP sliding window rate limiting |
| `APIKeyMiddleware` | API key authentication with exempt paths |
| `EventBus` | Pub/sub event bus for SSE streaming |
| SSE Routes | `/events/insights`, `/events/alerts`, `/events/publish` |

### 11. Configuration (`config.py`)

| Setting | Default | Env Var |
|---------|---------|---------|
| Host | `0.0.0.0` | `FUSION_FINANCE_HOST` |
| Port | `11446` | `FUSION_FINANCE_PORT` |
| MLX URL | `http://localhost:11432/v1` | `FUSION_FINANCE_MLX_URL` |
| Model | `qwen3.5-9b` | `FUSION_FINANCE_MODEL` |
| Data dir | `~/.fusion/finance` | `FUSION_FINANCE_DATA_DIR` |

---

## 🏗️ Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                 CLI / API Server                               │
│   Click CLI (fusion-finance)  │  FastAPI (localhost:11446)     │
├───────────────────────────────────────────────────────────────┤
│               API Middleware & SSE                             │
│  AuditMiddleware │ RateLimitMiddleware │ APIKeyMiddleware      │
│  EventBus + SSE (insights / alerts streams)                   │
├───────────────────────────────────────────────────────────────┤
│                    Engine Layer                                │
│  FinancialModeling │ StatementAnalyzer │ RiskCompliance        │
│  AdvancedModeling  │ RiskModelingEngine │ ReportGenerator       │
│  ReportFormatter   │ ProjectManager     │ VersionControl        │
│  InteractiveDCF    │ ScenarioManager    │ CopilotEngine         │
│  ChartRenderer     │ DataAdapter        │ ConversationMemory    │
│  StatementNormalizer│ FinancialScreener │ Copilot Prompts       │
│  Chart Modules (4)                                            │
├───────────────────────────────────────────────────────────────┤
│                 AI Backend (fusion-mlx)                        │
│  HTTP → http://localhost:11432/v1/chat/completions            │
│  MLXClient with retry + httpx fallback                        │
│  100% local, zero data upload                                 │
└───────────────────────────────────────────────────────────────┘
```

---

## 🔧 CLI Reference

```bash
fusion-finance [OPTIONS] COMMAND [ARGS]

Options:
  --verbose, -v    Verbose output
  --model, -m      fusion-mlx model name
  --version        Show version

Commands:
  model dcf <company> <revenue...>        DCF valuation
  statement analyze <company> [options]   Financial metrics
  risk kyc <entity>                       KYC screening
  report valuation <company> [options]    Generate valuation report
  serve [--host] [--port] [--reload]      Start API server
```

---

## 🧪 Running Tests

```bash
pip install -e ".[test]"
pytest tests/ -v                              # All tests (497 passed)
pytest tests/test_core.py -v                  # Core tests
pytest tests/test_api.py -v                   # API endpoint tests
pytest tests/test_coverage.py -v              # Advanced model tests
pytest tests/test_phase2.py -v                # Phase 2: copilot, chart, data
pytest tests/test_phase3.py -v                # Phase 3: report templates, project, audit
pytest tests/test_phase3plus.py -v            # Phase 3+: prompts, middleware, SSE, chart modules
pytest tests/test_phase5.py -v                # Phase 5: BL, yield curve, sanctions, entity, market feed
pytest tests/test_integration.py -v           # Integration: WS, CLI, normalizer, screener, scenarios, tools
pytest tests/ --cov=fusion_finance --cov-report=html
```

---

## 🔒 Security & Compliance

- **100% Local Offline** — Zero data upload, no privacy leakage
- **No Telemetry** — No analytics, no phoning home
- **Data Sovereignty** — All processing on local machine
- **Audit Trail** — Complete audit logging for compliance
- **Compliant with Chinese regulations** — No cross-border data transfer

---

## 📄 License

Apache License 2.0. See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Fusion-Finance — Local AI Finance. Zero Upload, Full Compliance.</strong>
</p>
<p align="center">
  <sub>Built with ❤️ and fusion-mlx</sub>
</p>
