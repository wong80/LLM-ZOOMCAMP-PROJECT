"""Integration tests for monitoring (PostgreSQL + Grafana)."""

import pytest
import json
import os


@pytest.mark.integration
class TestMonitoringIntegration:
    def test_full_monitoring_flow(self, db_connection, mocker):
        from app.db import save_conversation, save_feedback
        from tests.conftest import BASE_CONV

        conv = {**BASE_CONV, "id": "monitor-e2e"}
        save_conversation(db_connection, conv)
        save_feedback(db_connection, "monitor-e2e", -1)

        mock_api = mocker.MagicMock()
        mock_post = mocker.MagicMock()
        mock_post.raise_for_status.return_value = None
        mock_post.json.side_effect = [
            {"datasource": {"type": "postgres", "name": "PyDoc PostgreSQL", "uid": "test-uid"}},
            {"dashboard": {"panels": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}, {"id": 6}]}},
        ]
        mock_api.post = mocker.MagicMock(return_value=mock_post)

        from grafana.init import create_postgres_datasource, import_dashboard
        ds = create_postgres_datasource(mock_api)
        assert ds["datasource"]["uid"] is not None

        dash_path = os.path.join(os.path.dirname(__file__), "..", "grafana", "dashboard.json")
        dash = import_dashboard(mock_api, dash_path)
        assert len(dash["dashboard"]["panels"]) >= 5
