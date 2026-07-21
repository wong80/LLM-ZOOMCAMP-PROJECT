import os


class TestReadme:
    def test_readme_exists(self):
        assert os.path.exists("README.md")

    def test_readme_has_problem_statement(self):
        content = open("README.md", encoding="utf-8").read()
        assert "Problem" in content

    def test_readme_has_architecture(self):
        content = open("README.md", encoding="utf-8").read()
        assert "Architecture" in content or "┌" in content

    def test_readme_has_setup_instructions(self):
        content = open("README.md", encoding="utf-8").read()
        assert "uv sync" in content

    def test_readme_has_scoring_checklist(self):
        content = open("README.md", encoding="utf-8").read()
        assert "Scoring Checklist" in content

    def test_readme_has_evaluation_results(self):
        content = open("README.md", encoding="utf-8").read()
        assert "Hit Rate" in content or "MRR" in content or "RELEVANT" in content


class TestEnvExample:
    def test_env_example_exists(self):
        assert os.path.exists(".env.example")

    def test_env_example_contains_openai_key(self):
        content = open(".env.example", encoding="utf-8").read()
        assert "OPENAI_API_KEY" in content

    def test_env_example_not_real_key(self):
        content = open(".env.example", encoding="utf-8").read()
        assert "sk-proj" in content
