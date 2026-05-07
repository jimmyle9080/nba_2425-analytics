-- ============================================================
-- NBA 2024-25 Season Analytics
-- Script 02: Advanced Window Function Analysis
-- Author: Jimmy Le-Nguyen
-- ============================================================

-- 1. Season scoring rank -- who led the league in points per game?
SELECT
    player,
    team,
    COUNT(*)                  AS games,
    ROUND(AVG(pts), 1)        AS avg_pts,
    ROUND(AVG(gmsc), 1)       AS avg_gmsc,
    RANK() OVER (ORDER BY AVG(pts) DESC)     AS pts_rank,
    RANK() OVER (ORDER BY AVG(gmsc) DESC)    AS gmsc_rank,
    RANK() OVER (ORDER BY AVG(ts_pct) DESC)  AS ts_rank
FROM qualified_logs
GROUP BY player, team
HAVING games >= 41
ORDER BY avg_pts DESC
LIMIT 25;

-- 2. Rolling 10-game average for top scorers
-- Shows hot streaks and cold streaks throughout the season
SELECT
    player,
    date,
    game_number,
    pts,
    AVG(pts) OVER (
        PARTITION BY player
        ORDER BY date
        ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) AS rolling_10g_pts,
    AVG(gmsc) OVER (
        PARTITION BY player
        ORDER BY date
        ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) AS rolling_10g_gmsc,
    SUM(pts) OVER (
        PARTITION BY player
        ORDER BY date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_pts
FROM qualified_logs
WHERE player IN (
    SELECT player FROM player_season_averages
    WHERE games_played >= 41
    ORDER BY avg_pts DESC
    LIMIT 10
)
ORDER BY player, date;

-- 3. Best single game performances of the 2024-25 season
SELECT
    player,
    team,
    opp,
    date,
    pts,
    trb,
    ast,
    stl,
    blk,
    gmsc,
    plus_minus,
    RANK() OVER (ORDER BY gmsc DESC)      AS gmsc_rank,
    RANK() OVER (ORDER BY pts DESC)       AS pts_rank
FROM qualified_logs
ORDER BY gmsc DESC
LIMIT 25;

-- 4. Consistency score -- standard deviation of scoring
-- Low stdev = consistent, High stdev = streaky
SELECT
    player,
    team,
    COUNT(*)                      AS games,
    ROUND(AVG(pts), 1)            AS avg_pts,
    ROUND(AVG(gmsc), 1)           AS avg_gmsc,
    -- SQLite doesn't have STDEV natively so we calculate it manually
    ROUND(
        SQRT(
            AVG(pts * pts) - AVG(pts) * AVG(pts)
        ), 2
    )                             AS pts_stdev,
    RANK() OVER (
        ORDER BY AVG(pts) DESC
    )                             AS scoring_rank
FROM qualified_logs
GROUP BY player, team
HAVING games >= 41
ORDER BY pts_stdev ASC
LIMIT 20;

-- 5. Home vs away performance split
SELECT
    player,
    CASE WHEN opp LIKE '@%' OR opp IS NULL THEN 'Away' ELSE 'Home' END AS location,
    COUNT(*)               AS games,
    ROUND(AVG(pts), 1)     AS avg_pts,
    ROUND(AVG(gmsc), 1)    AS avg_gmsc,
    ROUND(AVG(fg_pct), 3)  AS avg_fg_pct,
    ROUND(AVG(plus_minus), 1) AS avg_plus_minus
FROM qualified_logs
WHERE player IN (
    SELECT player FROM player_season_averages
    WHERE games_played >= 41
    ORDER BY avg_pts DESC LIMIT 15
)
GROUP BY player, location
ORDER BY player, location;

-- 6. Month by month performance trends
-- Shows which players peaked during playoffs vs regular season
SELECT
    player,
    month,
    month_num,
    COUNT(*)               AS games,
    ROUND(AVG(pts), 1)     AS avg_pts,
    ROUND(AVG(gmsc), 1)    AS avg_gmsc,
    ROUND(AVG(ts_pct), 3)  AS avg_ts_pct,
    ROUND(AVG(plus_minus), 1) AS avg_plus_minus,
    SUM(win)               AS wins
FROM qualified_logs
WHERE player IN (
    SELECT player FROM player_season_averages
    WHERE games_played >= 41
    ORDER BY avg_gmsc DESC LIMIT 10
)
GROUP BY player, month, month_num
ORDER BY player, month_num;

-- 7. Back to back game performance
-- Do players decline in second game of back to backs?
WITH game_gaps AS (
    SELECT
        player,
        date,
        pts,
        gmsc,
        mp_decimal,
        plus_minus,
        LAG(date) OVER (PARTITION BY player ORDER BY date) AS prev_game_date,
        JULIANDAY(date) - JULIANDAY(
            LAG(date) OVER (PARTITION BY player ORDER BY date)
        ) AS days_rest
    FROM qualified_logs
)
SELECT
    CASE
        WHEN days_rest = 1 THEN 'Back to Back (0 days rest)'
        WHEN days_rest = 2 THEN '1 Day Rest'
        WHEN days_rest = 3 THEN '2 Days Rest'
        ELSE '3+ Days Rest'
    END AS rest_situation,
    COUNT(*)                   AS game_logs,
    ROUND(AVG(pts), 1)         AS avg_pts,
    ROUND(AVG(gmsc), 1)        AS avg_gmsc,
    ROUND(AVG(mp_decimal), 1)  AS avg_minutes,
    ROUND(AVG(plus_minus), 1)  AS avg_plus_minus
FROM game_gaps
WHERE days_rest IS NOT NULL
GROUP BY rest_situation
ORDER BY MIN(days_rest);
