-- Question: How does playtime/engagement vary by genre?
-- Note: SteamSpy's playtime fields (average_forever, average_2weeks, median_forever)
-- returned 0 for all 50 tracked games in this dataset. Root cause: an April 2018
-- Steam privacy change made playtime hidden by default for most accounts, which
-- broke SteamSpy's ability to sample playtime data industry-wide - a permanent,
-- documented limitation of this source, confirmed here rather than assumed.
-- Substitute metric: average concurrent players (Steam's official API, not
-- privacy-gated) as a proxy for real engagement by genre.

SELECT g.genre_name,
       COUNT(DISTINCT a.appid) AS games_in_genre,
       ROUND(AVG(p.concurrent_players)) AS avg_concurrent_players
FROM player_snapshots p
         JOIN apps a ON a.appid = p.appid
         JOIN app_genres ag ON ag.appid = a.appid
         JOIN genres g ON g.genre_id = ag.genre_id
GROUP BY g.genre_name
ORDER BY avg_concurrent_players DESC;