# Decisions

Newest first. Design decisions about the code are ADRs in `docs/adr/`; this file holds decisions
about the repo and the project.

- 2026-10-15: The web game stays free and opens only from scottcoxdev.com (Scottie; ADR 0041).
- 2026-10-15: A paid Android version is built separately (Scottie): Unity, in its own private repo
  `kings-of-the-card-arena-android`, with a copy of this server, its own accounts and leaderboards,
  and cosmetics-only purchases. This repo is not changed for it.
- 2026-10-15: Renamed the repo to `kings-of-the-card-arena`, after the game (Scottie).
- 2026-10-15: The repo stays public, the only public Papa Bear game repo, because it is a
  portfolio piece and scottcoxdev.com links to its code (Scottie).
- 2026-10-13: Production's database stays on paid Basic (about $5 a month), which Scottie set on
  2026-10-10, rather than moving back to the free serverless offer (Scottie).
- 2026-10-13: The deploy no longer forces the free offer on a shared database someone moved to a
  paid tier; it leaves it as it is (Claude, so production deploys work again).

- 2026-10-13: Moved the repo from `scox115` to the `papa-bear-games` GitHub org (Scottie). Links,
  setup-script defaults and the image name now use `papa-bear-games`.
- 2026-10-13: Every repo carries `CLAUDE.md`, `docs/STATUS.md` and `docs/DECISIONS.md` so any
  Claude session can pick it up cold (Scottie).
- 2026-10-13: Claude may merge green PRs itself (Scottie).
