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
  <img src="https://img.shields.io/badge/tests-63%20passed-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-90%25-green" alt="Coverage">
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
| **LBO Model** | ✅ | ✅ | `modeling/advanced.py` |
| **DDM Model** | ✅ | ✅ | `modeling/advanced.py` |
| **Merger Model** | ✅ | ✅ | `modeling/advanced.py` |
| Financial Metrics | ✅ | ✅ | `statements/analyzer.py` |
| Balance Sheet Validation | ✅ | ✅ | `statements/analyzer.py` |
| KYC Screening | ✅ | ✅ | `risk/engine.py` |
| Credit Assessment | ✅ | ✅ | `risk/engine.py` |
| Compliance Check | ✅ | ✅ | `risk/engine.py` |
| **VaR Calculation** | ✅ | ✅ | `risk/advanced_risk.py` |
| **Monte Carlo VaR** | ✅ | ✅ | `risk/advanced_risk.py` |
| **Stress Testing** | ✅ | ✅ | `risk/advanced_risk.py` |
| Valuation Report | ✅ | ✅ | `report/reports.py` |
| PitchBook | ✅ | ✅ | `report/reports.py` |
| Research Report | ✅ | ✅ | `report/reports.py` |
| **Audit Trail** | ✅ | ✅ | `utils/audit.py` |
| **License** | Enterprise | ✅ **MIT (free)** | — |

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/dahai80/fusion-finance.git
cd fusion-finance

# Install
pip install -e .

# DCF Valuation
fusion-finance model dcf "Apple" 100 120 140 160

# Financial analysis
fusion-finance statement analyze "Apple" --revenue 1000 --net-income 150

# KYC screening
fusion-finance risk kyc "Company"

# Generate valuation report
fusion-finance report valuation "Apple" --output ./reports
```

---

## 📖 Modules

### 1. Financial Modeling (`modeling/`)

| Component | Description |
|-----------|-------------|
| `DCFModel` | Discounted cash flow valuation with terminal value |
| `CompsAnalysis` | Comparable company analysis with peer multiples |
| `LBOModel` | Leveraged buyout model with IRR/MOIC |
| `DDMModel` | Dividend discount model for fair value |
| `MergerModel` | Merger accretion/dilution analysis |
| `sensitivity_analysis()` | WACC vs growth rate sensitivity matrix |
| `monte_carlo()` | Monte Carlo simulation for valuation range |

### 2. Statement Analysis (`statements/`)

| Component | Description |
|-----------|-------------|
| `FinancialStatement` | Income statement, balance sheet, cash flow data |
| `FinancialAnalysis` | Calculated metrics: margins, ROE, ROA, debt ratio |
| `calculate_metrics()` | Compute financial ratios from raw data |
| `validate_balance_sheet()` | Check assets = liabilities + equity |
| `analyze_statements()` | AI-powered deep financial analysis |

### 3. Risk & Compliance (`risk/`)

| Component | Description |
|-----------|-------------|
| `KYCCheck` | KYC due diligence screening |
| `CreditAssessment` | Credit scoring and rating |
| `VaRResult` | Value at Risk calculation (95%/99%) |
| `StressTestResult` | Stress test scenario definitions |
| `calculate_var()` | Historical VaR from return series |
| `monte_carlo_var()` | Monte Carlo VaR simulation |
| `stress_test_scenarios()` | Predefined stress test scenarios |

### 4. Report Generation (`report/`)

| Component | Description |
|-----------|-------------|
| `generate_valuation_report()` | Professional DCF valuation report |
| `generate_pitchbook()` | Investment pitchbook template |
| `generate_research_report()` | AI-powered deep research report |
| `save_report()` | Save report to file |

### 5. Audit Trail (`utils/`)

| Component | Description |
|-----------|-------------|
| `AuditTrail` | JSONL-based audit logging |
| `record()` | Record audit entry with user/timestamp |
| `query()` | Query audit entries by user/action/module |
| `get_stats()` | Audit statistics summary |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    CLI (fusion-finance)                        │
│      model │ statement │ risk │ report                         │
├──────────────────────────────────────────────────────────────┤
│                    Engine Layer                                │
│  FinancialModeling │ StatementAnalyzer │ RiskCompliance        │
│  AdvancedModeling  │ RiskModelingEngine │ ReportGenerator      │
├──────────────────────────────────────────────────────────────┤
│                    AI Backend (fusion-mlx)                     │
│  HTTP → http://localhost:8000/v1/chat/completions             │
│  100% local, zero data upload                                │
└──────────────────────────────────────────────────────────────┘
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
```

---

## 🧪 Running Tests

```bash
pip install -e ".[test]"
pytest tests/ -v
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
  <img src="https://img.shields.io/badge/测试-63%20通过-brightgreen" alt="测试">
  <img src="https://img.shields.io/badge/覆盖率-90%25-green" alt="覆盖率">
</p>

---

## 📋 产品简介

**Fusion-Finance** 是一款本地 AI 金融分析平台，基于 `fusion-mlx` 构建，**100% 本地离线，数据不出境**，是国内环境下 Claude Financial 的合规替代方案。

### 对标 Claude Financial

| 能力 | Claude Financial | Fusion-Finance |
|------|----------------|----------------|
| 数据本地化 | ❌ 云端处理 | ✅ **100% 本地** |
| 国内可访问 | ❌ 被屏蔽 | ✅ **完全可用** |
| 开源免费 | ❌ 企业订阅 | ✅ **MIT 协议** |
| DCF 估值 | ✅ | ✅ |
| 可比公司分析 | ✅ | ✅ |
| LBO 杠杆收购 | ✅ | ✅ |
| DDM 股利贴现 | ✅ | ✅ |
| 并购模型 | ✅ | ✅ |
| 敏感性分析 | ✅ | ✅ |
| 蒙特卡洛模拟 | ✅ | ✅ |
| 财务指标 | ✅ | ✅ |
| 资产负债表校验 | ✅ | ✅ |
| KYC 尽调 | ✅ | ✅ |
| 信用评估 | ✅ | ✅ |
| 合规审查 | ✅ | ✅ |
| VaR 风险价值 | ✅ | ✅ |
| 压力测试 | ✅ | ✅ |
| 估值报告 | ✅ | ✅ |
| PitchBook | ✅ | ✅ |
| 投研报告 | ✅ | ✅ |
| 审计日志 | ✅ | ✅ |

### 快速开始

```bash
# 安装
git clone https://github.com/dahai80/fusion-finance.git
cd fusion-finance
pip install -e .

# DCF 估值
fusion-finance model dcf "公司A" 100 120 140 160

# 财务分析
fusion-finance statement analyze "公司A" --revenue 1000 --net-income 150

# KYC 尽调
fusion-finance risk kyc "目标公司"

# 生成估值报告
fusion-finance report valuation "公司A" --output ./reports
```

### 五大模块

| 模块 | 功能 | 关键能力 |
|------|------|----------|
| 📊 **财务建模** | DCF/LBO/DDM/并购/敏感性/蒙特卡洛 | 6 种估值模型 |
| 📋 **财报分析** | 指标计算/勾稽校验/AI 分析 | 10+ 财务指标 |
| 🛡️ **风控合规** | KYC/信用评估/VaR/压力测试 | 4 大风控模型 |
| 📄 **报告生成** | 估值报告/PitchBook/投研报告 | 3 种报告模板 |
| 🔍 **审计日志** | 操作记录/查询/统计 | JSONL 持久化 |

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