"""Tests for Dockerfile and docker-compose.yaml."""

import os
import yaml
import subprocess

import pytest


class TestDockerfile:
    def test_dockerfile_exists(self):
        assert os.path.exists("Dockerfile")

    def test_dockerfile_uses_python_312(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "python:3.12" in content or "python:3.12-slim" in content

    def test_dockerfile_exposes_port_8501(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "EXPOSE 8501" in content

    def test_dockerfile_installs_uv(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "uv" in content or "astral-sh" in content

    def test_dockerfile_cmd_runs_streamlit(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "streamlit" in content
        assert "8501" in content


class TestDockerCompose:
    def test_compose_file_exists(self):
        path = "docker-compose.yaml" if os.path.exists("docker-compose.yaml") else "docker-compose.yml"
        assert os.path.exists(path)

    def test_compose_has_required_services(self):
        path = "docker-compose.yaml" if os.path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        services = set(config["services"].keys())
        assert "postgres" in services
        assert "app" in services
        assert "grafana" in services

    def test_postgres_healthcheck_configured(self):
        path = "docker-compose.yaml" if os.path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        healthcheck = config["services"]["postgres"].get("healthcheck", {})
        assert "test" in healthcheck
        assert "pg_isready" in " ".join(healthcheck["test"])

    def test_app_depends_on_postgres_healthy(self):
        path = "docker-compose.yaml" if os.path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        deps = config["services"]["app"].get("depends_on", {})
        assert "postgres" in deps
        if isinstance(deps["postgres"], dict):
            assert deps["postgres"].get("condition") == "service_healthy"

    def test_app_passes_openai_api_key(self):
        path = "docker-compose.yaml" if os.path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        env = config["services"]["app"].get("environment", {})
        assert "OPENAI_API_KEY" in str(env)

    def test_grafana_exposes_port_3000(self):
        path = "docker-compose.yaml" if os.path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        ports = config["services"]["grafana"].get("ports", [])
        assert any("3000" in str(p) for p in ports)

    def test_volumes_defined(self):
        path = "docker-compose.yaml" if os.path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        volumes = config.get("volumes", {})
        assert "postgres_data" in volumes
        assert "grafana_data" in volumes


class TestInitScript:
    def test_init_script_exists(self):
        assert os.path.exists("init.py")

    def test_init_creates_tables(self, mocker):
        mocker.patch("init.create_db_tables")
        mocker.patch("init.provision_grafana")
        import init
        init.main()
        init.create_db_tables.assert_called_once()
        init.provision_grafana.assert_called_once()


@pytest.mark.integration
class TestDockerBuild:
    def test_image_builds_successfully(self):
        result = subprocess.run(
            ["docker", "build", "-t", "pydoc-assistant:test", "."],
            capture_output=True, text=True, timeout=300
        )
        assert result.returncode == 0, f"Build failed:\n{result.stderr}"

    @pytest.mark.integration
    def test_container_starts_and_serves(self):
        """Build and run container, verify Streamlit responds on 8501."""
        subprocess.run(["docker", "rm", "-f", "pydoc-test"], capture_output=True)
        subprocess.run([
            "docker", "run", "-d", "--name", "pydoc-test",
            "-p", "18501:8501",
            "-e", "OPENAI_API_KEY=sk-test",
            "pydoc-assistant:test"
        ], check=True, timeout=30)
        import time; time.sleep(5)
        result = subprocess.run(
            ["curl", "-s", "-o", "nul", "-w", "%{http_code}", "http://localhost:18501"],
            capture_output=True, text=True, timeout=10
        )
        subprocess.run(["docker", "rm", "-f", "pydoc-test"], capture_output=True)
        assert result.stdout.strip() == "200" or result.stdout.strip().startswith("2")
