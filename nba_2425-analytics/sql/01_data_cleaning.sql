-- ============================================================
-- NBA 2024-25 Season Analytics
-- Script 01: Data Cleaning & Quality Checks
-- Author: Jimmy Le-Nguyen
-- Dataset: NBA Daily Leaders 2024-25 (28,265 game logs)
-- ============================================================

-- 1. Overview of the raw dataset
SELECT
    COUNT(*)                    AS total_game_logs,
    COUNT(DISTINCT player)      AS unique_players,
    COUNT(DISTINCT team)        AS unique_teams,
    MIN(date)                   AS season_start,
    MAX(date)                   AS season_end,
    ROUND(AVG(pts), 1)          AS avg_pts_per_game,
    ROUND(AVG(mp_decimal), 1)   AS avg_minutes_per_game
FROM game_logs;

-- 2. Identify missing values in key columns
SELECT
    COUNT(*)                                            AS total_records,
    SUM(CASE WHEN fg_pct   IS NULL THEN 1 ELSE 0 END)  AS missing_fg_pct,
    SUM(CASE WHEN ts_pct   IS NULL THEN 1 ELSE 0 END)  AS missing_ts_pct,
    SUM(CASE WHEN plus_minus IS NULL THEN 1 ELSE 0 END) AS missing_plus_minus,
    SUM(CASE WHEN mp_decimal IS NULL THEN 1 ELSE 0 END) AS missing_minutes
FROM game_logs;

-- 3. Players with very low minutes -- likely garbage time or DNP-CD
-- These should be filtered for meaningful analysis
SELECT
    player,
    COUNT(*)            AS games,
    ROUND(AVG(mp_decimal),1) AS avg_minutes,
    ROUND(AVG(pts), 1)  AS avg_pts
FROM game_logs
WHERE mp_decimal < 5.0
GROUP BY player
HAVING games > 5
ORDER BY games DESC
LIMIT 20;

-- 4. Create a qualified game logs view
-- Minimum 10 minutes played to filter out garbage time
CREATE VIEW IF NOT EXISTS qualified_logs AS
SELECT *
FROM game_logs
WHERE mp_decimal >= 10.0
  AND fga > 0;

-- 5. Season averages per player -- qualified games only
CREATE VIEW IF NOT EXISTS player_season_averages AS
SELECT
    player,
    team,
    COUNT(*)                        AS games_played,
    ROUND(AVG(mp_decimal), 1)       AS avg_minutes,
    ROUND(AVG(pts), 1)              AS avg_pts,
    ROUND(AVG(trb), 1)              AS avg_reb,
    ROUND(AVG(ast), 1)              AS avg_ast,
    ROUND(AVG(stl), 1)              AS avg_stl,
    ROUND(AVG(blk), 1)              AS avg_blk,
    ROUND(AVG(tov), 1)              AS avg_tov,
    ROUND(AVG(fg_pct), 3)           AS avg_fg_pct,
    ROUND(AVG(threeP_pct), 3)       AS avg_3p_pct,
    ROUND(AVG(ft_pct), 3)           AS avg_ft_pct,
    ROUND(AVG(ts_pct), 3)           AS avg_ts_pct,
    ROUND(AVG(gmsc), 1)             AS avg_gmsc,
    ROUND(AVG(plus_minus), 1)       AS avg_plus_minus,
    SUM(win)                        AS wins,
    ROUND(100.0*SUM(win)/COUNT(*),1) AS win_pct
FROM qualified_logs
GROUP BY player, team;
