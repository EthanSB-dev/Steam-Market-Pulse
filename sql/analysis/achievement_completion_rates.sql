-- Question: Which games have the highest / lowest achievement completion rates?
-- Filtered to games with >= 5 tracked achievements to avoid small-sample skew
-- (a game with only 1-2 achievements can show a misleadingly extreme average).

-- Lowest completion rates (hardest / most demanding achievement sets)
SELECT a.name,
       COUNT(*) AS achievements_tracked,
       ROUND(AVG(ac.global_completion_pct), 1) AS avg_completion_pct
FROM achievement_stats ac
         JOIN apps a ON a.appid = ac.appid
GROUP BY a.name
HAVING COUNT(*) >= 5
ORDER BY avg_completion_pct ASC
LIMIT 10;

-- Highest completion rates (easiest / most casual achievement sets)
SELECT a.name,
       COUNT(*) AS achievements_tracked,
       ROUND(AVG(ac.global_completion_pct), 1) AS avg_completion_pct
FROM achievement_stats ac
         JOIN apps a ON a.appid = ac.appid
GROUP BY a.name
HAVING COUNT(*) >= 5
ORDER BY avg_completion_pct DESC
LIMIT 10;