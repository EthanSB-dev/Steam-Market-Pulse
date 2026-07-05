-- Question: How does engagement (concurrent players) vary by genre?
-- Note: SteamSpy's playtime data was unusable (see prior note); using average
-- concurrent players from the official Steam API as a substitute engagement metric.
-- Genres with fewer than 3 tracked games are excluded - a single atypical game
-- (e.g. Wallpaper Engine, a background utility with unusually high concurrent
-- usage) can otherwise dominate a small genre's average and misrepresent it.

SELECT g.genre_name,
       COUNT(DISTINCT a.appid) AS games_in_genre,
       ROUND(AVG(p.concurrent_players)) AS avg_concurrent_players
FROM player_snapshots p
         JOIN apps a ON a.appid = p.appid
         JOIN app_genres ag ON ag.appid = a.appid
         JOIN genres g ON g.genre_id = ag.genre_id
GROUP BY g.genre_name
HAVING COUNT(DISTINCT a.appid) >= 3
ORDER BY avg_concurrent_players DESC;