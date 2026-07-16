"""Fusion-Finance CLI 入口。"""

from __future__ import annotations

import asyncio
import click

from . import __version__, __app_name__
from .ai_client import MLXClient
from .modeling import FinancialModelingEngine, DCFModel
from .statements import StatementAnalyzer, FinancialStatement
from .risk import RiskComplianceEngine
from .report import ReportGenerator


@click.group()
@click.option("--verbose", "-v", is_flag=True)
@click.option("--model", "-m", default="")
@click.version_option(version=__version__, prog_name=__app_name__)
@click.pass_context
def cli(ctx, verbose, model):
    """Fusion-Finance — Local AI-powered financial analysis platform."""
    mlx = MLXClient(model=model)
    ctx.ensure_object(dict)
    ctx.obj["mlx"] = mlx
    ctx.obj["modeling"] = FinancialModelingEngine(mlx)
    ctx.obj["statements"] = StatementAnalyzer(mlx)
    ctx.obj["risk"] = RiskComplianceEngine(mlx)
    ctx.obj["report"] = ReportGenerator(mlx)


@cli.group()
def model():
    """财务建模。"""
    pass


@model.command("dcf")
@click.argument("company")
@click.argument("revenue", nargs=-1, type=float)
@click.option("--wacc", default=0.10)
@click.pass_context
def model_dcf(ctx, company, revenue, wacc):
    """DCF 估值模型。"""
    asyncio.run(_async_dcf(ctx, company, list(revenue), wacc))


async def _async_dcf(ctx, company, revenue, wacc):
    engine = ctx.obj["modeling"]
    model = await engine.build_dcf(company, revenue, {"wacc": wacc})
    result = model.calculate()
    click.echo(f"\n📊 {company} DCF 估值")
    click.echo(f"   WACC: {model.wacc:.1%}")
    click.echo(f"   企业价值: {result.get('enterprise_value', 0):,.2f}")
    click.echo(f"   股权价值: {result.get('equity_value', 0):,.2f}")
    if model.target_price:
        click.echo(f"   目标价: {model.target_price:,.2f}")
    click.echo()


@cli.group()
def statement():
    """财报分析。"""
    pass


@statement.command("analyze")
@click.argument("company")
@click.option("--revenue", type=float)
@click.option("--net-income", type=float)
@click.option("--total-assets", type=float)
@click.pass_context
def stmt_analyze(ctx, company, revenue, net_income, total_assets):
    """分析财务指标。"""
    stmt = FinancialStatement(company=company, revenue=revenue or 0,
                              net_income=net_income or 0, total_assets=total_assets or 0)
    analyzer = ctx.obj["statements"]
    analysis = analyzer.calculate_metrics(stmt)
    click.echo(f"\n📋 {company} 财务指标")
    click.echo(f"   净利率: {analysis.net_margin:.1f}%")
    click.echo(f"   ROA: {analysis.roa:.1f}%")
    if analysis.debt_ratio:
        click.echo(f"   资产负债率: {analysis.debt_ratio:.1f}%")
    click.echo()


@cli.group()
def risk():
    """风控合规。"""
    pass


@risk.command("kyc")
@click.argument("entity")
@click.pass_context
def risk_kyc(ctx, entity):
    """KYC 尽调。"""
    asyncio.run(_async_kyc(ctx, entity))


async def _async_kyc(ctx, entity):
    engine = ctx.obj["risk"]
    result = await engine.kyc_screening(entity)
    click.echo(f"\n🔍 KYC 尽调: {entity}")
    click.echo(f"   风险等级: {result.risk_level}")
    click.echo(f"   风险评分: {result.risk_score:.0f}/100")
    click.echo()


@cli.group()
def report():
    """报告生成。"""
    pass


@report.command("valuation")
@click.argument("company")
@click.option("--output", "-o", default="~/Desktop")
@click.pass_context
def report_valuation(ctx, company, output):
    """生成估值报告。"""
    dcf = DCFModel(company=company, revenue=[100, 120, 140])
    dcf.calculate()
    gen = ctx.obj["report"]
    content = gen.generate_valuation_report(company, dcf)
    path = gen.save_report(content, output)
    click.echo(f"📄 估值报告已保存: {path}")


def main():
    cli()


if __name__ == "__main__":
    main()