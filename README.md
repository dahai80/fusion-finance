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
  <img src="https://img.shields.io/badge/tests-23%20passed-brightgreen" alt="Tests">
</p>

---

## 📋 Overview

**Fusion-Finance** is a local AI-powered financial analysis platform, designed as a domestic alternative to **Claude Financial (CFS)**. Built on `fusion-mlx`, it provides financial modeling, statement analysis, risk compliance, and report generation — all **100% offline** with zero data uploaded.

### Claude Financial Comparison

| Capability | Claude Financial | Fusion-Finance |
|------------|-----------------|----------------|
| **Data residency** | ❌ Cloud-only | ✅ **100% local** |
| **China accessible** | ❌ Blocked | ✅ **Fully accessible** |
| **DCF modeling** | ✅ | ✅ |
| **Comps analysis** | ✅ | ✅ |
| **Sensitivity analysis** | ✅ | ✅ |
| **Monte Carlo simulation** | ✅ | ✅ |
| **Financial metrics** | ✅ | ✅ |
| **Balance sheet validation** | ✅ | ✅ |
| **KYC screening** | ✅ | ✅ |
| **Credit assessment** | ✅ | ✅ |
| **Compliance check** | ✅ | ✅ |
| **Valuation report** | ✅ | ✅ |
| **PitchBook** | ✅ | ✅ |
| **Research report** | ✅ | ✅ |
| **License** | Enterprise | **MIT (free)** |

---

## 🚀 Quick Start

```bash
git clone https://github.com/dahai80/fusion-finance.git
cd fusion-finance
pip install -e .

# DCF Valuation
fusion-finance model dcf "Company" 100 120 140 160

# Financial analysis
fusion-finance statement analyze "Company" --revenue 1000 --net-income 150

# KYC screening
fusion-finance risk kyc "Company"

# Generate valuation report
fusion-finance report valuation "Company" --output ./reports
```

## 📖 Modules

| Module | Capabilities | File |
|--------|-------------|------|
| **Modeling** | DCF, Comps, Sensitivity, Monte Carlo | `modeling/engine.py` |
| **Statements** | Financial metrics, Balance sheet validation | `statements/analyzer.py` |
| **Risk** | KYC, Credit assessment, Compliance check | `risk/engine.py` |
| **Report** | Valuation report, PitchBook, Research report | `report/reports.py` |

## 🧪 Tests

```bash
pip install -e ".[test]"
pytest tests/ -v
```

## 📄 License

MIT License.

---

<p align="center">
  <strong>Fusion-Finance — Local AI Finance. Zero Upload, Full Compliance.</strong>
</p>
<p align="center">
  <sub>Built with ❤️ and fusion-mlx</sub>
</p>