Kind: web

# Kings of the Card Arena

Scottie's portfolio project: a turn-based card battler in the browser, built like a production
service. Live at https://play.scottcoxdev.com and linked from https://scottcoxdev.com
(papa-bear-games/scottcoxdev-site). Repo: https://github.com/papa-bear-games/kings-of-the-card-arena, public on
purpose so hiring managers can read the code (moved from
`scox115/gameappportfolio` on 2026-10-13 and renamed from `gameappportfolio` on 2026-10-15; old
links redirect).

The web game is free and opens only from scottcoxdev.com (ADR 0041). The paid Android version is a
separate project in `papa-bear-games/kings-of-the-card-arena-android`; changes for it don't go here.

Read this first, then `docs/STATUS.md` (where it stands and what waits on Scottie) and
`docs/DECISIONS.md` (decisions about the repo and project). Design decisions about the code are
Architecture Decision Records in `docs/adr/`; `ReadMe.md` and `docs/case-study.md` are the public
face of the project.

It is not one of the Papa Bear mobile puzzle games: the Play Store release workflow, ads, the
Papa Bear login packages and the Android secrets do not apply here.

## Tech

- .NET 10: ASP.NET Core Minimal APIs, SignalR, EF Core (SQL Server), Blazor WebAssembly client,
  RabbitMQ for match events, .NET Aspire for local runs.
- Azure, free tiers: Container Apps (API, scales to zero), Static Web Apps (client), serverless SQL
  on the shared portfolio base (`rg-portfolio-shared`, ADR 0040), Blob Storage, Key Vault, App
  Configuration, Application Insights. All in Bicep under `infra/`.
- GitHub Actions signs in to Azure with OIDC (no stored credentials). The trust is tied to the
  repository's name, so it must be re-added after a rename or transfer (`infra/setup.ps1`).

## Layout

| Folder | What lives there |
|---|---|
| `1.Core/Game.Core` | Domain: entities, battle rules, rating, shop. No framework references. |
| `2.Infrastructure/Game.Infrastructure` | EF Core context and migrations, Identity, storage, email, messaging. |
| `3.BackendAPI/Game.Api` | Endpoints, SignalR hubs, auth, background workers, health, telemetry. |
| `4.Frontend/Game.Client` | Blazor WebAssembly client (components with code-behind and scoped CSS, ADR 0039). |
| `5.Tests/` | Core, API, AppHost and Playwright browser tests (600+). |
| `6.Aspire/Game.AppHost` | Local orchestration: `dotnet run --project 6.Aspire/Game.AppHost`. |
| `infra/` | Bicep, one-time setup scripts, restore drill, ops dashboard. |
| `templates/new-app/` | Kit for putting another portfolio app on the shared base. |
| `loadtest/` | k6 load test. |

## Build, test, deploy

- Tests: `dotnet test --filter "Category!=Browser"` (no Docker needed). CI (`ci.yml`) also runs the
  SQL Server and browser tests on every PR; CodeQL runs too.
- Every merge to `main` runs CI, then `deploy.yml`: staging first, then production with the image
  staging tested (blue-green revisions, one-click `rollback.yml`). PRs get a client preview.
- The API image goes to `ghcr.io/papa-bear-games/card-arena-api` (named after the repo owner).
- Monthly `restore-drill.yml` proves the database backups restore.

## Rules to keep

- The server decides every game outcome; the client only picks a card (ADR 0002).
- Every significant design decision gets an ADR in `docs/adr/` and a line in its README.
- Docs travel with the code: every PR that changes behaviour, setup or structure updates, in the
  same PR, `ReadMe.md`, this file, `docs/STATUS.md`, `docs/DECISIONS.md` and any guide or ADR it
  makes wrong.
- Secrets never go in the repo or in chat.
- Steps for Scottie are numbered, one action per line, naming the site, app or page. His PC is
  "The-Hive-One"; his repos live under `C:\Users\scott\Repos\GitHub`.
- Claude may merge green PRs itself (Scottie, 2026-10-13).
