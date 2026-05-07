-- ============================================================
-- NBA 2024-25 Season Analytics
-- Script 03: Player & Team Analysis
-- Author: Jimmy Le-Nguyen
-- ============================================================

-- 1. MVP Composite Score -- 2024-25 season
-- Formula: weighted combination of scoring, efficiency, and impact
SELECT
    player,
    team,
    games_played,
    avg_pts,
    avg_reb,
    avg_ast,
    avg_ts_pct,
    avg_gmsc,
    avg_plus_minus,
    win_pct,
    ROUND(
        (avg_pts      * 0.30) +
        (avg_gmsc     * 0.25) +
        (avg_ts_pct   * 50  * 0.20) +
        (avg_plus_minus * 0.15) +
        (win_pct      * 0.10)
    , 2) AS mvp_composite_score,
    RANK() OVER (
        ORDER BY
            (avg_pts * 0.30) +
            (avg_gmsc * 0.25) +
            (avg_ts_pct * 50 * 0.20) +
            (avg_plus_minus * 0.15) +
            (win_pct * 0.10)
        DESC
    ) AS mvp_rank
FROM player_season_averages
WHERE games_played >= 41
ORDER BY mvp_composite_score DESC
LIMIT 15;

-- 2. Clutch performance analysis
-- Defined as games decided by 5 points or fewer
SELECT
    player,
    team,
    COUNT(*)                     AS clutch_games,
    ROUND(AVG(pts), 1)           AS avg_pts_clutch,
    ROUND(AVG(gmsc), 1)          AS avg_gmsc_clutch,
    ROUND(AVG(ts_pct), 3)        AS avg_ts_clutch,
    SUM(win)                     AS clutch_wins,
    ROUND(100.0*SUM(win)/COUNT(*),1) AS clutch_win_pct,
    ROUND(AVG(plus_minus), 1)    AS avg_plus_minus_clutch
FROM qualified_logs
WHERE ABS(plus_minus) <= 5
  AND player IN (
      SELECT player FROM player_season_averages
      WHERE games_played >= 41
      ORDER BY avg_pts DESC LIMIT 20
  )
GROUP BY player, team
HAVING clutch_games >= 15
ORDER BY clutch_win_pct DESC, avg_pts_clutch DESC;

-- 3. Triple double and near triple double tracker
SELECT
    player,
    team,
    date,
    pts,
    trb,
    ast,
    stl,
    blk,
    gmsc,
    CASE
        WHEN pts >= 10 AND trb >= 10 AND ast >= 10 THEN 'Triple Double'
        WHEN pts >= 20 AND trb >= 10 AND ast >= 10 THEN '20+ Triple Double'
        WHEN pts >= 10 AND trb >= 10 THEN 'Double Double (Pts+Reb)'
        WHEN pts >= 10 AND ast >= 10 THEN 'Double Double (Pts+Ast)'
        ELSE 'Standard'
    END AS game_type
FROM qualified_logs
WHERE (pts >= 10 AND trb >= 10) OR (pts >= 10 AND ast >= 10)
ORDER BY gmsc DESC;

-- 4. 40+ point games this season
SELECT
    player,
    team,
    opp,
    date,
    pts,
    fg,
    fga,
    fg_pct,
    threeP,
    ft,
    fta,
    gmsc,
    plus_minus,
    win,
    RANK() OVER (ORDER BY pts DESC) AS pts_rank_overall
FROM qualified_logs
WHERE pts >= 40
ORDER BY pts DESC;

-- 5. Team offensive efficiency
SELECT
    team,
    COUNT(*)                         AS total_game_logs,
    COUNT(DISTINCT player)           AS players_used,
    ROUND(AVG(pts), 1)               AS avg_pts_per_player_game,
    ROUND(SUM(pts) * 1.0 / COUNT(DISTINCT date), 1) AS estimated_team_pts_per_game,
    ROUND(AVG(fg_pct), 3)            AS avg_fg_pct,
    ROUND(AVG(threeP_pct), 3)        AS avg_3p_pct,
    ROUND(AVG(ts_pct), 3)            AS avg_ts_pct,
    ROUND(AVG(gmsc), 1)              AS avg_gmsc,
    ROUND(SUM(win)*100.0/COUNT(*),1) AS win_pct
FROM qualified_logs
GROUP BY team
ORDER BY avg_ts_pct DESC;

-- 6. Scoring distribution -- how many players hit each scoring tier per game
SELECT
    CASE
        WHEN pts >= 40 THEN '40+ Points'
        WHEN pts >= 30 THEN '30-39 Points'
        WHEN pts >= 20 THEN '20-29 Points'
        WHEN pts >= 10 THEN '10-19 Points'
        ELSE 'Under 10 Points'
    END AS scoring_tier,
    COUNT(*) AS game_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_games
FROM qualified_logs
GROUP BY scoring_tier
ORDER BY MIN(pts) DESC;
