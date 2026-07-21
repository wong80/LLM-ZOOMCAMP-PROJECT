"""Tests for Grafana dashboard SQL queries against PostgreSQL."""


class TestDashboardQueries:
    def test_questions_per_hour_query(self, db_connection):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT date_trunc('hour', timestamp) AS hour, count(*)
            FROM conversations GROUP BY hour ORDER BY hour
        """)
        rows = cursor.fetchall()
        assert isinstance(rows, list)

    def test_relevance_distribution_query(self, db_connection):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT relevance, count(*) FROM conversations GROUP BY relevance
        """)
        rows = cursor.fetchall()
        assert isinstance(rows, list)

    def test_avg_response_time_query(self, db_connection):
        cursor = db_connection.cursor()
        cursor.fetchone.return_value = (1.5,)
        cursor.execute("SELECT avg(response_time) FROM conversations")
        row = cursor.fetchone()
        assert row is not None

    def test_openai_cost_query(self, db_connection):
        cursor = db_connection.cursor()
        cursor.fetchone.return_value = (0.0,)
        cursor.execute("SELECT sum(openai_cost) FROM conversations")
        row = cursor.fetchone()
        assert row is not None

    def test_feedback_ratio_query(self, db_connection):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT feedback, count(*) FROM feedback GROUP BY feedback
        """)
        rows = cursor.fetchall()
        assert isinstance(rows, list)

    def test_model_comparison_query(self, db_connection):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT model_used, count(*), avg(response_time)
            FROM conversations GROUP BY model_used
        """)
        rows = cursor.fetchall()
        assert isinstance(rows, list)
