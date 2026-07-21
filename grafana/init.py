"""Provision Grafana with PostgreSQL datasource and import dashboard."""

import json
import os

import httpx

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")


def _client(api_client=None):
    if api_client is not None:
        return api_client
    return httpx.Client(auth=(GRAFANA_USER, GRAFANA_PASSWORD), base_url=GRAFANA_URL)


def _datasource_payload() -> dict:
    return {
        "name": "PyDoc PostgreSQL",
        "uid": "pydoc-pg",
        "type": "postgres",
        "access": "proxy",
        "url": os.getenv("POSTGRES_HOST", "postgres") + ":" + os.getenv("POSTGRES_PORT", "5432"),
        "user": os.getenv("POSTGRES_USER", "user"),
        "secureJsonData": {"password": os.getenv("POSTGRES_PASSWORD", "password")},
        "jsonData": {
            "database": os.getenv("POSTGRES_DB", "pydoc_assistant"),
            "sslmode": "disable",
        },
    }


def create_postgres_datasource(api_client=None) -> dict:
    payload = _datasource_payload()
    c = _client(api_client)
    c.delete("/api/datasources/name/PyDoc PostgreSQL")
    r = c.post("/api/datasources", json=payload)
    r.raise_for_status()
    return r.json()


def import_dashboard(api_client=None, path: str = "grafana/dashboard.json") -> dict:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    payload = {"dashboard": raw["dashboard"], "overwrite": True}
    c = _client(api_client)
    r = c.post("/api/dashboards/db", json=payload)
    r.raise_for_status()
    return r.json()


def provision():
    create_postgres_datasource()
    import_dashboard()
    print("Grafana datasource and dashboard provisioned.")


if __name__ == "__main__":
    provision()
