-- Dimension table: static app metadata
CREATE TABLE apps (
                      appid           INTEGER PRIMARY KEY,
                      name            TEXT NOT NULL,
                      developer       TEXT,
                      publisher       TEXT,
                      release_date    DATE,
                      is_free         BOOLEAN DEFAULT FALSE,
                      created_at      TIMESTAMP NOT NULL DEFAULT now()
);

-- Genre dimension + many-to-many junction
CREATE TABLE genres (
                        genre_id    SERIAL PRIMARY KEY,
                        genre_name  TEXT UNIQUE NOT NULL
);

CREATE TABLE app_genres (
                            appid       INTEGER REFERENCES apps(appid) ON DELETE CASCADE,
                            genre_id    INTEGER REFERENCES genres(genre_id) ON DELETE CASCADE,
                            PRIMARY KEY (appid, genre_id)
);

-- Time series: price/discount over time (Store API)
CREATE TABLE price_snapshots (
                                 snapshot_id     SERIAL PRIMARY KEY,
                                 appid           INTEGER NOT NULL REFERENCES apps(appid) ON DELETE CASCADE,
                                 captured_at     TIMESTAMP NOT NULL DEFAULT now(),
                                 price_usd       NUMERIC(10,2),
                                 discount_pct    SMALLINT
);

-- Time series: concurrent players over time (official Web API)
CREATE TABLE player_snapshots (
                                  snapshot_id         SERIAL PRIMARY KEY,
                                  appid               INTEGER NOT NULL REFERENCES apps(appid) ON DELETE CASCADE,
                                  captured_at         TIMESTAMP NOT NULL DEFAULT now(),
                                  concurrent_players  INTEGER
);

-- Periodic snapshot: ownership/playtime estimates (SteamSpy)
CREATE TABLE ownership_stats (
                                 snapshot_id                     SERIAL PRIMARY KEY,
                                 appid                           INTEGER NOT NULL REFERENCES apps(appid) ON DELETE CASCADE,
                                 captured_at                     TIMESTAMP NOT NULL DEFAULT now(),
                                 owners_low                      BIGINT,
                                 owners_high                     BIGINT,
                                 avg_playtime_forever_minutes    INTEGER,
                                 avg_playtime_2weeks_minutes     INTEGER,
                                 median_playtime_forever_minutes INTEGER,
                                 positive_reviews                INTEGER,
                                 negative_reviews                INTEGER
);

-- Achievement completion rates (official Web API, global stats)
CREATE TABLE achievement_stats (
                                   snapshot_id             SERIAL PRIMARY KEY,
                                   appid                   INTEGER NOT NULL REFERENCES apps(appid) ON DELETE CASCADE,
                                   achievement_name        TEXT NOT NULL,
                                   global_completion_pct   NUMERIC(5,2),
                                   captured_at             TIMESTAMP NOT NULL DEFAULT now()
);

-- Indexes for the time-series lookups we'll actually query
CREATE INDEX idx_price_snapshots_appid_time ON price_snapshots (appid, captured_at);
CREATE INDEX idx_player_snapshots_appid_time ON player_snapshots (appid, captured_at);
CREATE INDEX idx_ownership_stats_appid_time ON ownership_stats (appid, captured_at);
CREATE INDEX idx_achievement_stats_appid ON achievement_stats (appid);