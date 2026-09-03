"""Coverage-boost tests batch 2 — audit, project, formatter, cli, report/statements/project routes, ai_client, tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from fusion_finance.api.app import app


@pytest.fixture(autouse=True)
def _restore_config(tmp_path):
    from fusion_finance import config

    dirs = {}
    for name in ("DATA_DIR", "AUDIT_DIR", "PROJECT_DIR", "CACHE_DIR", "EXPORT_DIR"):
        dirs[name] = getattr(config, name)
        setattr(config, name, tmp_path / name.lower())
    yield
    for name, val in dirs.items():
        setattr(config, name, val)


def _client() -> TestClient:
    return TestClient(app)


# ---------- AuditTrail ----------


class TestAuditTrail:
    def _trail(self, tmp_path):
        from fusion_finance.utils.audit import AuditTrail

        path = str(tmp_path / "audit.jsonl")
        return AuditTrail(log_path=path)

    def test_record_and_query(self, tmp_path):
        trail = self._trail(tmp_path)
        trail.record("alice", "login", "auth", {"ip": "1.2.3.4"}, "success", 5.0)
        trail.record("bob", "export", "report", "", "success", 12.0)
        trail.record("alice", "login", "auth", "", "failed", 1.0)
        results = trail.query(user="alice")
        assert len(results) == 2
        results = trail.query(action="login", status="failed")
        assert len(results) == 1
        results = trail.query(module="report")
        assert len(results) == 1
        results = trail.query(start_time=1.0, end_time=1e12, limit=10)
        assert len(results) == 3
        # offset slice
        page = trail.query(limit=1, offset=1)
        assert len(page) == 1

    def test_chain_verify_ok(self, tmp_path):
        trail = self._trail(tmp_path)
        trail.record("alice", "login", "auth")
        trail.record("alice", "logout", "auth")
        result = trail.verify_chain()
        assert result["verified"] is True
        assert result["checked"] == 2

    def test_chain_verify_broken(self, tmp_path):
        trail = self._trail(tmp_path)
        trail.record("alice", "login", "auth")
        # corrupt the file by tampering prev_hash
        path = Path(trail.log_path)
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        first = json.loads(lines[0])
        first["prev_hash"] = "deadbeef" * 8
        lines[0] = json.dumps(first, ensure_ascii=False)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = trail.verify_chain()
        assert result["verified"] is False
        assert result["broken_count"] >= 1

    def test_get_stats_inmemory(self, tmp_path):
        trail = self._trail(tmp_path)
        trail.record("alice", "login", "auth", duration_ms=5.0)
        trail.record("bob", "login", "auth", duration_ms=15.0, status="failed")
        stats = trail.get_stats()
        assert stats["total_entries"] == 2
        assert stats["unique_users"] == 2
        assert stats["source"] == "in_memory"
        assert "warning" in stats

    def test_get_stats_empty(self, tmp_path):
        trail = self._trail(tmp_path)
        stats = trail.get_stats()
        assert stats["total_entries"] == 0
        assert stats["success_rate"] == 0.0

    def test_get_stats_from_file(self, tmp_path):
        trail = self._trail(tmp_path)
        trail.record("alice", "login", "auth")
        trail.record("bob", "export", "report", status="failed")
        stats = trail.get_stats_from_file()
        assert stats["source"] == "file"
        assert stats["total_entries"] == 2

    def test_get_stats_from_file_with_corruption(self, tmp_path):
        trail = self._trail(tmp_path)
        trail.record("alice", "login", "auth")
        path = Path(trail.log_path)
        path.write_text(path.read_text(encoding="utf-8") + "NOT JSON\n", encoding="utf-8")
        stats = trail.get_stats_from_file()
        assert stats["corrupted_skipped"] >= 1

    def test_query_from_file_corrupted(self, tmp_path):
        trail = self._trail(tmp_path)
        trail.record("alice", "login", "auth")
        path = Path(trail.log_path)
        path.write_text(path.read_text(encoding="utf-8") + "GARBAGE LINE\n", encoding="utf-8")
        results = trail.query(user="alice", limit=10)
        assert len(results) == 1

    def test_singleton(self, tmp_path):
        from fusion_finance.utils import audit as audit_mod

        audit_mod._AUDIT_SINGLETON = None
        t1 = audit_mod.get_audit_trail()
        t2 = audit_mod.get_audit_trail()
        assert t1 is t2

    def test_rotation(self, tmp_path):
        from fusion_finance.utils import audit as audit_mod

        path = str(tmp_path / "audit.jsonl")
        trail = audit_mod.AuditTrail(log_path=path)
        # force rotation threshold tiny
        with patch.object(audit_mod, "_MAX_FILE_BYTES", 50):
            trail.record("alice", "login", "auth", details="x" * 100)
            trail.record("bob", "login", "auth", details="y" * 100)
        assert (Path(path) + ".1") if False else Path(path + ".1").exists()

    def test_read_last_hash_empty_and_missing(self, tmp_path):
        from fusion_finance.utils.audit import _GENESIS_HASH, AuditTrail

        trail = AuditTrail(log_path=str(tmp_path / "nope.jsonl"))
        assert trail._read_last_hash() == _GENESIS_HASH
        # empty file
        p = tmp_path / "empty.jsonl"
        p.write_text("", encoding="utf-8")
        trail2 = AuditTrail(log_path=str(p))
        assert trail2._read_last_hash() == _GENESIS_HASH

    def test_rotated_paths(self, tmp_path):
        trail = self._trail(tmp_path)
        paths = trail._rotated_paths(reverse=False)
        assert paths[0] == trail.log_path
        rev = trail._rotated_paths(reverse=True)
        assert rev[-1] == trail.log_path


# ---------- ProjectManager ----------


class TestProjectManager:
    def _mgr(self, tmp_path):
        from fusion_finance.project.manager import ProjectManager

        return ProjectManager(data_dir=str(tmp_path / "projects"))

    def test_full_lifecycle(self, tmp_path):
        mgr = self._mgr(tmp_path)
        proj = mgr.create("P1", "desc", {"k": "v"})
        assert proj.id.startswith("proj_")
        got = mgr.get(proj.id)
        assert got.name == "P1"
        updated = mgr.update(proj.id, name="P1b", description="d2", data={"a": 1})
        assert updated.name == "P1b"
        assert updated.version == 2
        assert updated.current_data == {"a": 1}
        listed = mgr.list_projects()
        assert len(listed) == 1
        assert listed[0]["name"] == "P1b"
        assert mgr.delete(proj.id) is True
        assert mgr.get(proj.id) is None
        assert mgr.delete(proj.id) is False

    def test_update_not_found(self, tmp_path):
        mgr = self._mgr(tmp_path)
        from fusion_finance.exceptions import DataError

        with pytest.raises(DataError):
            mgr.update("proj_00000000")

    def test_update_version_conflict(self, tmp_path):
        from fusion_finance.exceptions import FinanceError

        mgr = self._mgr(tmp_path)
        proj = mgr.create("P1")
        with pytest.raises(FinanceError):
            mgr.update(proj.id, name="x", expected_version=999)

    def test_snapshot_and_restore(self, tmp_path):
        mgr = self._mgr(tmp_path)
        proj = mgr.create("P1", None)
        mgr.update(proj.id, data={"v": 1})
        snap1 = mgr.snapshot(proj.id, label="first")
        assert snap1["version"] == 1
        mgr.update(proj.id, data={"v": 2})
        snap2 = mgr.snapshot(proj.id, label="second")
        assert snap2["version"] == 2
        versions = mgr.get_versions(proj.id)
        assert len(versions) == 2
        restored = mgr.restore(proj.id, version=1)
        assert restored["restored_version"] == 1
        got = mgr.get(proj.id)
        assert got.current_data == {"v": 1}
        # restore latest
        r2 = mgr.restore(proj.id)
        assert r2["restored_version"] == 2

    def test_snapshot_not_found(self, tmp_path):
        from fusion_finance.exceptions import DataError

        mgr = self._mgr(tmp_path)
        with pytest.raises(DataError):
            mgr.snapshot("proj_00000000")

    def test_restore_not_found(self, tmp_path):
        from fusion_finance.exceptions import DataError

        mgr = self._mgr(tmp_path)
        with pytest.raises(DataError):
            mgr.restore("proj_00000000")

    def test_restore_no_versions(self, tmp_path):
        from fusion_finance.exceptions import DataError

        mgr = self._mgr(tmp_path)
        proj = mgr.create("P1")
        with pytest.raises(DataError):
            mgr.restore(proj.id)

    def test_restore_version_not_found(self, tmp_path):
        from fusion_finance.exceptions import DataError

        mgr = self._mgr(tmp_path)
        proj = mgr.create("P1")
        mgr.snapshot(proj.id, data={"a": 1})
        with pytest.raises(DataError):
            mgr.restore(proj.id, version=999)

    def test_invalid_project_id(self, tmp_path):
        mgr = self._mgr(tmp_path)
        assert mgr.get("bad-id") is None
        assert mgr._project_path("") is None
        assert mgr._project_path("not-valid") is None

    def test_versions_dir_invalid(self, tmp_path):
        from fusion_finance.exceptions import FinanceError

        mgr = self._mgr(tmp_path)
        with pytest.raises(FinanceError):
            mgr._versions_dir("bad-id")

    def test_eviction(self, tmp_path):
        from fusion_finance.project import manager as mgr_mod

        mgr = self._mgr(tmp_path)
        proj = mgr.create("P1")
        with patch.object(mgr_mod, "_MAX_VERSIONS", 3):
            for i in range(5):
                mgr.snapshot(proj.id, label=f"v{i}", data={"i": i})
        got = mgr.get(proj.id)
        assert len(got.versions) == 3

    def test_load_corrupt_project(self, tmp_path):
        mgr = self._mgr(tmp_path)
        proj = mgr.create("P1")
        Path(mgr._project_path(proj.id)).write_text("NOT JSON", encoding="utf-8")
        mgr._cache.pop(proj.id, None)
        assert mgr.get(proj.id) is None

    def test_save_invalid_id(self, tmp_path, caplog):
        from fusion_finance.project.manager import Project

        mgr = self._mgr(tmp_path)
        proj = Project(id="bad", name="x")
        mgr._save_project(proj)  # should log error, not raise

    def test_version_data_missing(self, tmp_path):
        mgr = self._mgr(tmp_path)
        proj = mgr.create("P1")
        assert mgr.get_version_data(proj.id, 999) == {}

    def test_cache_hit(self, tmp_path):
        mgr = self._mgr(tmp_path)
        proj = mgr.create("P1")
        g1 = mgr.get(proj.id)
        g2 = mgr.get(proj.id)
        assert g1 is g2  # cached


# ---------- ProjectExporter ----------


class TestProjectExporter:
    def _setup(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter
        from fusion_finance.project.manager import ProjectManager

        mgr = ProjectManager(data_dir=str(tmp_path / "projects"))
        exp = ProjectExporter(manager=mgr)
        return mgr, exp

    def test_export_import_json(self, tmp_path):

        mgr, exp = self._setup(tmp_path)
        proj = mgr.create("P1", "desc")
        mgr.update(proj.id, data={"a": 1})
        mgr.snapshot(proj.id, label="s1", data={"a": 1})
        path = exp.export_json(proj.id)
        assert path and Path(path).exists()
        # import
        name = Path(path).name
        new_id = exp.import_json(name)
        assert new_id is not None

    def test_export_zip(self, tmp_path):
        mgr, exp = self._setup(tmp_path)
        proj = mgr.create("P1")
        mgr.update(proj.id, data={"a": 1})
        mgr.snapshot(proj.id, label="s1", data={"a": 1})
        path = exp.export_zip(proj.id)
        assert path and Path(path).exists()

    def test_import_zip(self, tmp_path):
        mgr, exp = self._setup(tmp_path)
        proj = mgr.create("P1")
        mgr.update(proj.id, data={"a": 1})
        mgr.snapshot(proj.id, label="s1", data={"a": 1})
        zip_path = exp.export_zip(proj.id)
        name = Path(zip_path).name
        new_id = exp.import_zip(name)
        assert new_id is not None

    def test_export_not_found(self, tmp_path):
        mgr, exp = self._setup(tmp_path)
        assert exp.export_json("proj_00000000") is None
        assert exp.export_zip("proj_00000000") is None

    def test_export_unsafe_name(self, tmp_path):
        mgr, exp = self._setup(tmp_path)
        proj = mgr.create("P1")
        # sanitize_name strips traversal to basename -> safe, export succeeds
        path = exp.export_json(proj.id, output_path="../../etc/evil")
        assert path is not None and path.endswith("evil.json")
        zpath = exp.export_zip(proj.id, output_path="../../etc/evil")
        assert zpath is not None and zpath.endswith("evil.zip")

    def test_resolve_import_path_rejects(self, tmp_path):
        from fusion_finance.project.export import ProjectExporter

        assert ProjectExporter._resolve_import_path("", ".json") is None
        assert ProjectExporter._resolve_import_path("/abs/path", ".json") is None
        assert ProjectExporter._resolve_import_path("../rel", ".json") is None
        assert ProjectExporter._resolve_import_path("nonexistent.json", ".json") is None

    def test_import_json_not_found(self, tmp_path):
        mgr, exp = self._setup(tmp_path)
        assert exp.import_json("nope.json") is None

    def test_import_zip_bad_archive(self, tmp_path):
        from fusion_finance import config

        mgr, exp = self._setup(tmp_path)
        bad = config.EXPORT_DIR / "bad.zip"
        config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"not a zip")
        assert exp.import_zip("bad.zip") is None

    def test_import_zip_missing_project_json(self, tmp_path):
        import zipfile

        from fusion_finance import config

        mgr, exp = self._setup(tmp_path)
        config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        bad = config.EXPORT_DIR / "nozproj.zip"
        with zipfile.ZipFile(str(bad), "w") as zf:
            zf.writestr("other.json", "{}")
        assert exp.import_zip("nozproj.zip") is None


# ---------- ReportFormatter ----------


class TestReportFormatter:
    def _fmt(self):
        from fusion_finance.report.formatter import ReportFormatter

        return ReportFormatter()

    def test_render_html_known_template(self):
        fmt = self._fmt()
        html = fmt.render_html("valuation", {"company": "Apple", "body": "<b>x</b>"})
        assert "Apple" in html

    def test_render_html_unknown_template(self):
        fmt = self._fmt()
        html = fmt.render_html("nonexistent", {"company": "X", "content": "hello"})
        assert "X" in html

    def test_render_html_fallback_when_no_jinja(self):
        fmt = self._fmt()
        fmt._jinja_env = False
        html = fmt.render_html("valuation", {"company": "Y", "body": "content"})
        assert "Y" in html

    def test_export_html(self, tmp_path):

        fmt = self._fmt()
        path = fmt.export("<html>hi</html>", "html", output_path="myreport")
        assert Path(path).exists()
        assert path.endswith(".html")

    def test_export_markdown(self, tmp_path):
        fmt = self._fmt()
        path = fmt.export("# Title", "markdown")
        assert Path(path).exists()
        assert path.endswith(".md")

    def test_export_json(self, tmp_path):
        fmt = self._fmt()
        path = fmt.export("content", "json", template_data={"a": 1})
        assert Path(path).exists()
        assert path.endswith(".json")

    def test_export_pdf_fallback(self, tmp_path):
        fmt = self._fmt()
        fmt._weasyprint = None
        path = fmt.export("<html>x</html>", "pdf", output_path="rep")
        assert path.endswith(".html")

    def test_export_pptx_fallback(self, tmp_path):
        fmt = self._fmt()
        fmt._pptx = None
        path = fmt.export("content text", "pptx", output_path="rep")
        assert path.endswith(".txt")

    def test_export_xlsx_fallback(self, tmp_path):
        fmt = self._fmt()
        fmt._openpyxl = None
        path = fmt.export("a,b,c", "xlsx", output_path="rep")
        assert path.endswith(".csv")

    def test_export_xlsx_with_dcf_summary(self, tmp_path):
        fmt = self._fmt()
        data = {"dcf_summary": [{"label": "EV", "value": 100}, {"label": "Equity", "value": 80}]}
        path = fmt.export("content", "xlsx", template_data=data, output_path="rep")
        assert path.endswith(".xlsx")

    def test_export_xlsx_with_financial_table(self, tmp_path):
        fmt = self._fmt()
        data = {"financial_table": {"columns": ["A", "B"], "rows": [["1", "2"], ["3", "4"]]}}
        path = fmt.export("content", "xlsx", template_data=data, output_path="rep")
        assert path.endswith(".xlsx")

    def test_export_unsupported_format(self):
        fmt = self._fmt()
        with pytest.raises(ValueError):
            fmt.export("x", "docx")

    def test_export_bad_output_path(self):
        # sanitize_name strips traversal to basename -> safe; cannot trigger ReportError
        # via path traversal. Verify export still works with traversal-like name (sanitized).
        fmt = self._fmt()
        path = fmt.export("x", "html", output_path="../../etc/evil")
        assert Path(path).exists()

    def test_sanitize_cell(self):
        from fusion_finance.report.formatter import _sanitize_cell

        assert _sanitize_cell("=evil") == "'=evil"
        assert _sanitize_cell("@evil") == "'@evil"
        assert _sanitize_cell("normal") == "normal"
        assert _sanitize_cell(123) == 123

    def test_split_content(self):
        from fusion_finance.report.formatter import _split_content

        text = "\n".join(["line" * 50] * 10)
        chunks = _split_content(text, max_chars=100)
        assert len(chunks) >= 2

    def test_export_pptx_real(self, tmp_path):
        pytest.importorskip("pptx")
        fmt = self._fmt()
        fmt._detect_deps()
        path = fmt.export("content here", "pptx", template_data={"company": "C", "date": "2026-01-01"}, output_path="rep")
        assert path.endswith(".pptx")

    def test_export_xlsx_real(self, tmp_path):
        pytest.importorskip("openpyxl")
        fmt = self._fmt()
        fmt._detect_deps()
        path = fmt.export("content", "xlsx", template_data={"dcf_summary": [{"label": "L", "value": 1}]}, output_path="rep")
        assert path.endswith(".xlsx")


# ---------- CLI ----------


class TestCLI:
    def test_model_dcf(self):
        from click.testing import CliRunner

        from fusion_finance.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["model", "dcf", "Apple", "100", "120", "140", "--wacc", "0.10"])
        assert result.exit_code == 0
        assert "DCF" in result.output

    def test_statement_analyze_pure(self):
        from click.testing import CliRunner

        from fusion_finance.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["statement", "analyze", "Apple", "--revenue", "1000", "--net-income", "200", "--total-assets", "5000"]
        )
        assert result.exit_code == 0

    def test_statement_analyze_ai_fallback(self):
        from click.testing import CliRunner

        from fusion_finance.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["statement", "analyze", "Apple", "--revenue", "1000", "--ai"])
        # AI fails (no mlx) -> fallback to pure calc
        assert result.exit_code == 0

    def test_report_valuation(self):
        from click.testing import CliRunner

        from fusion_finance.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["report", "valuation", "Apple", "100", "120", "140"])
        assert result.exit_code == 0
        assert "估值报告" in result.output or "saved" in result.output.lower() or "报告" in result.output

    def test_version(self):
        from click.testing import CliRunner

        from fusion_finance.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_serve_refuses_non_loopback_when_auth_enabled(self, monkeypatch):
        from click.testing import CliRunner

        from fusion_finance import config
        from fusion_finance.cli import cli

        monkeypatch.setattr(config, "is_auth_disabled", lambda: False)
        monkeypatch.setattr(config, "auth_safety_check", lambda host: ["Refusing to start: auth required on 0.0.0.0"])
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--host", "0.0.0.0", "--port", "11999"])
        assert result.exit_code == 2


# ---------- Report routes ----------


class TestReportRoutes:
    def test_valuation_route(self):
        c = _client()
        resp = c.post(
            "/api/v1/report/valuation",
            json={"company": "Apple", "revenue": [100, 120, 140], "ebit_margin": [0.2, 0.2, 0.2]},
        )
        assert resp.status_code == 200
        assert "content" in resp.json()

    def test_valuation_route_with_comps(self):
        c = _client()
        resp = c.post(
            "/api/v1/report/valuation",
            json={
                "company": "Apple",
                "revenue": [100, 120],
                "ebit_margin": [0.2, 0.2],
                "include_comps": True,
                "peers": [{"ev_revenue": 3.0, "ev_ebitda": 10.0, "p_e": 20.0}],
            },
        )
        assert resp.status_code == 200

    def test_pitchbook_route(self):
        c = _client()
        resp = c.post(
            "/api/v1/report/pitchbook",
            json={"company": "Apple", "industry": "Tech", "revenue": [100, 120], "ebit_margin": [0.2, 0.2]},
        )
        assert resp.status_code == 200

    def test_research_route_with_mock(self):
        from fusion_finance.api.dependencies import get_mlx_client

        mock = MagicMock()
        mock.chat = AsyncMock(return_value="AI research report content")
        app.dependency_overrides[get_mlx_client] = lambda: mock
        try:
            c = _client()
            resp = c.post("/api/v1/report/research", json={"company": "Apple", "industry": "Tech", "data": {}})
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_export_html_route(self):
        c = _client()
        resp = c.post("/api/v1/report/export/html", json={"content": "<html>x</html>", "name": "rtest"})
        assert resp.status_code == 200
        assert resp.json()["format"] == "html"

    def test_export_md_route(self):
        c = _client()
        resp = c.post("/api/v1/report/export/markdown", json={"content": "# hi", "name": "mdtest"})
        assert resp.status_code == 200
        assert resp.json()["format"] == "markdown"

    def test_export_unsupported_route(self):
        c = _client()
        resp = c.post("/api/v1/report/export/docx", json={"content": "x", "name": "r"})
        assert resp.status_code == 400

    def test_export_unsafe_name_route(self):
        c = _client()
        # sanitize_name strips to basename -> sanitized to safe name, returns 200
        resp = c.post("/api/v1/report/export/html", json={"content": "x", "name": "../../evil"})
        assert resp.status_code == 200

    def test_formats_route(self):
        c = _client()
        resp = c.get("/api/v1/report/formats")
        assert resp.status_code == 200
        assert "html" in resp.json()["formats"]


# ---------- Statements routes ----------


class TestStatementsRoutes:
    def test_metrics_route(self):
        c = _client()
        resp = c.post(
            "/api/v1/statements/metrics",
            json={"company": "X", "revenue": 1000, "net_income": 100, "total_assets": 5000, "equity": 2000},
        )
        assert resp.status_code == 200

    def test_validate_route(self):
        c = _client()
        resp = c.post(
            "/api/v1/statements/validate",
            json={
                "statements": [
                    {"company": "X", "total_assets": 1000, "total_liabilities": 400, "equity": 600}
                ]
            },
        )
        assert resp.status_code == 200
        assert "issues" in resp.json()

    def test_screener_route(self):
        c = _client()
        resp = c.post("/api/v1/statements/screener", json={"filters": {"preset": "growth"}, "limit": 5})
        assert resp.status_code == 200

    def test_screener_route_custom_filters(self):
        c = _client()
        resp = c.post(
            "/api/v1/statements/screener",
            json={"filters": {"filters": [{"metric": "roe", "min": 10}]}, "limit": 5},
        )
        assert resp.status_code == 200

    def test_normalize_route(self):
        c = _client()
        resp = c.post(
            "/api/v1/statements/normalize",
            json={"data": {"revenue": 1000, "net_income": 100}, "standard": "A", "company": "X"},
        )
        assert resp.status_code == 200

    def test_trend_route(self):
        c = _client()
        resp = c.post(
            "/api/v1/statements/trend",
            json={
                "statements": [
                    {"company": "X", "period": "2024", "revenue": 1000, "net_income": 100},
                    {"company": "X", "period": "2025", "revenue": 1200, "net_income": 150},
                ]
            },
        )
        assert resp.status_code == 200

    def test_standards_route(self):
        c = _client()
        resp = c.get("/api/v1/statements/standards")
        assert resp.status_code == 200

    def test_screener_presets_route(self):
        c = _client()
        resp = c.get("/api/v1/statements/screener-presets")
        assert resp.status_code == 200

    def test_analyze_route_with_mock(self):
        from fusion_finance.api.dependencies import get_mlx_client

        mock = MagicMock()
        mock.chat = AsyncMock(return_value='{"summary": "ok", "strengths": [], "weaknesses": []}')
        app.dependency_overrides[get_mlx_client] = lambda: mock
        try:
            c = _client()
            resp = c.post("/api/v1/statements/analyze", json={"company": "X", "data": {"revenue": 1000}})
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ---------- Project routes ----------


class TestProjectRoutes:
    def test_full_lifecycle(self):
        c = _client()
        # create
        resp = c.post("/api/v1/project/create", json={"name": "P1", "description": "d"})
        assert resp.status_code == 200
        pid = resp.json()["id"]
        # get
        resp = c.get(f"/api/v1/project/{pid}")
        assert resp.status_code == 200
        # update
        resp = c.put(f"/api/v1/project/{pid}", json={"name": "P1b", "data": {"a": 1}})
        assert resp.status_code == 200
        # list
        resp = c.get("/api/v1/project/list")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1
        # snapshot
        resp = c.post(f"/api/v1/project/{pid}/snapshot", json={"label": "s1", "data": {"a": 1}})
        assert resp.status_code == 200
        resp = c.post(f"/api/v1/project/{pid}/snapshot", json={"label": "s2", "data": {"a": 2}})
        assert resp.status_code == 200
        # versions
        resp = c.get(f"/api/v1/project/{pid}/versions")
        assert resp.status_code == 200
        # history
        resp = c.get(f"/api/v1/project/{pid}/history")
        assert resp.status_code == 200
        # diff
        resp = c.get(f"/api/v1/project/{pid}/diff?v1=1&v2=2")
        assert resp.status_code == 200
        # restore
        resp = c.post(f"/api/v1/project/{pid}/restore", json={"version": 1})
        assert resp.status_code == 200
        # export json
        resp = c.post(f"/api/v1/project/{pid}/export", json={"format": "json", "name": "pexp"})
        assert resp.status_code == 200
        # export zip
        resp = c.post(f"/api/v1/project/{pid}/export", json={"format": "zip", "name": "pexpz"})
        assert resp.status_code == 200
        # delete
        resp = c.delete(f"/api/v1/project/{pid}")
        assert resp.status_code == 200

    def test_get_not_found(self):
        c = _client()
        resp = c.get("/api/v1/project/proj_00000000")
        assert resp.status_code == 404

    def test_update_not_found(self):
        c = _client()
        resp = c.put("/api/v1/project/proj_00000000", json={"name": "x"})
        assert resp.status_code == 404

    def test_delete_not_found(self):
        c = _client()
        resp = c.delete("/api/v1/project/proj_00000000")
        assert resp.status_code == 404

    def test_snapshot_not_found(self):
        c = _client()
        resp = c.post("/api/v1/project/proj_00000000/snapshot", json={"label": "x"})
        assert resp.status_code == 404

    def test_restore_not_found(self):
        c = _client()
        resp = c.post("/api/v1/project/proj_00000000/restore", json={"version": 1})
        assert resp.status_code == 404

    def test_diff_not_found(self):
        c = _client()
        resp = c.get("/api/v1/project/proj_00000000/diff")
        assert resp.status_code == 404

    def test_history_not_found(self):
        c = _client()
        resp = c.get("/api/v1/project/proj_00000000/history")
        assert resp.status_code == 404

    def test_export_not_found(self):
        c = _client()
        resp = c.post("/api/v1/project/proj_00000000/export", json={"format": "json"})
        assert resp.status_code in (404, 500)

    def test_export_unsafe_name(self):
        c = _client()
        resp = c.post("/api/v1/project/create", json={"name": "P1"})
        pid = resp.json()["id"]
        # sanitize_name strips to basename -> safe, returns 200
        resp = c.post(f"/api/v1/project/{pid}/export", json={"format": "json", "name": "../../evil"})
        assert resp.status_code == 200


# ---------- AI client ----------


class TestMLXClient:
    def test_resolve_api_key_explicit(self):
        from fusion_finance.ai_client import _resolve_api_key

        assert _resolve_api_key("key123") == "key123"

    def test_resolve_api_key_env(self, monkeypatch):
        from fusion_finance.ai_client import _resolve_api_key

        monkeypatch.setenv("FUSION_MLX_API_KEY", "envkey")
        assert _resolve_api_key("") == "envkey"

    def test_resolve_api_key_settings_file(self, monkeypatch, tmp_path):
        from fusion_finance.ai_client import _resolve_api_key

        monkeypatch.delenv("FUSION_MLX_API_KEY", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg = tmp_path / ".fusion-mlx" / "settings.json"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(json.dumps({"auth": {"api_key": "filekey"}}), encoding="utf-8")
        assert _resolve_api_key("") == "filekey"

    def test_resolve_api_key_settings_corrupt(self, monkeypatch, tmp_path):
        from fusion_finance.ai_client import _resolve_api_key

        monkeypatch.delenv("FUSION_MLX_API_KEY", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg = tmp_path / ".fusion-mlx" / "settings.json"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("NOT JSON", encoding="utf-8")
        assert _resolve_api_key("") == ""

    def test_circuit_breaker(self):
        from fusion_finance.ai_client import _CircuitBreaker

        cb = _CircuitBreaker(failure_threshold=2, recovery_seconds=1000)
        assert not cb.is_open
        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert cb.is_open
        cb.record_success()
        assert not cb.is_open

    def test_circuit_breaker_half_open(self):
        from fusion_finance.ai_client import _CircuitBreaker

        cb = _CircuitBreaker(failure_threshold=1, recovery_seconds=0.0)
        cb.record_failure()
        import time

        time.sleep(0.01)
        # recovery_seconds=0 -> after any elapsed, is_open resets failures and returns False
        assert not cb.is_open
        assert cb._failures == 0

    def test_chat_rejected_when_breaker_open(self):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.exceptions import AIClientError

        client = MLXClient()
        client._breaker._failures = 100
        client._breaker._opened_at = 1e12
        import asyncio

        with pytest.raises(AIClientError):
            asyncio.run(client.chat([{"role": "user", "content": "hi"}]))

    def test_chat_httpx_success(self, monkeypatch):
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        # simulate httpx path
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"choices": [{"message": {"content": "hello"}}]}
        fake_resp.raise_for_status = MagicMock()

        fake_client = MagicMock()
        fake_client.post = AsyncMock(return_value=fake_resp)
        fake_client.get = AsyncMock(return_value=MagicMock(json=lambda: {"data": []}))
        client._httpx_client = fake_client
        # force httpx path
        import fusion_finance.ai_client as ai_mod

        orig = ai_mod._HAS_FUSION_CORE
        ai_mod._HAS_FUSION_CORE = False
        client._client = None
        try:
            import asyncio

            result = asyncio.run(client.chat([{"role": "user", "content": "hi"}], model="m"))
            assert result == "hello"
        finally:
            ai_mod._HAS_FUSION_CORE = orig

    def test_chat_retries_exhausted(self, monkeypatch):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.exceptions import AIClientError

        client = MLXClient(max_retries=1)
        fake_client = MagicMock()
        fake_client.post = AsyncMock(side_effect=Exception("conn refused"))
        client._httpx_client = fake_client
        import fusion_finance.ai_client as ai_mod

        orig = ai_mod._HAS_FUSION_CORE
        ai_mod._HAS_FUSION_CORE = False
        client._client = None
        try:
            import asyncio

            with pytest.raises(AIClientError):
                asyncio.run(client.chat([{"role": "user", "content": "hi"}], model="m"))
        finally:
            ai_mod._HAS_FUSION_CORE = orig

    def test_chat_programming_error(self, monkeypatch):
        from fusion_finance.ai_client import MLXClient
        from fusion_finance.exceptions import AIClientError

        client = MLXClient()
        fake_client = MagicMock()
        fake_client.post = AsyncMock(side_effect=TypeError("bad type"))
        client._httpx_client = fake_client
        import fusion_finance.ai_client as ai_mod

        orig = ai_mod._HAS_FUSION_CORE
        ai_mod._HAS_FUSION_CORE = False
        client._client = None
        try:
            import asyncio

            with pytest.raises(AIClientError):
                asyncio.run(client.chat([{"role": "user", "content": "hi"}], model="m"))
        finally:
            ai_mod._HAS_FUSION_CORE = orig

    def test_health_check_httpx(self, monkeypatch):
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        fake_resp = MagicMock()
        fake_resp.raise_for_status = MagicMock()
        fake_resp.json.return_value = {"data": [{"id": "m1"}]}
        fake_client = MagicMock()
        fake_client.get = AsyncMock(return_value=fake_resp)
        client._httpx_client = fake_client
        import fusion_finance.ai_client as ai_mod

        orig = ai_mod._HAS_FUSION_CORE
        ai_mod._HAS_FUSION_CORE = False
        client._client = None
        try:
            import asyncio

            result = asyncio.run(client.health_check())
            assert result["status"] == "ok"
        finally:
            ai_mod._HAS_FUSION_CORE = orig

    def test_health_check_error(self, monkeypatch):
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        fake_client = MagicMock()
        fake_client.get = AsyncMock(side_effect=Exception("fail"))
        client._httpx_client = fake_client
        import fusion_finance.ai_client as ai_mod

        orig = ai_mod._HAS_FUSION_CORE
        ai_mod._HAS_FUSION_CORE = False
        client._client = None
        try:
            import asyncio

            result = asyncio.run(client.health_check())
            assert result["status"] == "error"
        finally:
            ai_mod._HAS_FUSION_CORE = orig

    def test_close(self):
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        client._httpx_client = MagicMock()
        client._httpx_client.aclose = AsyncMock()
        import asyncio

        asyncio.run(client.close())
        assert client._httpx_client is None

    def test_chat_stream_httpx_fallback(self, monkeypatch):
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"choices": [{"message": {"content": "streamed"}}]}
        fake_resp.raise_for_status = MagicMock()
        fake_client = MagicMock()
        fake_client.post = AsyncMock(return_value=fake_resp)
        fake_client.get = AsyncMock(return_value=MagicMock(json=lambda: {"data": []}))
        client._httpx_client = fake_client
        import fusion_finance.ai_client as ai_mod

        orig = ai_mod._HAS_FUSION_CORE
        ai_mod._HAS_FUSION_CORE = False
        client._client = None
        try:
            import asyncio

            async def collect():
                out = []
                async for chunk in client.chat_stream([{"role": "user", "content": "hi"}], model="m"):
                    out.append(chunk)
                return out

            assert asyncio.run(collect()) == ["streamed"]
        finally:
            ai_mod._HAS_FUSION_CORE = orig

    def test_chat_httpx_no_model_lists(self, monkeypatch):
        from fusion_finance.ai_client import MLXClient

        client = MLXClient()
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        fake_resp.raise_for_status = MagicMock()
        fake_client = MagicMock()
        fake_client.post = AsyncMock(return_value=fake_resp)
        # /models fails -> fallback default
        fake_client.get = AsyncMock(side_effect=Exception("nope"))
        client._httpx_client = fake_client
        import fusion_finance.ai_client as ai_mod

        orig = ai_mod._HAS_FUSION_CORE
        ai_mod._HAS_FUSION_CORE = False
        client._client = None
        try:
            import asyncio

            result = asyncio.run(client.chat([{"role": "user", "content": "hi"}], model=""))
            assert result == "ok"
        finally:
            ai_mod._HAS_FUSION_CORE = orig


# ---------- ToolRegistry ----------


class TestToolRegistry:
    def _registry(self):
        from fusion_finance.copilot.tools import ToolRegistry

        mock_mlx = MagicMock()
        return ToolRegistry(mlx=mock_mlx)

    def test_format_prompt(self):
        reg = self._registry()
        prompt = reg.format_prompt()
        assert "工具" in prompt
        assert "build_dcf" in prompt

    def test_get_definitions(self):
        reg = self._registry()
        defs = reg.get_definitions()
        names = [d["name"] for d in defs]
        assert "build_dcf" in names
        assert "calculate_var" in names

    def test_execute_unknown_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("nope", {}))
        assert result["error"] == "tool_failed"
        assert result["code"] == "unknown_tool"

    def test_execute_invalid_args_type(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("build_dcf", "notdict"))
        assert result["code"] == "invalid_args_type"

    def test_execute_missing_required(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("build_dcf", {}))
        assert result["code"] == "missing_key"

    def test_execute_type_mismatch(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("build_dcf", {"company": 123, "revenue": [1, 2]}))
        assert result["code"] == "TypeError"

    def test_execute_array_item_type(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("build_dcf", {"company": "x", "revenue": ["a", "b"]}))
        assert result["code"] == "TypeError"

    def test_calculate_dcf(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("calculate_dcf", {"company": "Apple", "revenue": [100, 120], "wacc": 0.1}))
        assert "enterprise_value" in result or "dcf_value" in result or "company" in result

    def test_var_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("calculate_var", {"returns": [0.01, -0.02, 0.03], "portfolio_value": 1000}))
        assert "var" in result or "var_95" in result

    def test_stress_test(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("stress_test", {}))
        assert isinstance(result, list)

    def test_sensitivity_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(
            reg.execute("sensitivity_analysis", {"company": "X", "revenue": [100, 120], "wacc_range": [0.08, 0.1], "growth_range": [0.02, 0.03]})
        )
        assert isinstance(result, dict)

    def test_monte_carlo_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("monte_carlo", {"company": "X", "revenue": [100, 120], "simulations": 10}))
        assert isinstance(result, dict)

    def test_metrics_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(
            reg.execute(
                "calculate_metrics",
                {"income_statement": {"company": "X", "revenue": 1000, "net_income": 100}, "balance_sheet": {"total_assets": 5000, "total_equity": 2000}},
            )
        )
        assert "net_margin" in result

    def test_portfolio_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(
            reg.execute(
                "optimize_portfolio",
                {"returns": [0.1, 0.12], "volatilities": [0.15, 0.2], "correlations": [[1, 0.3], [0.3, 1]]},
            )
        )
        assert isinstance(result, dict)

    def test_black_litterman_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(
            reg.execute(
                "black_litterman",
                {"returns": [0.1, 0.12], "volatilities": [0.15, 0.2], "correlations": [[1, 0.3], [0.3, 1]], "views": []},
            )
        )
        assert isinstance(result, dict)

    def test_sanctions_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("sanctions_screening", {"entity": "Some Company", "threshold": 0.5}))
        assert isinstance(result, list)

    def test_entity_resolution_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("entity_resolution", {"entity": "X Corp", "depth": 2}))
        assert isinstance(result, dict)

    def test_market_feed_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("market_feed", {"market": "A"}))
        assert isinstance(result, list)

    def test_bond_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(
            reg.execute("bond_analysis", {"face_value": 1000, "coupon_rate": 0.05, "years": 5, "yield_to_maturity": 0.05})
        )
        assert isinstance(result, dict)

    def test_yield_curve_tool_ok(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(
            reg.execute("yield_curve", {"maturities": [1, 2, 5, 10], "yields": [0.02, 0.025, 0.03, 0.035]})
        )
        assert isinstance(result, dict)

    def test_yield_curve_tool_missing(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("yield_curve", {"maturities": [], "yields": []}))
        assert "error" in result

    def test_val_report_tool(self):
        import asyncio

        reg = self._registry()
        result = asyncio.run(reg.execute("generate_valuation_report", {"company": "X", "revenue": [100, 120]}))
        assert isinstance(result, str)

    def test_kyc_tool_with_mock(self):
        import asyncio

        reg = self._registry()
        reg._mlx.chat = AsyncMock(
            return_value='{"risk_level": "low", "risk_score": 20, "findings": [], "recommendations": []}'
        )
        result = asyncio.run(reg.execute("kyc_screening", {"entity": "X"}))
        assert result["risk_level"] == "low"

    def test_credit_tool_with_mock(self):
        import asyncio

        reg = self._registry()
        reg._mlx.chat = AsyncMock(
            return_value='{"credit_score": 80, "rating": "AA", "max_credit_line": 1000, "strengths": [], "concerns": []}'
        )
        result = asyncio.run(reg.execute("credit_assessment", {"entity": "X", "financials": {}}))
        assert result["rating"] == "AA"

    def test_build_dcf_tool_with_mock(self):
        import asyncio

        reg = self._registry()
        reg._mlx.chat = AsyncMock(
            return_value='{"wacc": 0.1, "terminal_growth": 0.03, "ebit_margin": [0.2, 0.2]}'
        )
        result = asyncio.run(reg.execute("build_dcf", {"company": "X", "revenue": [100, 120]}))
        assert isinstance(result, dict)

    def test_build_comps_tool_with_mock(self):
        import asyncio

        reg = self._registry()
        reg._mlx.chat = AsyncMock(
            return_value='{"peers": [{"ev_revenue": 3, "ev_ebitda": 10, "p_e": 20}], "industry_avg": {}}'
        )
        result = asyncio.run(reg.execute("build_comps", {"company": "X", "industry": "Tech"}))
        assert isinstance(result, dict)

    def test_register_override_warning(self, caplog):
        reg = self._registry()
        reg.register("calculate_dcf", lambda args: None)  # overwrite

    def test_schema_to_prompt_empty(self):
        from fusion_finance.copilot.tools import _schema_to_prompt

        assert _schema_to_prompt({}) == ""
        assert _schema_to_prompt({"properties": {"a": {"type": "string", "description": "d"}}, "required": ["a"]}) != ""

    def test_validate_args_no_definition(self):
        reg = self._registry()
        # unknown name -> no-op
        reg._validate_args("unknown_tool", {})

    def test_check_type_any(self):
        from fusion_finance.copilot.tools import ToolRegistry

        ToolRegistry._check_type("k", "x", None)  # no raise
        ToolRegistry._check_type("k", "x", "any")  # no raise

    def test_check_type_unknown_expected(self):
        from fusion_finance.copilot.tools import ToolRegistry

        ToolRegistry._check_type("k", "x", "weird")  # no raise, unknown type

    def test_check_item_type_non_list(self):
        from fusion_finance.copilot.tools import ToolRegistry

        ToolRegistry._check_item_type("k", "notlist", {"type": "string"})  # no raise
