"""Tests for infra/back_to_free.py, with the Azure CLI, sqlpackage and the database reads faked.

    python3 -m unittest discover -s infra/tests
"""
import importlib.util
import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "back_to_free.py"
spec = importlib.util.spec_from_file_location("back_to_free", SCRIPT)
free = importlib.util.module_from_spec(spec)
spec.loader.exec_module(free)

SERVER = "sql-portfolio-xyz.database.windows.net"
TARGET = {"group": "rg-portfolio-shared", "environment": "cae-portfolio-xyz", "server": "sql-portfolio-xyz",
          "location": "centralus", "database": "cardarena", "ready": "true", "free": "false"}
DATA = {"migrations": ["001_Initial", "002_Shop"], "tables": {"dbo.Players": 12, "dbo.Battles": 340}}


class BackToFreeTests(unittest.TestCase):
    def setUp(self):
        self.target = dict(TARGET)
        self.copy = DATA
        self.calls = []
        self.fail_on = None

        def az(*args):
            command = " ".join(args)
            self.calls.append(command)
            if self.fail_on and command.startswith(self.fail_on):
                raise RuntimeError(f"az {self.fail_on} failed")
            if command.startswith("account get-access-token"):
                return "token"
            if command.startswith("containerapp list"):
                return ["ca-cardarena-api"]
            return None

        def sqlpackage(*args, attempts=3):
            self.calls.append(f"sqlpackage {args[0]}")
            if args[0] == "/Action:Export":
                Path(next(a for a in args if a.startswith("/TargetFile:")).split(":", 1)[1]).write_bytes(b"bacpac")

        reads = []

        def inspect(fqdn, name, token):
            self.assertEqual((fqdn, name), (SERVER, "cardarena"))
            reads.append(name)
            return DATA if len(reads) <= 2 else self.copy

        for name, value in [("az", az), ("sqlpackage", sqlpackage), ("inspect_database", inspect),
                            ("public_ip", lambda: "20.1.2.3"),
                            ("shared_base", lambda group, environment: self.target)]:
            patch = mock.patch.object(free, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def run_it(self):
        with redirect_stderr(io.StringIO()):
            return free.run("rg-card-arena", "rg-portfolio-shared", "production")

    def ran(self, prefix):
        return [c for c in self.calls if c.startswith(prefix)]

    def test_copies_to_a_free_database_and_deletes_the_paid_one(self):
        summary = self.run_it()
        self.assertIn("back on the free offer", summary)
        order = [c.split(" --")[0] for c in self.calls]
        self.assertLess(order.index("containerapp delete"), order.index("sqlpackage /Action:Export"))
        self.assertLess(order.index("sqlpackage /Action:Export"), order.index("sql db rename"))
        self.assertLess(order.index("sql db rename"), order.index("deployment group create"))
        self.assertLess(order.index("deployment group create"), order.index("sqlpackage /Action:Import"))
        rename = self.ran("sql db rename")[0]
        self.assertIn("--name cardarena --new-name cardarena-paid-", rename)
        self.assertIn("databaseName=cardarena", self.ran("deployment group create")[0])
        deleted = self.ran("sql db delete")
        self.assertEqual(len(deleted), 1)
        self.assertIn("--name cardarena-paid-", deleted[0])
        self.assertTrue(self.ran("sql server firewall-rule delete"))

    def test_does_nothing_when_already_free(self):
        self.target["free"] = "true"
        self.assertIsNone(self.run_it())
        self.assertEqual(self.calls, [])

    def test_a_copy_that_differs_puts_the_paid_database_back(self):
        self.copy = {"migrations": DATA["migrations"], "tables": {"dbo.Players": 12, "dbo.Battles": 339}}
        with self.assertRaises(RuntimeError):
            self.run_it()
        deleted = self.ran("sql db delete")
        self.assertEqual(len(deleted), 1)
        self.assertIn("--name cardarena --yes", deleted[0])
        renames = self.ran("sql db rename")
        self.assertEqual(len(renames), 2)
        self.assertIn("--new-name cardarena", renames[1])
        self.assertTrue(renames[1].endswith("--new-name cardarena"))
        self.assertTrue(self.ran("sql server firewall-rule delete"))

    def test_a_failed_export_leaves_the_paid_database_alone(self):
        def broken(*args, attempts=3):
            raise RuntimeError("sqlpackage /Action:Export failed")
        with mock.patch.object(free, "sqlpackage", broken), self.assertRaises(RuntimeError):
            self.run_it()
        self.assertEqual(self.ran("sql db rename"), [])
        self.assertEqual(self.ran("sql db delete"), [])


if __name__ == "__main__":
    unittest.main()
