from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

import pytest

from fusion_finance.project.export import ProjectExporter
from fusion_finance.project.manager import ProjectManager
from fusion_finance.project.version import VersionControl
from fusion_finance.report.formatter import FORMAT_HTML, FORMAT_JSON, FORMAT_MD, SUPPORTED_FORMATS, ReportFormatter
from fusion_finance.utils.audit import AuditTrail


class TestReportFormatter:
    def setup_method(self):
        self.formatter = ReportFormatter()

    def test_fallback_html(self):
        data = {"company": "TestCo", "date": "2026-01-01", "content": "hello"}
        html = self.formatter._fallback_html("valuation", data)
        assert "TestCo" in html
        assert "hello" in html

    def test_render_html_jinja(self):
        data = {
            "company": "TestCo",
            "date": "2026-01-01",
            "dcf_summary": [{"label": "EV", "value": "1,000.00"}],
            "assumptions": [],
            "comps": [],
            "chart_svg": "",
            "timestamp": "2026-01-01 12:00:00",
        }
        html = self.formatter.render_html("valuation", data)
        assert "TestCo" in html
        assert "1,000.00" in html

    def test_render_html_unknown_template(self):
        data = {"company": "X"}
        html = self.formatter.render_html("nonexistent", data)
        assert "X" in html

    def test_export_markdown(self, tmp_path):
        out = str(tmp_path / "test.md")
        result = self.formatter.export("# Hello", FORMAT_MD, output_path=out)
        assert Path(result).exists()
        assert Path(result).read_text() == "# Hello"

    def test_export_json(self, tmp_path):
        out = str(tmp_path / "test.json")
        data = {"company": "TestCo", "dcf_summary": [{"label": "EV", "value": "100"}]}
        result = self.formatter.export("", FORMAT_JSON, output_path=out, template_data=data)
        assert Path(result).exists()
        loaded = json.loads(Path(result).read_text())
        assert loaded["company"] == "TestCo"

    def test_export_html_with_template(self, tmp_path):
        out = str(tmp_path / "test.html")
        data = {
            "company": "TestCo",
            "date": "2026-01-01",
            "dcf_summary": [{"label": "EV", "value": "500"}],
            "assumptions": [],
            "comps": [],
            "chart_svg": "",
            "timestamp": "2026-01-01",
        }
        result = self.formatter.export("", FORMAT_HTML, output_path=out,
                                       template_name="valuation", template_data=data)
        assert Path(result).exists()
        content = Path(result).read_text()
        assert "TestCo" in content

    def test_export_unsupported_format(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            self.formatter.export("test", "docx")

    def test_supported_formats_list(self):
        assert "html" in SUPPORTED_FORMATS
        assert "json" in SUPPORTED_FORMATS
        assert "markdown" in SUPPORTED_FORMATS


class TestProjectManager:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.pm = ProjectManager(data_dir=self.tmp_dir)

    def test_create_project(self):
        proj = self.pm.create("TestProj", description="A test")
        assert proj.id.startswith("proj_")
        assert proj.name == "TestProj"

    def test_get_project(self):
        proj = self.pm.create("GetTest")
        loaded = self.pm.get(proj.id)
        assert loaded is not None
        assert loaded.name == "GetTest"

    def test_get_nonexistent(self):
        assert self.pm.get("proj_nonexistent") is None

    def test_update_project(self):
        proj = self.pm.create("OldName")
        updated = self.pm.update(proj.id, name="NewName", data={"key": "val"})
        assert updated.name == "NewName"
        assert updated.current_data == {"key": "val"}

    def test_delete_project(self):
        proj = self.pm.create("DeleteMe")
        assert self.pm.delete(proj.id) is True
        assert self.pm.get(proj.id) is None

    def test_list_projects(self):
        self.pm.create("ProjA")
        self.pm.create("ProjB")
        listing = self.pm.list_projects()
        assert len(listing) >= 2

    def test_snapshot(self):
        proj = self.pm.create("SnapTest")
        result = self.pm.snapshot(proj.id, label="v1", data={"val": 1})
        assert result["version"] == 1

    def test_restore(self):
        proj = self.pm.create("RestoreTest")
        self.pm.snapshot(proj.id, data={"v": 1})
        self.pm.snapshot(proj.id, data={"v": 2})
        result = self.pm.restore(proj.id, version=1)
        assert result["restored_version"] == 1

    def test_get_versions(self):
        proj = self.pm.create("VerTest")
        self.pm.snapshot(proj.id, data={"a": 1})
        self.pm.snapshot(proj.id, data={"a": 2})
        versions = self.pm.get_versions(proj.id)
        assert len(versions) == 2


class TestVersionControl:
    def setup_method(self):
        self.vc = VersionControl()

    def test_compute_hash_deterministic(self):
        h1 = self.vc.compute_hash({"a": 1, "b": 2})
        h2 = self.vc.compute_hash({"b": 2, "a": 1})
        assert h1 == h2

    def test_diff_added_removed(self):
        d = self.vc.diff({"a": 1}, {"b": 2})
        assert d["added"] == {"b": 2}
        assert d["removed"] == {"a": 1}

    def test_diff_changed(self):
        d = self.vc.diff({"a": 1}, {"a": 2})
        assert d["changed"]["a"] == {"old": 1, "new": 2}

    def test_patch(self):
        d = self.vc.diff({"a": 1, "b": 2}, {"a": 3, "c": 4})
        result = self.vc.patch({"a": 1, "b": 2}, d)
        assert result == {"a": 3, "c": 4}

    def test_cherry_pick(self):
        versions = [{"version": 1, "data": {"x": 1}}, {"version": 2, "data": {"x": 2}}]
        assert self.vc.cherry_pick(versions, 2) == {"x": 2}

    def test_history_summary(self):
        versions = [
            {"version": 1, "label": "v1", "data": {"a": 1}, "timestamp": 1000},
            {"version": 2, "label": "v2", "data": {"a": 2, "b": 3}, "timestamp": 2000},
        ]
        summary = self.vc.history_summary(versions)
        assert len(summary) == 2
        assert summary[1]["changes"]["added"] == 1


class TestProjectExporter:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.pm = ProjectManager(data_dir=self.tmp_dir)
        self.exporter = ProjectExporter(manager=self.pm)

    def test_export_json(self, tmp_path):
        proj = self.pm.create("ExportTest")
        out = str(tmp_path / "export.json")
        result = self.exporter.export_json(proj.id, output_path=out)
        assert result is not None
        data = json.loads(Path(result).read_text())
        assert data["name"] == "ExportTest"

    def test_export_zip(self, tmp_path):
        proj = self.pm.create("ZipTest")
        self.pm.snapshot(proj.id, data={"v": 1})
        out = str(tmp_path / "export.zip")
        result = self.exporter.export_zip(proj.id, output_path=out)
        assert result is not None
        with zipfile.ZipFile(result, "r") as zf:
            assert "project.json" in zf.namelist()

    def test_import_json(self, tmp_path):
        data = {
            "name": "Imported",
            "description": "test",
            "metadata": {},
            "current_data": {"x": 1},
            "versions": [{"version": 1, "label": "v1", "data": {"x": 1}, "timestamp": 1000}],
        }
        inp = tmp_path / "import.json"
        inp.write_text(json.dumps(data), encoding="utf-8")
        proj_id = self.exporter.import_json(str(inp))
        assert proj_id is not None

    def test_import_nonexistent(self):
        assert self.exporter.import_json("/no/such/file.json") is None


class TestAuditTrailEnhanced:
    def setup_method(self):
        self.tmp_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp_file.close()
        self.audit = AuditTrail(log_path=self.tmp_file.name)

    def teardown_method(self):
        import contextlib
        with contextlib.suppress(OSError):
            os.unlink(self.tmp_file.name)

    def test_record_and_query(self):
        self.audit.record("user1", "create", "project")
        self.audit.record("user1", "delete", "project")
        self.audit.record("user2", "create", "modeling")
        assert len(self.audit.query(user="user1")) == 2

    def test_query_by_action(self):
        self.audit.record("u1", "create", "m1")
        self.audit.record("u1", "delete", "m1")
        assert len(self.audit.query(action="create")) == 1

    def test_query_by_status(self):
        self.audit.record("u1", "create", "m1", status="failed")
        self.audit.record("u1", "create", "m1", status="success")
        assert len(self.audit.query(status="failed")) == 1

    def test_get_stats(self):
        self.audit.record("u1", "create", "project", status="success")
        self.audit.record("u1", "delete", "project", status="failed")
        stats = self.audit.get_stats()
        assert stats["total_entries"] == 2
        assert stats["success_rate"] == 0.5
        assert "action_counts" in stats
        assert "hourly_distribution" in stats

    def test_query_from_file(self):
        self.audit.record("u1", "create", "project")
        new_audit = AuditTrail(log_path=self.tmp_file.name)
        results = new_audit.query_from_file(action="create")
        assert len(results) >= 1

    def test_get_stats_from_file(self):
        self.audit.record("u1", "create", "project")
        new_audit = AuditTrail(log_path=self.tmp_file.name)
        stats = new_audit.get_stats_from_file()
        assert stats["total_entries"] >= 1


class TestPhase3APIRoutes:
    def setup_method(self):
        from httpx import ASGITransport, AsyncClient

        from fusion_finance.api.app import app
        self.transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=self.transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_report_formats(self):
        resp = await self.client.get("/api/v1/report/formats")
        assert resp.status_code == 200
        assert "html" in resp.json()["formats"]

    @pytest.mark.asyncio
    async def test_report_export_json(self, tmp_path):
        resp = await self.client.post(
            "/api/v1/report/export/json",
            json={"content": "test", "template_data": {"company": "X"}, "output_path": str(tmp_path / "out.json")},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_project_crud(self):
        resp = await self.client.post("/api/v1/project/create", json={"name": "APITest"})
        assert resp.status_code == 200
        pid = resp.json()["id"]
        r2 = await self.client.get(f"/api/v1/project/{pid}")
        assert r2.status_code == 200
        r3 = await self.client.put(f"/api/v1/project/{pid}", json={"name": "Updated"})
        assert r3.status_code == 200
        r4 = await self.client.delete(f"/api/v1/project/{pid}")
        assert r4.status_code == 200

    @pytest.mark.asyncio
    async def test_project_snapshot_versions_restore(self):
        resp = await self.client.post("/api/v1/project/create", json={"name": "SnapAPI"})
        pid = resp.json()["id"]
        await self.client.post(f"/api/v1/project/{pid}/snapshot", json={"data": {"v": 1}})
        await self.client.post(f"/api/v1/project/{pid}/snapshot", json={"data": {"v": 2}})
        vers = await self.client.get(f"/api/v1/project/{pid}/versions")
        assert vers.json()["total"] >= 2
        restore = await self.client.post(f"/api/v1/project/{pid}/restore", json={"version": 1})
        assert restore.status_code == 200

    @pytest.mark.asyncio
    async def test_project_diff_and_history(self):
        resp = await self.client.post("/api/v1/project/create", json={"name": "DiffAPI"})
        pid = resp.json()["id"]
        await self.client.post(f"/api/v1/project/{pid}/snapshot", json={"data": {"a": 1}})
        await self.client.post(f"/api/v1/project/{pid}/snapshot", json={"data": {"a": 2}})
        diff = await self.client.get(f"/api/v1/project/{pid}/diff?v1=1&v2=2")
        assert diff.status_code == 200
        hist = await self.client.get(f"/api/v1/project/{pid}/history")
        assert hist.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_record_query_stats(self):
        rec = await self.client.post("/api/v1/audit/record",
                                     json={"user": "test", "action": "create", "module": "project"})
        assert rec.status_code == 200
        q = await self.client.post("/api/v1/audit/query", json={"user": "test"})
        assert q.status_code == 200
        stats = await self.client.get("/api/v1/audit/stats")
        assert stats.status_code == 200
        file_stats = await self.client.get("/api/v1/audit/file-stats")
        assert file_stats.status_code == 200
