# Steam Market Pulse

A data engineering + analytics project that tracks Steam game ownership, pricing, and player engagement over time, using a fully automated Python → PostgreSQL pipeline.

Rather than a one-time data pull, this project is built as a *living* pipeline: a scheduled job collects fresh data every 4 hours, meaning the dataset — and the trends visible in it — genuinely deepen the longer it runs.

## Why this project

Game studios and analysts track the same core signals this project does: how many people own a game, how engaged they actually are with it, how pricing/discounts move, and how deeply players complete it. This project treats Steam as a real market to analyze, not just an API to call — the goal was to practice the full lifecycle of a data project: schema design, ETL, automation, data-quality investigation, SQL analysis, and visualization.

## Architecture

Steam Web API (official)          Python ETL                PostgreSQL              Consumers
GetNumberOfCurrentPlayers    ┐
GetGlobalAchievementPercent  ├──►  ingestion scripts   ──►  apps (dimension)  ──►  SQL analysis
│     (requests, retries,       genres/app_genres      (sql/analysis/)
Steam Storefront API         │      rate limiting,           price_snapshots
(appdetails, pricing)        ┤      idempotent upserts)      player_snapshots   ──►  Streamlit
│                                ownership_stats        dashboard
SteamSpy (owners, reviews)   ┘                                achievement_stats      (dashboard/app.py)

Scheduled via cron (every 4 hours) →  collect_snapshots.py

## Data sources

| Source | What it provides | Auth required |
|---|---|---|
| [Steam Web API](https://steamcommunity.com/dev) | Live concurrent player counts, global achievement completion % | Yes (free key) |
| [Steam Storefront API](https://store.steampowered.com/api/appdetails) | Game metadata, genres, developer/publisher, pricing | No |
| [SteamSpy](https://steamspy.com) | Ownership estimates, review counts | No |

Games tracked are seeded dynamically from SteamSpy's "top 100 in 2 weeks" list rather than a hardcoded list, so the tracked set reflects genuinely popular current titles.

## Database design

7 tables, split deliberately into **dimension** (static) and **time-series/fact** (repeating) data:

- `apps` — static game metadata, keyed on Steam's own `appid` (a natural key, not a generated one)
- `genres` / `app_genres` — a many-to-many junction, since a game can belong to multiple genres
- `price_snapshots`, `player_snapshots` — time series, one row per collection run
- `ownership_stats`, `achievement_stats` — periodic snapshots (these change slowly, so they're refreshed less often than price/player data)

Design decisions worth calling out:
- `NUMERIC`, not `FLOAT`, for all price/percentage columns — floating point rounds money and percentages in ways that silently corrupt them
- `ON DELETE CASCADE` on every foreign key, so removing a tracked game cleans up its history automatically
- Full schema: [`sql/001_create_schema.sql`](sql/001_create_schema.sql)

## Pipeline

| Script | Purpose | Frequency |
|---|---|---|
| `src/ingestion/load_apps.py` | Seeds tracked games + metadata + genres | Run once (or to refresh the tracked list) |
| `src/ingestion/load_stats.py` | Ownership estimates + achievement completion | Run periodically |
| `src/ingestion/collect_snapshots.py` | Current player count + price/discount | **Automated every 4 hours via cron** |

All ingestion is idempotent (`ON CONFLICT ... DO UPDATE`) and defensive — every external API call is wrapped so a single failed request (a delisted app, a flaky server response) is logged and skipped rather than crashing the whole run.

## Data quality: what I found and how I handled it

Real third-party data has real limitations, and I treated finding them as part of the deliverable rather than a problem to hide:

- **SteamSpy's playtime fields (`average_forever`, `average_2weeks`, `median_forever`) were confirmed unusable for 100% of tracked games.** Root cause: a 2018 Steam privacy default change made playtime private for most accounts, breaking SteamSpy's ability to sample it industry-wide. I verified this with a diagnostic query before concluding it, then substituted concurrent player count as a more reliable engagement proxy throughout the analysis.
- **Small-sample skew**, caught twice independently: a single-achievement game briefly appeared to have the "hardest" achievement set, and a background utility (Wallpaper Engine, tagged with several niche genres) skewed 4 genre averages built on just 1 game each. Both are now filtered with minimum-sample-size thresholds (`HAVING COUNT(*) >= 5` / `>= 3`), documented directly in the relevant queries.
- **SteamSpy's owner counts are ranges, not exact figures** (e.g. `"10,000,000 .. 20,000,000"`), parsed into `owners_low`/`owners_high` and reduced to a midpoint estimate for ranking — a deliberate, explainable methodology choice rather than an arbitrary one.

## Analysis

Each query in [`sql/analysis/`](sql/analysis/) answers one specific question, with its reasoning documented in a comment block at the top of the file:

- `most_owned_games.sql` — which games have the largest estimated player base
- `playtime_by_genre.sql` — engagement by genre (reframed from playtime to concurrent players, see above)
- `most_engaged_games.sql` — individual games with the highest sustained concurrent players
- `achievement_completion_rates.sql` — which games are hardest/easiest to fully complete
- `popular_but_rarely_completed.sql` — games above the popularity median but below the completion median, using Postgres CTEs and `PERCENTILE_CONT`

## Dashboard

An interactive Streamlit dashboard (`dashboard/app.py`) built directly on top of the same database — no duplicated logic between analysis and visualization:

- Live overview metrics (games tracked, snapshots collected, last updated)
- Most owned games, engagement by genre, current active discounts, achievement completion rates
- An interactive per-game selector with live player count and price history charts

*(Add a screenshot here once you have one you like: `![dashboard screenshot](docs/dashboard.png)`)*

## Setup

```bash
git clone https://github.com/<your-username>/steam-market-pulse.git
cd steam-market-pulse
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

STEAM_API_KEY=your_steam_web_api_key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=steam_market_pulse
DB_USER=
DB_PASSWORD=

Create the database and schema:
```bash
createdb steam_market_pulse
psql -d steam_market_pulse -f sql/001_create_schema.sql
```

Run the pipeline:
```bash
python src/ingestion/load_apps.py
python src/ingestion/load_stats.py
python src/ingestion/collect_snapshots.py
```

Launch the dashboard:
```bash
streamlit run dashboard/app.py
```

To automate ongoing collection, schedule `run_snapshot_collection.sh` via cron (see script for details).

## Project structure

steam-market-pulse/
├── src/
│   ├── ingestion/     # ETL scripts
│   └── db/            # Connection handling
├── sql/
│   ├── 001_create_schema.sql
│   └── analysis/      # One file per analysis question
├── dashboard/          # Streamlit app
├── tests/
└── run_snapshot_collection.sh   # Cron entry point

## What this project demonstrates

- Relational schema design (dimension vs. fact tables, many-to-many modeling, appropriate data types)
- ETL pipeline design: idempotency, error handling, rate limiting, unattended automation via cron
- Working across multiple real-world APIs with differing reliability, and diagnosing a genuine third-party data-quality dead end rather than reporting misleading numbers
- SQL: joins across 5+ tables, CTEs, window/aggregate functions, `HAVING`, `DISTINCT ON`, `PERCENTILE_CONT`
- Turning raw analysis into an interactive, parameterized dashboard

## Possible future improvements

- Integrate a historical pricing API (e.g. IsThereAnyDeal) for multi-year price trends, beyond what this project's own collection window can provide
- Expand tracked games beyond the initial 50
- Add automated tests for the ingestion scripts
- Deploy the dashboard publicly (Streamlit Community Cloud) rather than running it locally