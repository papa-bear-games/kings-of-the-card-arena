# Status

- 2026-10-17: The three log alerts (server errors, slow requests, browser errors) are gone from the
  template and deleted by the deploy, to keep Azure under $10 a month (Scottie). The crash-loop email alert stays.
- 2026-10-15: The free web game now opens only for visitors who come from scottcoxdev.com; others
  see a page pointing there (ADR 0041). Scottie chose this because a separate, paid Android
  version is planned in its own repo, `kings-of-the-card-arena-android` (Unity, its own server and
  accounts). That work happens there, not here. Plan:
  https://claude.ai/code/artifact/638337ca-b99e-4261-ae82-6163c3b51563
- 2026-10-15: Repo renamed from `gameappportfolio` to `kings-of-the-card-arena`, the game's
  name. The history is unchanged and old links redirect. The repo stays public. Azure still trusts
  only the old name, so previews and deploys fail at "Sign in to Azure" until Scottie re-runs
  `infra/setup.ps1` for production and staging (checked 2026-10-20).
- 2026-10-13: Repo moved from `scox115` to the `papa-bear-games` GitHub org. The game itself is
  live and unchanged at https://play.scottcoxdev.com. After the move, deploys failed at "Sign in
  to Azure" because Azure only trusted the old repo name. Fixed the same day: Scottie removed the
  old `scox115` federated credentials and re-ran `infra/setup.ps1` for production and staging, so
  Azure now trusts `papa-bear-games/gameappportfolio` (both the name and ID forms). Public
  packages were turned on for the org and the `card-arena-api` package was made public, so
  Azure can pull the image without a token. The setup scripts now repoint an existing credential
  at a new repo name instead of failing with "already exists".
- 2026-10-13: The first deploy after the move reached staging but production stopped at the
  database step: "Cannot update paid database to free database". Production's `cardarena` was
  switched by hand from the free serverless offer to paid Basic (5 DTU, 2 GB) on 2026-10-10 from
  Scottie's account, while the template still asked for the free offer. The deploy now leaves a
  paid shared database as it is (`free=false` from `infra/shared-base.sh`). Scottie chose to keep
  Basic (about $5 a month, no cold starts). Staging stays on the free offer.
- 2026-10-10: Feature work done to date: boss fights, live duels, ranked seasons, friends,
  spectating, replays, guest play, two-factor sign-in (required for admins), recovery email,
  moderation, staging and previews, shared portfolio base (ADR 0040). See the ADR index.
- Next: whatever Scottie asks for. Dependabot PRs keep arriving and can be merged once green.
