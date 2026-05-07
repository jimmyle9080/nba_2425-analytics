# NBA 2024-25 Season Analytics | SQL + Python + Power BI

**Author:** Jimmy Le-Nguyen  
**Tools:** Python, SQLite, Matplotlib, Seaborn, Power BI  
**Dataset:** NBA Daily Leaders 2024-25 — 28,265 game logs, 569 players, 30 teams

---

## Quick Start (Run in VS Code)

### 1. Clone the repo
```bash
git clone https://github.com/jimmyle9080/nba-analytics-2024-25.git
cd nba-analytics-2024-25
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the full pipeline
```bash
python main.py
```

That's it. Running `main.py` will:
- Load and clean the raw CSV into a SQLite database
- Run all SQL analyses
- Export CSVs to `exports/` for Power BI
- Generate 6 charts saved to `charts/`

---

## Project Structure

```
nba-analytics-2024-25/
├── main.py                              # Run this -- does everything
├── requirements.txt                     # pip install -r requirements.txt
├── README.md
├── data/
│   └── nba_dailyleaders_full_24_25.csv  # Raw dataset (28,265 game logs)
├── sql/
│   ├── 01_data_cleaning.sql             # Data quality checks
│   ├── 02_window_functions.sql          # RANK, LAG, rolling averages
│   ├── 03_player_analysis.sql           # MVP model, clutch, consistency
│   └── 04_business_insights.sql         # Strategic insights
├── python/
│   ├── load_data.py                     # Clean CSV → SQLite
│   ├── analysis.py                      # Run queries → export CSVs
│   └── visualizations.py               # Generate 6 charts
├── exports/                             # Power BI CSVs (auto-generated)
└── charts/                             # PNG charts (auto-generated)
```

---

## Key Findings

**MVP Race 2024-25 (Composite Score Model):**
| Rank | Player | Team | Score |
|------|--------|------|-------|
| 1 | Shai Gilgeous-Alexander | OKC | 31.84 |
| 2 | Nikola Jokic | DEN | 29.88 |
| 3 | Giannis Antetokounmpo | MIL | 28.48 |
| 4 | Jayson Tatum | BOS | 27.31 |
| 5 | Donovan Mitchell | CLE | 26.20 |

**Biggest Single Game Performances:**
- Nikola Jokic: 61 pts vs MIN — Game Score: 52.7
- De'Aaron Fox: 60 pts vs MIN — Game Score: 47.0
- Giannis Antetokounmpo: 59 pts vs DET — Game Score: 54.2

**Rest Impact:**
- Back to back games reduce win rate by 7.5% vs 2 days rest
- Players average 2+ fewer points on zero rest nights

---

## SQL Concepts Demonstrated

| Concept | Scripts |
|---------|---------|
| Views | 01, 02 |
| RANK / DENSE_RANK / NTILE / PERCENT_RANK | 02, 03 |
| LAG / LEAD | 02, 04 |
| Rolling averages (ROWS BETWEEN) | 02 |
| Cumulative sums | 02 |
| CTEs | 02, 04 |
| CASE statements | 01, 04 |
| Subqueries | 02, 03 |
| JULIANDAY date math | 02, 04 |
| Aggregations / HAVING | 01, 03 |

---

## Power BI Dashboard

Connect Power BI to the CSVs in `exports/` after running `main.py`:

| File | Dashboard Page |
|------|---------------|
| season_leaderboard.csv | Season Stats Table |
| mvp_scores.csv | MVP Race |
| rolling_averages.csv | Hot Streak Tracker |
| rest_impact.csv | Rest Impact Analysis |
| monthly_trends.csv | Monthly Performance |
| team_efficiency.csv | Team Rankings |
| big_games.csv | 40+ Point Games |
| game_logs_clean.csv | Full Game Log Explorer |
