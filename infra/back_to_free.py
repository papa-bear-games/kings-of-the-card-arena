#!/usr/bin/env python3
"""Moves one copy of the game's database (staging or production) from a paid tier back to the Azure
SQL free offer, on the same shared server and under the same name, so the game needs no new settings.

Run by the "Database back to free" workflow. Azure can't switch a paid database back to the free offer
in place, so this copies it instead:

    back_to_free.py --resource-group rg-card-arena --shared-resource-group rg-portfolio-shared \\
        --environment production

  1. Check the database is on a paid tier (shared-base.sh says free=false); otherwise do nothing.
  2. Delete the API container app, so nothing writes to the database while it is copied. Players see
     the game as down until the deploy that follows creates the API again.
  3. Export the database to a BACPAC file, rename it to <name>-paid-<time>, create the free database
     under the old name from infra/modules/database.bicep and import the file into it.
  4. Check that the copy has the same migrations and the same row count in every table, then delete
     the paid database (Azure keeps a deleted database's backups for 7 days, so it can be restored).

If anything fails after the rename, the new database is deleted and the paid one gets its name back,
so the next deploy puts the game back where it was. Needs the Azure CLI signed in as an admin of the
shared SQL server (the deploy app), the .NET SDK and sqlpackage.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from move_to_shared_base import (DATABASE_TEMPLATE, SQL_RESOURCE, TAGS, az, differences,  # noqa: E402
                                 inspect_database, log, public_ip, shared_base, sqlpackage)


def report(environment, target, paid, source, seconds):
    return "\n".join([
        f"### ✅ {environment.capitalize()}'s database is back on the free offer",
        "",
        f"- Copied `{target['database']}` on `{target['server']}` to a new free database of the same name "
        f"in **{seconds / 60:.1f} minutes**.",
        f"- {len(source['tables'])} tables, {sum(source['tables'].values())} rows, "
        f"migration `{(source['migrations'] or ['none'])[-1]}`; the copy matches.",
        f"- Deleted the paid copy `{paid}`. It can be restored from Azure's deleted databases for 7 days.",
        "",
    ])


def run(group, shared_group, environment):
    target = shared_base(shared_group, environment)
    if target.get("ready") != "true":
        raise RuntimeError(f"{environment.capitalize()} has no database on the shared base yet.")
    if target.get("free") == "true":
        log(f"{target['database']} is already on the free offer; nothing to do.")
        return None
    server, name = target["server"], target["database"]
    fqdn = f"{server}.database.windows.net"
    stamp = time.strftime("%Y%m%d%H%M", time.gmtime())
    paid = f"{name}-paid-{stamp}"
    rule = f"back-to-free-{stamp}"
    renamed = created = done = False
    clock = time.monotonic()

    log(f"Letting this machine through the firewall of {server}.")
    ip = public_ip()
    az("sql", "server", "firewall-rule", "create", "--resource-group", shared_group, "--server", server,
       "--name", rule, "--start-ip-address", ip, "--end-ip-address", ip)
    try:
        # The OIDC sign-in expires after 5 minutes; the database token lasts about an hour.
        token = az("account", "get-access-token", "--resource", SQL_RESOURCE, "--query", "accessToken")
        before = inspect_database(fqdn, name, token)
        log(f"{name} has {len(before['tables'])} tables and {sum(before['tables'].values())} rows.")

        apps = az("containerapp", "list", "--resource-group", group, "--query", "[?ends_with(name, '-api')].name") or []
        for app in apps:
            log(f"Deleting the API container app {app}; the game is down until the deploy finishes.")
            az("containerapp", "delete", "--resource-group", group, "--name", app, "--yes")
        source = inspect_database(fqdn, name, token)  # again, now nothing writes to it

        with tempfile.TemporaryDirectory() as folder:
            bacpac = os.path.join(folder, f"{name}.bacpac")
            log(f"Exporting {name}...")
            sqlpackage("/Action:Export", f"/SourceServerName:{fqdn}", f"/SourceDatabaseName:{name}",
                       f"/AccessToken:{token}", f"/TargetFile:{bacpac}")
            log(f"Exported {os.path.getsize(bacpac) / 1e6:.1f} MB. Renaming the paid database to {paid}.")
            az("sql", "db", "rename", "--resource-group", shared_group, "--server", server,
               "--name", name, "--new-name", paid)
            renamed = True

            created = True
            log(f"Creating the free database {name}...")
            az("deployment", "group", "create", "--resource-group", shared_group,
               "--name", f"card-arena-database-{environment}", "--template-file", str(DATABASE_TEMPLATE),
               "--parameters", f"serverName={server}", f"databaseName={name}", f"location={target['location']}",
               f"tags={json.dumps({**TAGS, 'environment': environment})}")
            log(f"Importing into {name}...")
            sqlpackage("/Action:Import", f"/TargetServerName:{fqdn}", f"/TargetDatabaseName:{name}",
                       f"/AccessToken:{token}", f"/SourceFile:{bacpac}")

        problems = differences(source, inspect_database(fqdn, name, token))
        if problems:
            raise RuntimeError("The copy doesn't match the paid database: " + " ".join(problems))
        done = True
        log(f"The copy matches. Deleting the paid database {paid}.")
        try:
            az("sql", "db", "delete", "--resource-group", shared_group, "--server", server, "--name", paid, "--yes")
        except RuntimeError as error:
            log(f"::warning::Couldn't delete {paid}; delete it in the portal, it still costs money. {error}")
        return report(environment, target, paid, source, time.monotonic() - clock)
    finally:
        if not done:
            if created:
                log(f"Deleting the new {name}, so the paid database can have its name back.")
                try:
                    az("sql", "db", "delete", "--resource-group", shared_group, "--server", server, "--name", name, "--yes")
                except RuntimeError as error:
                    log(f"::warning::Couldn't delete the new {name}; delete it in the portal. {error}")
            if renamed:
                log(f"Renaming {paid} back to {name}.")
                try:
                    az("sql", "db", "rename", "--resource-group", shared_group, "--server", server,
                       "--name", paid, "--new-name", name)
                except RuntimeError as error:
                    log(f"::error::Couldn't rename {paid} back to {name}; rename it in the portal before deploying. {error}")
        try:
            az("sql", "server", "firewall-rule", "delete", "--resource-group", shared_group, "--server", server,
               "--name", rule)
        except RuntimeError as error:
            log(f"::warning::Couldn't remove the firewall rule {rule} on {server}; remove it in the portal. {error}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--resource-group", required=True, help="the game's resource group for this environment")
    parser.add_argument("--shared-resource-group", required=True)
    parser.add_argument("--environment", required=True, choices=["staging", "production"])
    args = parser.parse_args(argv)

    try:
        summary = run(args.resource_group, args.shared_resource_group, args.environment)
    except RuntimeError as error:
        log(f"::error::{error}")
        return 1
    if summary:
        print(summary)
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a", encoding="utf-8") as handle:
                handle.write(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
