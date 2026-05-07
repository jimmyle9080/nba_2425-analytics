"""
NBA 2024-25 Season Analytics
Author: Jimmy Le-Nguyen

How to run:
  1. Open this folder in VS Code
  2. pip install -r requirements.txt  (first time only)
  3. Run main.py
"""

import os
import sys
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

ROOT       = os.path.dirname(os.path.abspath(__file__))
CSV_PATH   = os.path.join(ROOT, "data", "nba_dailyleaders_full_24_25.csv")
DB_PATH    = os.path.join(ROOT, "data", "nba_2425.db")
EXPORT_DIR = os.path.join(ROOT, "exports")
CHART_DIR  = os.path.join(ROOT, "charts")
SQL_DIR    = os.path.join(ROOT, "sql")

os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

BLUE   = "#1d428a"
RED    = "#c8102e"
GOLD   = "#ffc72c"
GRAY   = "#888888"
GREEN  = "#2ecc71"
PURPLE = "#9b59b6"

sns.set_theme(style="whitegrid")


def load_data():
    print("Loading and cleaning data...")

    if not os.path.exists(CSV_PATH):
        print(f"CSV not found at {CSV_PATH}")
        print("Make sure nba_dailyleaders_full_24_25.csv is in the data/ folder.")
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)
    df = df.drop(columns=["Unnamed: 3"])

    df.columns = [
        "player", "team", "opp", "result", "mp",
        "fg", "fga", "fg_pct", "threeP", "threePA", "threeP_pct",
        "ft", "fta", "ft_pct", "orb", "drb", "trb",
        "ast", "stl", "blk", "tov", "pf", "pts",
        "plus_minus", "gmsc", "date"
    ]

    def parse_minutes(mp_str):
        try:
            m, s = str(mp_str).split(":")
            return round(int(m) + int(s) / 60, 2)
        except:
            return None

    df["mp_decimal"] = df["mp"].apply(parse_minutes)
    df["win"] = df["result"].apply(lambda x: 1 if str(x).startswith("W") else 0)

    df["date"]      = pd.to_datetime(df["date"])
    df["month"]     = df["date"].dt.strftime("%B")
    df["month_num"] = df["date"].dt.month

    for col in ["fg_pct", "threeP_pct", "ft_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["plus_minus"] = pd.to_numeric(df["plus_minus"], errors="coerce").fillna(0)

    df = df.sort_values(["player", "date"])
    df["game_number"] = df.groupby("player").cumcount() + 1

    # true shooting %
    df["ts_pct"] = df.apply(
        lambda r: round(r["pts"] / (2 * (r["fga"] + 0.44 * r["fta"])), 3)
        if (r["fga"] + 0.44 * r["fta"]) > 0 else None,
        axis=1
    )

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("game_logs", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

    print(f"  {len(df):,} records loaded")
    print(f"  {df['player'].nunique()} players across {df['team'].nunique()} teams")
    print(f"  {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  Saved to data/nba_2425.db")


def run_analysis():
    print("\nRunning SQL analysis and exporting CSVs...")

    conn = sqlite3.connect(DB_PATH)

    conn.executescript("""
        DROP VIEW IF EXISTS qualified_logs;
        CREATE VIEW qualified_logs AS
        SELECT * FROM game_logs
        WHERE mp_decimal >= 10.0 AND fga > 0;

        DROP VIEW IF EXISTS player_season_averages;
        CREATE VIEW player_season_averages AS
        SELECT
            player, team,
            COUNT(*)                          AS games_played,
            ROUND(AVG(mp_decimal), 1)         AS avg_minutes,
            ROUND(AVG(pts), 1)                AS avg_pts,
            ROUND(AVG(trb), 1)                AS avg_reb,
            ROUND(AVG(ast), 1)                AS avg_ast,
            ROUND(AVG(stl), 1)                AS avg_stl,
            ROUND(AVG(blk), 1)                AS avg_blk,
            ROUND(AVG(tov), 1)                AS avg_tov,
            ROUND(AVG(fg_pct), 3)             AS avg_fg_pct,
            ROUND(AVG(threeP_pct), 3)         AS avg_3p_pct,
            ROUND(AVG(ft_pct), 3)             AS avg_ft_pct,
            ROUND(AVG(ts_pct), 3)             AS avg_ts_pct,
            ROUND(AVG(gmsc), 1)               AS avg_gmsc,
            ROUND(AVG(plus_minus), 1)         AS avg_plus_minus,
            SUM(win)                          AS wins,
            ROUND(100.0*SUM(win)/COUNT(*), 1) AS win_pct
        FROM qualified_logs
        GROUP BY player, team;
    """)
    conn.commit()

    def q(sql):
        return pd.read_sql_query(sql, conn)

    exports = {

        "season_leaderboard": q("""
            SELECT player, team, games_played,
                avg_pts, avg_reb, avg_ast, avg_stl, avg_blk, avg_tov,
                avg_fg_pct, avg_3p_pct, avg_ts_pct,
                avg_gmsc, avg_plus_minus, win_pct,
                RANK() OVER (ORDER BY avg_pts DESC)    AS pts_rank,
                RANK() OVER (ORDER BY avg_gmsc DESC)   AS gmsc_rank,
                RANK() OVER (ORDER BY avg_ts_pct DESC) AS ts_rank
            FROM player_season_averages
            WHERE games_played >= 41
            ORDER BY avg_pts DESC
        """),

        # composite MVP score: Pts 30% | GmSc 25% | TS% 20% | +/- 15% | Win% 10%
        "mvp_scores": q("""
            SELECT player, team, games_played,
                avg_pts, avg_reb, avg_ast, avg_ts_pct,
                avg_gmsc, avg_plus_minus, win_pct,
                ROUND(
                    (avg_pts * 0.30) + (avg_gmsc * 0.25) +
                    (avg_ts_pct * 50 * 0.20) +
                    (avg_plus_minus * 0.15) + (win_pct * 0.10)
                , 2) AS mvp_composite_score,
                RANK() OVER (ORDER BY
                    (avg_pts*0.30)+(avg_gmsc*0.25)+
                    (avg_ts_pct*50*0.20)+(avg_plus_minus*0.15)+(win_pct*0.10)
                DESC) AS mvp_rank
            FROM player_season_averages
            WHERE games_played >= 41
            ORDER BY mvp_composite_score DESC
        """),

        "game_logs_clean": q("""
            SELECT player, team, opp, date, month,
                mp_decimal, pts, trb, ast, stl, blk, tov,
                fg, fga, fg_pct, threeP, threePA, threeP_pct,
                ft, fta, ft_pct, ts_pct,
                gmsc, plus_minus, win, game_number
            FROM qualified_logs
            ORDER BY date, player
        """),

        # rolling 10-game window
        "rolling_averages": q("""
            SELECT player, date, game_number, pts, gmsc, ts_pct,
                AVG(pts) OVER (
                    PARTITION BY player ORDER BY date
                    ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                ) AS rolling_10g_pts,
                AVG(gmsc) OVER (
                    PARTITION BY player ORDER BY date
                    ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                ) AS rolling_10g_gmsc,
                SUM(pts) OVER (
                    PARTITION BY player ORDER BY date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS cumulative_pts
            FROM qualified_logs
            WHERE player IN (
                SELECT player FROM player_season_averages
                WHERE games_played >= 41
                ORDER BY avg_pts DESC LIMIT 15
            )
            ORDER BY player, date
        """),

        # LAG + JULIANDAY to get days between games
        "rest_impact": q("""
            WITH rest_data AS (
                SELECT player, date, pts, gmsc, ts_pct, win,
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
                COUNT(*) AS games,
                ROUND(AVG(pts), 2)     AS avg_pts,
                ROUND(AVG(gmsc), 2)    AS avg_gmsc,
                ROUND(AVG(ts_pct), 3)  AS avg_ts_pct,
                ROUND(100.0*SUM(win)/COUNT(*), 1) AS win_pct
            FROM rest_data
            WHERE days_rest IS NOT NULL
            GROUP BY rest_category
            ORDER BY MIN(days_rest)
        """),

        "monthly_trends": q("""
            SELECT player, month, month_num,
                COUNT(*) AS games,
                ROUND(AVG(pts), 1)        AS avg_pts,
                ROUND(AVG(gmsc), 1)       AS avg_gmsc,
                ROUND(AVG(ts_pct), 3)     AS avg_ts_pct,
                ROUND(AVG(plus_minus), 1) AS avg_plus_minus
            FROM qualified_logs
            WHERE player IN (
                SELECT player FROM player_season_averages
                WHERE games_played >= 41
                ORDER BY avg_gmsc DESC LIMIT 10
            )
            GROUP BY player, month, month_num
            ORDER BY player, month_num
        """),

        "team_efficiency": q("""
            SELECT team,
                COUNT(DISTINCT player)            AS players_used,
                COUNT(*)                          AS game_logs,
                ROUND(AVG(pts), 1)                AS avg_pts_per_log,
                ROUND(AVG(fg_pct), 3)             AS avg_fg_pct,
                ROUND(AVG(threeP_pct), 3)         AS avg_3p_pct,
                ROUND(AVG(ts_pct), 3)             AS avg_ts_pct,
                ROUND(AVG(gmsc), 1)               AS avg_gmsc,
                ROUND(100.0*SUM(win)/COUNT(*), 1) AS win_pct
            FROM qualified_logs
            GROUP BY team
            ORDER BY avg_ts_pct DESC
        """),

        "big_games": q("""
            SELECT player, team, opp, date, pts, trb, ast,
                fg, fga, fg_pct, threeP, ft, fta,
                gmsc, plus_minus, win,
                RANK() OVER (ORDER BY pts DESC) AS pts_rank
            FROM qualified_logs
            WHERE pts >= 40
            ORDER BY pts DESC
        """),
    }

    conn.close()

    for name, df in exports.items():
        path = os.path.join(EXPORT_DIR, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"  exports/{name}.csv ({len(df):,} rows)")

    print(f"\n  {len(exports)} CSVs saved to exports/ -- ready for Power BI")


def save_chart(fig, filename):
    path = os.path.join(CHART_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  charts/{filename}")


def generate_charts():
    print("\nGenerating charts...")

    conn = sqlite3.connect(DB_PATH)

    def q(sql):
        return pd.read_sql_query(sql, conn)

    df = q("""
        SELECT player, team, avg_pts
        FROM player_season_averages
        WHERE games_played >= 41
        ORDER BY avg_pts DESC LIMIT 15
    """).sort_values("avg_pts")

    labels = [f"{r.player} ({r.team})" for _, r in df.iterrows()]
    colors = [RED if i == len(df)-1 else BLUE for i in range(len(df))]
    fig, ax = plt.subplots(figsize=(11, 7))
    bars = ax.barh(labels, df["avg_pts"], color=colors, edgecolor="white")
    for bar, val in zip(bars, df["avg_pts"]):
        ax.text(val+0.1, bar.get_y()+bar.get_height()/2,
                f"{val:.1f}", va="center", fontsize=9, fontweight="bold")
    ax.set_xlabel("Points Per Game", fontsize=11)
    ax.set_title("NBA 2024-25 — Top 15 Scorers", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlim(0, df["avg_pts"].max()+3)
    plt.tight_layout()
    save_chart(fig, "01_top_scorers.png")

    df = q("""
        SELECT player, team,
            ROUND((avg_pts*0.30)+(avg_gmsc*0.25)+(avg_ts_pct*50*0.20)+
                  (avg_plus_minus*0.15)+(win_pct*0.10), 2) AS mvp_score
        FROM player_season_averages
        WHERE games_played >= 41
        ORDER BY mvp_score DESC LIMIT 10
    """).sort_values("mvp_score")

    labels = [f"{r.player} ({r.team})" for _, r in df.iterrows()]
    colors = [RED if i == len(df)-1 else BLUE for i in range(len(df))]
    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.barh(labels, df["mvp_score"], color=colors, edgecolor="white")
    for bar, val in zip(bars, df["mvp_score"]):
        ax.text(val+0.05, bar.get_y()+bar.get_height()/2,
                f"{val:.2f}", va="center", fontsize=9, fontweight="bold")
    ax.set_xlabel("MVP Composite Score", fontsize=11)
    ax.set_title("NBA 2024-25 MVP Race — Composite Score Model\n"
                 "(Pts 30% | GmSc 25% | TS% 20% | +/- 15% | Win% 10%)",
                 fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    save_chart(fig, "02_mvp_composite.png")

    df = q("""
        WITH rd AS (
            SELECT player, date, pts, gmsc, win,
                JULIANDAY(date)-JULIANDAY(LAG(date) OVER (PARTITION BY player ORDER BY date)) AS dr
            FROM qualified_logs
        )
        SELECT CASE WHEN dr=1 THEN 'Back to Back' WHEN dr=2 THEN '1 Day Rest'
                    WHEN dr=3 THEN '2 Days Rest' ELSE '3+ Days Rest' END AS cat,
               ROUND(AVG(pts),2) AS avg_pts,
               ROUND(AVG(gmsc),2) AS avg_gmsc
        FROM rd WHERE dr IS NOT NULL
        GROUP BY cat ORDER BY MIN(dr)
    """)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Rest Impact on Performance — NBA 2024-25", fontsize=13, fontweight="bold")
    bar_colors = [RED, GOLD, BLUE, GREEN]
    for ax, col, label in zip(axes, ["avg_pts", "avg_gmsc"],
                               ["Avg Points Per Game", "Avg Game Score"]):
        bars = ax.bar(range(len(df)), df[col], color=bar_colors, edgecolor="white")
        ax.set_xticks(range(len(df)))
        ax.set_xticklabels(df["cat"], rotation=15, ha="right", fontsize=9)
        for bar, val in zip(bars, df[col]):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                    f"{val:.1f}", ha="center", fontsize=10, fontweight="bold")
        ax.set_title(label)
        ax.set_ylabel(label)
    plt.tight_layout()
    save_chart(fig, "03_rest_impact.png")

    df = q("""
        SELECT player, month, month_num, ROUND(AVG(pts),1) AS avg_pts
        FROM qualified_logs
        WHERE player IN (
            SELECT player FROM player_season_averages
            WHERE games_played >= 41
            ORDER BY avg_pts DESC LIMIT 6
        )
        GROUP BY player, month, month_num
        ORDER BY player, month_num
    """)
    fig, ax = plt.subplots(figsize=(13, 6))
    palette = [BLUE, RED, GOLD, GREEN, PURPLE, "#e67e22"]
    for i, (player, grp) in enumerate(df.groupby("player")):
        grp = grp.sort_values("month_num")
        ax.plot(grp["month"], grp["avg_pts"], marker="o", linewidth=2.5,
                label=player, color=palette[i % len(palette)])
    ax.set_title("Monthly Scoring Trends — Top 6 Scorers 2024-25",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Avg Points Per Game")
    ax.legend(loc="upper left", fontsize=9)
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()
    save_chart(fig, "04_monthly_trends.png")

    df = q("""
        SELECT player, team, avg_pts, avg_ts_pct, avg_gmsc
        FROM player_season_averages
        WHERE games_played >= 41 AND avg_ts_pct IS NOT NULL
    """)
    fig, ax = plt.subplots(figsize=(12, 8))
    scatter = ax.scatter(df["avg_pts"], df["avg_ts_pct"],
                         c=df["avg_gmsc"], cmap="RdYlGn",
                         s=80, alpha=0.75, edgecolors="white", linewidth=0.5)
    for _, row in df.nlargest(12, "avg_gmsc").iterrows():
        ax.annotate(row["player"].split(" ")[-1],
                    (row["avg_pts"], row["avg_ts_pct"]),
                    fontsize=7.5, ha="left", va="bottom",
                    xytext=(3, 3), textcoords="offset points")
    ax.axhline(df["avg_ts_pct"].median(), color=GRAY,
               linestyle="--", alpha=0.5, label="Median TS%")
    ax.axvline(df["avg_pts"].median(), color=GRAY,
               linestyle=":", alpha=0.5, label="Median PPG")
    plt.colorbar(scatter, ax=ax, label="Avg Game Score")
    ax.set_xlabel("Avg Points Per Game", fontsize=11)
    ax.set_ylabel("Avg True Shooting %", fontsize=11)
    ax.set_title("Scoring Volume vs Efficiency — NBA 2024-25\n(Color = Game Score)",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    plt.tight_layout()
    save_chart(fig, "05_efficiency_scatter.png")

    df = q("""
        SELECT team, ROUND(AVG(ts_pct),3) AS avg_ts_pct
        FROM qualified_logs
        GROUP BY team ORDER BY avg_ts_pct DESC
    """)
    colors = [RED if i < 5 else (GOLD if i >= len(df)-5 else BLUE)
              for i in range(len(df))]
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(df["team"], df["avg_ts_pct"], color=colors, edgecolor="white")
    ax.set_title("Team True Shooting % — NBA 2024-25", fontsize=13, fontweight="bold")
    ax.set_xlabel("Team")
    ax.set_ylabel("Avg True Shooting %")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(handles=[
        mpatches.Patch(color=RED,  label="Top 5"),
        mpatches.Patch(color=BLUE, label="Other Teams"),
        mpatches.Patch(color=GOLD, label="Bottom 5"),
    ], fontsize=9)
    plt.tight_layout()
    save_chart(fig, "06_team_efficiency.png")

    conn.close()
    print("  6 charts saved to charts/")


if __name__ == "__main__":
    print("NBA 2024-25 Season Analytics")
    print("Author: Jimmy Le-Nguyen\n")

    load_data()
    run_analysis()
    generate_charts()

    print("\nDone!")
    print("  exports/  ->  Power BI")
    print("  charts/   ->  GitHub README")