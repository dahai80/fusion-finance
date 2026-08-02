<div align="center">
  <h1>💰 Fusion-Finance</h1>
  <p><strong>Local AI-powered financial analysis platform for macOS Apple Silicon</strong></p>
  <p><em>100% offline, zero data upload, powered by fusion-mlx. The domestic alternative to Claude Financial.</em></p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/macOS-Apple%20Silicon-brightgreen" alt="macOS">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/AI-MLX%20Native-orange" alt="MLX">
  <img src="https://img.shields.io/badge/Offline-First-important" alt="Offline">
  <img src="https://img.shields.io/badge/tests-497%20passed-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-88%25-brightgreen" alt="Coverage">
  <img src="https://img.shields.io/badge/API-FastAPI-blue" alt="API">
</p>

---

## 📋 Overview

**Fusion-Finance** is a local AI-powered financial analysis platform, designed as a domestic alternative to **Claude Financial (CFS)**. Built on `fusion-mlx`, it provides comprehensive financial modeling, statement analysis, risk management, and report generation — all **100% offline** with zero data uploaded.

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
| **License** | Enterprise | ✅ **MIT (free)** | — |

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
fusion-finance serve --port 8200
# Or use start.sh
./start.sh start
```

---

## 🌐 API Server

Fusion-Finance v0.5.0 adds **custom exception hierarchy** (typed errors with structured JSON responses), **dashboard aggregation endpoints** (company overview, market overview, service status), **ruff lint clean** (0 issues), and **test consolidation** (merged coverage_boost + phase6 → integration). Previous v0.4.0: financial screener (4 presets), statement normalizer (A股/港股/US GAAP), 6 copilot tools, 88% coverage.

### Start / Stop

```bash
./start.sh start    # Start on port 8200
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
curl -X POST http://localhost:8200/api/v1/modeling/dcf/calculate \
  -H "Content-Type: application/json" \
  -d '{"company":"Apple","revenue":[100,120,140],"wacc":0.10,"terminal_growth":0.03}'

# Screen stocks with growth preset
curl -X POST http://localhost:8200/api/v1/statements/screener \
  -H "Content-Type: application/json" \
  -d '{"filters":{"preset":"growth"},"limit":5}'

# Normalize A-stock financial data
curl -X POST http://localhost:8200/api/v1/statements/normalize \
  -H "Content-Type: application/json" \
  -d '{"data":{"营业收入":1000,"净利润":200},"standard":"A","company":"TestCo","period":"2024"}'

# Health check
curl http://localhost:8200/api/v1/

# Dashboard: company overview
curl -X POST http://localhost:8200/api/v1/dashboard/company \
  -H "Content-Type: application/json" \
  -d '{"company":"Apple","revenue":[100,120,140],"ebit_margin":[0.2,0.22,0.24],"wacc":0.10}'

# Dashboard: market overview
curl http://localhost:8200/api/v1/dashboard/market?preset=quality&limit=5

# Dashboard: service status
curl http://localhost:8200/api/v1/dashboard/status

# AI Copilot chat
curl -X POST http://localhost:8200/api/v1/copilot/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"分析Apple的DCF估值","session_id":"demo"}'
```

Swagger docs: `http://localhost:8200/docs`

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
| Port | `8200` | `FUSION_FINANCE_PORT` |
| MLX URL | `http://localhost:11434/v1` | `FUSION_FINANCE_MLX_URL` |
| Model | `qwen3.5-9b` | `FUSION_FINANCE_MODEL` |
| Data dir | `~/.fusion/finance` | `FUSION_FINANCE_DATA_DIR` |

---

## 🏗️ Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                 CLI / API Server                               │
│   Click CLI (fusion-finance)  │  FastAPI (localhost:8200)     │
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
│  HTTP → http://localhost:11434/v1/chat/completions            │
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
pytest tests/test_phase2.py -v               # Phase 2: copilot, chart, data
pytest tests/test_phase3.py -v               # Phase 3: report templates, project, audit
pytest tests/test_phase3plus.py -v          # Phase 3+: prompts, middleware, SSE, chart modules
pytest tests/test_phase5.py -v               # Phase 5: BL, yield curve, sanctions, entity, market feed
pytest tests/test_integration.py -v          # Integration: WS, CLI, normalizer, screener, scenarios, tools
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

MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Fusion-Finance — Local AI Finance. Zero Upload, Full Compliance.</strong>
</p>
<p align="center">
  <sub>Built with ❤️ and fusion-mlx</sub>
</p>

---

<br>

<div align="center">
  <h1>💰 Fusion-Finance</h1>
  <p><strong>本地 AI 金融分析平台 — macOS Apple Silicon 原生</strong></p>
  <p><em>100% 本地离线，数据不出境，基于 fusion-mlx。国内 Claude Financial 替代方案。</em></p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/macOS-Apple%20Silicon-brightgreen" alt="macOS">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="许可证">
  <img src="https://img.shields.io/badge/AI-MLX%20Native-orange" alt="MLX">
  <img src="https://img.shields.io/badge/离线优先-核心特性-important" alt="离线优先">
  <img src="https://img.shields.io/badge/测试-497%20通过-brightgreen" alt="测试">
  <img src="https://img.shields.io/badge/覆盖率-88%25-brightgreen" alt="覆盖率">
  <img src="https://img.shields.io/badge/API-FastAPI-blue" alt="API">
</p>

---

## 📋 产品简介

**Fusion-Finance** 是一款本地 AI 金融分析平台，基于 `fusion-mlx` 构建，**100% 本地离线，数据不出境**，是国内环境下 Claude Financial 的合规替代方案。

v0.5.0 新增：**自定义异常体系**（6类结构化错误响应）、**仪表盘聚合端点**（公司全景、市场概览、服务状态）、**Ruff 零告警**、**测试整合**（合并为 integration 测试）、**fusion-studio GUI 集成**（FinanceBridge + 8 视图 + Sidebar 注册，PR [#87](https://github.com/dahai80/fusion-studio/pull/87)）。v0.4.0：选股器（4策略）、财报标准化（三准则互转）、6个 Copilot 工具、88%覆盖率。

### 快速开始

```bash
# 安装
pip install -e "."

# CLI 使用
fusion-finance model dcf "公司A" 100 120 140 160
fusion-finance statement analyze "公司A" --revenue 1000
fusion-finance risk kyc "目标公司"
fusion-finance report valuation "公司A" -o ./reports

# 启动 API 服务
fusion-finance serve --port 8200
# 或使用 start.sh
./start.sh start
```

### API 服务

```bash
./start.sh start     # 启动 (端口 8200)
./start.sh stop      # 停止
./start.sh status    # 查看状态
./start.sh log       # 查看日志
```

API 文档：`http://localhost:8200/docs`

### 九大模块

| 模块 | 功能 | 关键能力 |
|------|------|----------|
| 📊 **财务建模** | DCF/LBO/DDM/并购/敏感性/蒙特卡洛 | 15 种模型 + Black-Litterman + 收益率曲线 |
| 📋 **财报分析** | 指标计算/勾稽校验/AI 分析/标准化/选股 | 10+ 财务指标 + 三准则互转 + 4 策略筛选 |
| 🛡️ **风控合规** | KYC/信用评估/制裁名单/实体解析/VaR/压力测试 | 6 大风控模型 |
| 📄 **报告生成** | 估值报告/PitchBook/投研报告/董事会材料 | 4 种模板 + 6 种格式导出 |
| 🤖 **AI Copilot** | 自然语言交互/工具调用/场景提示 | ReAct 模式 + 18 工具 + 5 场景 |
| 📈 **图表渲染** | K线/热力图/瀑布图/龙卷风图 | 模块化 SVG 渲染 |
| 📥 **数据适配** | CSV导入/验证/缓存/行情模拟/计算缓存 | LRU + TTL + A股/港股模拟 |
| 🔍 **审计日志** | 操作记录/查询/统计 | JSONL 持久化 + 结构化查询 |
| 📁 **项目管理** | CRUD/快照/版本/导出 | SHA256 版本控制 + ZIP 导出 |
| 🔐 **API 中间件** | 审计/限流/认证/SSE 事件流 | 自动审计记录 + 实时推送 |

### 测试

```bash
pip install -e ".[test]"
pytest tests/ -v
pytest tests/ --cov=fusion_finance --cov-report=html
```

### 安全合规

- **100% 本地离线** — 零数据上传，零隐私泄露
- **无遥测** — 无埋点、无回传
- **数据主权** — 所有处理在本地完成
- **审计日志** — 完整操作记录
- **符合国内法规** — 无跨境数据传输

### 开源协议

MIT License
