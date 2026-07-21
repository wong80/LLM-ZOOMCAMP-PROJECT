"""Tests for Grafana provisioning."""

import pytest


class TestGrafanaProvisioning:
    def test_datasource_creation(self, mocker):
        mock_grafana_api = mocker.MagicMock()
        mock_grafana_api.__enter__.return_value = mock_grafana_api

        def fake_post(*a, **kw):
            resp = mocker.MagicMock()
            resp.json.return_value = {
                "datasource": {"type": "postgres", "name": "PyDoc PostgreSQL", "uid": "test-uid"}
            }
            resp.raise_for_status.return_value = None
            return resp

        mock_grafana_api.post = fake_post

        from grafana.init import create_postgres_datasource
        result = create_postgres_datasource(mock_grafana_api)
        assert result["datasource"]["type"] == "postgres"
        assert result["datasource"]["name"] == "PyDoc PostgreSQL"

    def test_dashboard_import(self, mocker, tmp_path):
        import json
        dash_path = tmp_path / "dashboard.json"
        dash_content = {
            "dashboard": {
                "title": "PyDoc Assistant Monitoring",
                "panels": [{"id": 1, "type": "timeseries"}],
            }
        }
        dash_path.write_text(json.dumps(dash_content), encoding="utf-8")

        mock_api = mocker.MagicMock()

        def fake_post(*a, **kw):
            resp = mocker.MagicMock()
            resp.json.return_value = {
                "dashboard": {"title": "PyDoc Assistant Monitoring", "panels": [{"id": 1, "type": "timeseries"}]}
            }
            resp.raise_for_status.return_value = None
            return resp

        mock_api.post = fake_post

        from grafana.init import import_dashboard
        result = import_dashboard(mock_api, str(dash_path))
        assert "dashboard" in result
        assert result["dashboard"]["title"] == "PyDoc Assistant Monitoring"

    def test_dashboard_has_six_panels(self):
        import json, os
        path = os.path.join(os.path.dirname(__file__), "..", "grafana", "dashboard.json")
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        panels = raw.get("dashboard", raw).get("panels", [])
        assert len(panels) >= 5

    def test_dashboard_panel_types(self):
        import json, os
        path = os.path.join(os.path.dirname(__file__), "..", "grafana", "dashboard.json")
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        panels = raw.get("dashboard", raw).get("panels", [])
        panel_types = {p["type"] for p in panels}
        assert "timeseries" in panel_types
        assert "piechart" in panel_types or "stat" in panel_types
