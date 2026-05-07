-- ============================================================
-- NBA 2024-25 Season Analytics
-- Script 04: Business Insights & Recommendations
-- Author: Jimmy Le-Nguyen
-- ============================================================

-- INSIGHT 1: Which players provide the best efficiency vs volume balance?
-- Business question: Who should a team target in free agency for best ROI?
SELECT
    player,
    team,
    games_played,
    avg_pts,
    avg_ts_pct,
    avg_gmsc,
    avg_plus_minus,
    CASE
        WHEN avg_pts >= 20 AND avg_ts_pct >= 0.580 THEN 'Elite (High Volume + High Efficiency)'
        WHEN avg_pts >= 20 AND avg_ts_pct < 0.580  THEN 'Volume Scorer (Lower Efficiency)'
        WHEN avg_pts < 20  AND avg_ts_pct >= 0.580 THEN 'Efficient Role Player'
        ELSE 'Average'
    END AS player_archetype
FROM player_season_averages
WHERE games_played >= 41
ORDER BY avg_gmsc DESC
LIMIT 30;

-- INSIGHT 2: Rest impact on performance league-wide
-- Business question: How much does schedule congestion hurt player output?
WITH rest_analysis AS (
    SELECT
        player,
        date,
        pts,
        gmsc,
        ts_pct,
        JULIANDAY(date) - JULIANDAY(
            LAG(date) OVER (PARTITION BY player ORDER BY date)
        ) AS days_rest
    FROM qualified_logs
)
SELECT
    CASE
        WHEN days_rest = 1 THEN 'Back to Back'
        WHEN days_rest = 2 THEN '1 Day Rest'
        WHEN days_rest = 3 THEN '2 Days Rest'
        ELSE '3+ Days Rest'
    END AS rest_category,
    COUNT(*)               AS games,
    ROUND(AVG(pts), 2)     AS avg_pts,
    ROUND(AVG(gmsc), 2)    AS avg_gmsc,
    ROUND(AVG(ts_pct), 3)  AS avg_ts_pct,
    -- Calculate performance drop vs 3+ days rest baseline
    ROUND(AVG(pts) - (
        SELECT AVG(pts) FROM rest_analysis WHERE days_rest >= 4
    ), 2)                  AS pts_vs_rested_baseline
FROM rest_analysis
WHERE days_rest IS NOT NULL
GROUP BY rest_category
ORDER BY MIN(days_rest);

-- INSIGHT 3: Top performers by position
-- Business question: Who are the best players at each position?
WITH position_rankings AS (
    SELECT
        psa.player,
        psa.team,
        psa.games_played,
        psa.avg_pts,
        psa.avg_reb,
        psa.avg_ast,
        psa.avg_gmsc,
        psa.avg_ts_pct,
        psa.avg_plus_minus,
        -- Infer position from stats profile
        CASE
            WHEN psa.avg_ast >= 6.0 AND psa.avg_reb < 6.0 THEN 'Guard'
            WHEN psa.avg_reb >= 8.0 AND psa.avg_ast < 4.0 THEN 'Big Man'
            WHEN psa.avg_ast >= 4.0 AND psa.avg_reb >= 5.0 THEN 'Forward/Wing'
            ELSE 'Role Player'
        END AS position_type,
        RANK() OVER (
            PARTITION BY
                CASE
                    WHEN psa.avg_ast >= 6.0 AND psa.avg_reb < 6.0 THEN 'Guard'
                    WHEN psa.avg_reb >= 8.0 AND psa.avg_ast < 4.0 THEN 'Big Man'
                    WHEN psa.avg_ast >= 4.0 AND psa.avg_reb >= 5.0 THEN 'Forward/Wing'
                    ELSE 'Role Player'
                END
            ORDER BY psa.avg_gmsc DESC
        ) AS position_rank
    FROM player_season_averages psa
    WHERE games_played >= 41
)
SELECT *
FROM position_rankings
WHERE position_rank <= 5
ORDER BY position_type, position_rank;

-- INSIGHT 4: Hot streak analysis
-- Which players had the longest stretches of elite performance?
WITH streaks AS (
    SELECT
        player,
        date,
        pts,
        gmsc,
        CASE WHEN gmsc >= 20.0 THEN 1 ELSE 0 END AS is_elite_game,
        ROW_NUMBER() OVER (PARTITION BY player ORDER BY date) -
        ROW_NUMBER() OVER (PARTITION BY player, CASE WHEN gmsc >= 20.0 THEN 1 ELSE 0 END ORDER BY date)
        AS streak_group
    FROM qualified_logs
),
streak_lengths AS (
    SELECT
        player,
        streak_group,
        SUM(is_elite_game) AS consecutive_elite_games,
        MIN(date)          AS streak_start,
        MAX(date)          AS streak_end
    FROM streaks
    WHERE is_elite_game = 1
    GROUP BY player, streak_group
)
SELECT
    player,
    consecutive_elite_games,
    streak_start,
    streak_end
FROM streak_lengths
WHERE consecutive_elite_games >= 5
ORDER BY consecutive_elite_games DESC
LIMIT 20;

-- INSIGHT 5: Opponent difficulty -- who dominated regardless of opposition?
SELECT
    player,
    team,
    opp,
    COUNT(*)               AS games_vs_opp,
    ROUND(AVG(pts), 1)     AS avg_pts,
    ROUND(AVG(gmsc), 1)    AS avg_gmsc,
    ROUND(AVG(plus_minus),1) AS avg_plus_minus,
    SUM(win)               AS wins
FROM qualified_logs
WHERE player IN (
    SELECT player FROM player_season_averages
    ORDER BY avg_gmsc DESC LIMIT 5
)
GROUP BY player, opp
HAVING games_vs_opp >= 2
ORDER BY player, avg_gmsc DESC;
