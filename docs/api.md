# Fusion-Finance API Reference

## Core Modules

### `fusion_finance.modeling`

```python
from fusion_finance.modeling import FinancialModelingEngine, DCFModel, CompsAnalysis, AdvancedModelingEngine, LBOModel, DDMModel, MergerModel

# DCF Valuation
engine = FinancialModelingEngine()
model = await engine.build_dcf("Company", [100, 120, 140, 160])
result = model.calculate()
print(result["enterprise_value"], result["target_price"])

# Comps Analysis
comps = await engine.build_comps("Company", "Technology", ["Peer1", "Peer2"])

# Sensitivity Analysis
matrix = await engine.sensitivity_analysis(model, [0.08, 0.10, 0.12], [0.02, 0.03, 0.04])

# Monte Carlo Simulation
mc = await engine.monte_carlo(model, simulations=1000)

# LBO Model
adv = AdvancedModelingEngine()
lbo = await adv.build_lbo("Company", [100, 120, 140, 160, 180])
print(lbo.calculate())

# DDM & Merger
ddm = DDMModel(company="C", current_dividend=2.0, growth_rate=0.05, required_return=0.10)
merger = MergerModel(acquirer="A", target="T", acquirer_price=50, target_price=30)
```

### `fusion_finance.statements`

```python
from fusion_finance.statements import StatementAnalyzer, FinancialStatement

analyzer = StatementAnalyzer()
stmt = FinancialStatement(company="ABC", revenue=1000, gross_profit=400,
                          operating_income=200, net_income=150,
                          total_assets=2000, total_liabilities=800, equity=1200)
analysis = analyzer.calculate_metrics(stmt)
print(analysis.gross_margin, analysis.net_margin, analysis.roe)

# Balance sheet validation
issues = analyzer.validate_balance_sheet([stmt])

# AI analysis
result = await analyzer.analyze_statements("ABC", {"revenue": 1000})
```

### `fusion_finance.risk`

```python
from fusion_finance.risk import RiskComplianceEngine, RiskModelingEngine

# KYC
engine = RiskComplianceEngine()
kyc = await engine.kyc_screening("Company")
print(kyc.risk_level, kyc.risk_score)

# Credit assessment
credit = await engine.credit_assessment("Company", {"revenue": 1000})

# Compliance check
compliance = await engine.compliance_check("Contract text...")

# VaR Calculation
returns = [0.01, -0.02, 0.03, -0.01, 0.02]
var = RiskModelingEngine.calculate_var(returns, portfolio_value=1_000_000)
print(var.var_95, var.var_99)

# Monte Carlo VaR
mc_var = RiskModelingEngine.monte_carlo_var(1_000_000, 0.10, 0.20, simulations=1000)

# Stress test scenarios
scenarios = RiskModelingEngine.stress_test_scenarios()
```

### `fusion_finance.report`

```python
from fusion_finance.report import ReportGenerator
from fusion_finance.modeling import DCFModel, CompsAnalysis

gen = ReportGenerator()
dcf = DCFModel(company="C", revenue=[100, 120, 140])
dcf.calculate()

# Valuation report
report = gen.generate_valuation_report("Company", dcf)
gen.save_report(report, "~/Desktop/reports")

# PitchBook
pb = gen.generate_pitchbook("Company", dcf, "Technology")

# AI research report
research = await gen.generate_research_report("Company", "Tech", {"key": "data"})
```

### `fusion_finance.utils`

```python
from fusion_finance.utils import AuditTrail

audit = AuditTrail()
audit.record("user1", "dcf_calc", "modeling", "DCF for Company")
audit.record("user1", "report_gen", "report", "Generated report")
entries = audit.query(user="user1")
stats = audit.get_stats()
```

## CLI Reference

```bash
fusion-finance [OPTIONS] COMMAND [ARGS]
```

### Global Options

| Option | Description |
|--------|-------------|
| `--verbose`, `-v` | Verbose output |
| `--model`, `-m` | fusion-mlx model name |
| `--version` | Show version |

### Commands

#### `model dcf`

```bash
fusion-finance model dcf <company> <revenue_values...> [--wacc 0.10]
```

#### `statement analyze`

```bash
fusion-finance statement analyze <company> [--revenue 1000] [--net-income 150] [--total-assets 2000]
```

#### `risk kyc`

```bash
fusion-finance risk kyc <entity>
```

#### `report valuation`

```bash
fusion-finance report valuation <company> [--output ~/Desktop]
```

## Data Models

### `DCFModel`

| Field | Type | Description |
|-------|------|-------------|
| `company` | `str` | Company name |
| `forecast_years` | `int` | Forecast period (years) |
| `revenue` | `List[float]` | Revenue projections |
| `ebit_margin` | `List[float]` | EBIT margin per year |
| `wacc` | `float` | Weighted average cost of capital |
| `terminal_growth` | `float` | Terminal growth rate |
| `net_debt` | `float` | Net debt |
| `shares_outstanding` | `float` | Shares outstanding |
| `target_price` | `float` | Calculated target price |

### `VaRResult`

| Field | Type | Description |
|-------|------|-------------|
| `var_95` | `float` | 95% VaR |
| `var_99` | `float` | 99% VaR |
| `cvar_95` | `float` | 95% CVaR (expected shortfall) |
| `simulations` | `int` | Number of simulations |
| `portfolio_value` | `float` | Portfolio value |

### `AuditEntry`

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `float` | Unix timestamp |
| `user` | `str` | User identifier |
| `action` | `str` | Action performed |
| `module` | `str` | Module name |
| `details` | `str` | Action details |
| `status` | `str` | `success` or `failed` |