"""Structure of the L07 DAG, checked without installing Airflow in CI.

The rules come from the project step: a DAG file is structure only (no heavy
import, no work at parse time), the period comes from the run and never from the
clock, every task retries with a delay, and the alert fires once retries are
exhausted. `airflow dags list-import-errors` covers the real import locally.
"""

import ast
from pathlib import Path
import unittest


DAG_FILE = Path(__file__).resolve().parents[1] / "orchestration" / "dags" / "group6_marketplace_daily.py"
HEAVY_MODULES = {"pandas", "psycopg", "psycopg2", "sqlalchemy", "google", "pyarrow", "requests"}


class DagStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DAG_FILE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def dag_keywords(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "DAG":
                return {keyword.arg: keyword.value for keyword in node.keywords}
        self.fail("No DAG(...) call found")

    def task_calls(self):
        calls = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "DockerOperator":
                keywords = {keyword.arg: keyword.value for keyword in node.keywords}
                task_id = keywords["task_id"]
                name = task_id.value if isinstance(task_id, ast.Constant) else ast.unparse(task_id)
                calls[name] = keywords
        return calls

    def test_no_heavy_import_at_module_level(self):
        imported = set()
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertFalse(imported & HEAVY_MODULES, imported & HEAVY_MODULES)

    def test_period_comes_from_the_run_not_the_clock(self):
        for clock in ("date.today", "datetime.now", "datetime.utcnow", "pendulum.now", "time.time"):
            self.assertNotIn(clock, self.source)
        self.assertIn("{{ data_interval_start | ds }}", self.source)
        self.assertIn("{{ data_interval_end | ds }}", self.source)

    def test_schedule_is_utc_with_a_real_start_and_no_catchup(self):
        keywords = self.dag_keywords()
        self.assertIn("timezone='UTC'", ast.unparse(keywords["schedule"]).replace('"', "'"))
        self.assertIn("tz='UTC'", ast.unparse(keywords["start_date"]).replace('"', "'"))
        self.assertIs(keywords["catchup"].value, False)
        self.assertEqual(keywords["max_active_runs"].value, 1)

    def test_retries_with_delay_and_alert_after_the_last_attempt(self):
        default_args = self.dag_keywords()["default_args"]
        keys = {key.value for key in default_args.keys}
        self.assertTrue({"retries", "retry_delay", "on_failure_callback"} <= keys, keys)
        # Code only: the docstrings explain why on_retry_callback is not used.
        names = {node.arg for node in ast.walk(self.tree) if isinstance(node, ast.keyword)}
        names |= {node.value for node in ast.walk(self.tree)
                  if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) < 40}
        self.assertNotIn("on_retry_callback", names)

    def test_every_writing_task_is_there_and_scratch_tables_always_go(self):
        tasks = self.task_calls()
        self.assertTrue({"f'extract_{table}'", "f'load_{table}'", "drop_staging"} <= set(tasks), set(tasks))
        self.assertEqual(tasks["drop_staging"]["trigger_rule"].value, "all_done")
        self.assertTrue({"dbt_build"} <= set(tasks) or {"dbt_run", "dbt_test"} <= set(tasks), set(tasks))

    def test_database_url_is_not_rendered_in_the_ui(self):
        extract = self.task_calls()["f'extract_{table}'"]
        self.assertIn("DATABASE_URL", ast.unparse(extract["private_environment"]))
        self.assertNotIn("DATABASE_URL", ast.unparse(extract["environment"]))


if __name__ == "__main__":
    unittest.main()
