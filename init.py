"""Initialize DB tables and provision Grafana."""

import os
import sys

_project_root = os.path.abspath(os.path.dirname(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def create_db_tables():
    from app.db import get_connection, init_db
    conn = get_connection()
    try:
        init_db(conn)
        print("Database tables created.")
    finally:
        conn.close()


def provision_grafana():
    from grafana.init import provision
    try:
        provision()
        print("Grafana datasource and dashboard provisioned.")
    except Exception as e:
        print(f"Grafana provisioning skipped (not running?): {e}")


def main():
    create_db_tables()
    provision_grafana()


if __name__ == "__main__":
    main()
