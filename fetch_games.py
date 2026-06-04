import urllib.request
import json
from datetime import datetime

def fetch_games(sport, league_path, league_name):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{league_path}/scoreboard?limit=100"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
    except Exception as e:
        print(f"Error fetching {league_name}: {e}")
        return []

    games = []
    for event in data.get("events", []):
        try:
            date_str = event["date"]
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%MZ")
            readable_date = dt.strftime("%a %b %d")
            readable_time = dt.strftime("%Y-%m-%dT%H:%M:00Z")

            competitors = event["competitions"][0]["competitors"]
            home = next(t for t in competitors if t["homeAway"] == "home")
            away = next(t for t in competitors if t["homeAway"] == "away")

            games.append({
                "date": readable_date,
                "time": readable_time,
                "home": home["team"]["displayName"],
                "away": away["team"]["displayName"],
                "home_logo": home["team"].get("logo", ""),
                "away_logo": away["team"].get("logo", ""),
                "status": event["status"]["type"]["description"]
            })
        except Exception:
            continue

    return games

def build_html(nfl_games, nba_games, mlb_games, nhl_games):
    def games_html(games):
        if not games:
            return "<p class='no-games'>No games found.</p>"
        rows = ""
        for g in games:
            rows += f"""
            <tr>
                <td>{g['date']}</td>
                <td data-utc="{g['time']}">{g['time']}</td>
                <td class='team'><img src='{g['away_logo']}' class='logo'/>{g['away']}</td>
                <td class='vs'>vs</td>
                <td class='team'><img src='{g['home_logo']}' class='logo'/>{g['home']}</td>
                <td class='status'>{g['status']}</td>
            </tr>"""
        return f"<table><thead><tr><th>Date</th><th>Time (Local)</th><th>Away</th><th></th><th>Home</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>"

    updated = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Global Sports Calendar</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Georgia, serif; background: #0f1117; color: #e8e8e8; min-height: 100vh; }}
        header {{ background: #1a1d27; border-bottom: 3px solid #f0a500; padding: 2rem; text-align: center; }}
        header h1 {{ font-size: 2.2rem; color: #f0a500; letter-spacing: 2px; text-transform: uppercase; }}
        header p {{ color: #888; margin-top: 0.4rem; font-size: 0.9rem; }}
        .tabs {{ display: flex; justify-content: center; gap: 1rem; padding: 1.5rem; }}
        .tab {{ padding: 0.6rem 2rem; background: #1a1d27; border: 2px solid #333; color: #aaa;
                cursor: pointer; font-size: 1rem; border-radius: 4px; transition: all 0.2s; }}
        .tab.active {{ border-color: #f0a500; color: #f0a500; background: #22263a; }}
        .section {{ display: none; padding: 0 2rem 3rem; max-width: 1000px; margin: 0 auto; }}
        .section.active {{ display: block; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th {{ background: #1a1d27; color: #f0a500; padding: 0.75rem 1rem; text-align: left;
              font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; }}
        td {{ padding: 0.7rem 1rem; border-bottom: 1px solid #222; font-size: 0.95rem; }}
        tr:hover td {{ background: #1a1d27; }}
        td.vs {{ color: #555; font-size: 0.8rem; }}
        td.status {{ color: #888; font-size: 0.85rem; font-style: italic; }}
        .no-games {{ color: #666; padding: 2rem; text-align: center; }}
        .logo {{ width: 28px; height: 28px; object-fit: contain; margin-right: 8px; vertical-align: middle; }}
        td.team {{ display: flex; align-items: center; }}
        footer {{ text-align: center; padding: 2rem; color: #444; font-size: 0.8rem; border-top: 1px solid #222; }}
    </style>
</head>
<body>
    <header>
        <h1>⚡ Global Sports Calendar</h1>
        <p>Updated: {updated}</p>
    </header>

    <div class="tabs">
        <button class="tab active" onclick="show('nfl', this)">🏈 NFL</button>
        <button class="tab" onclick="show('nba', this)">🏀 NBA</button>
        <button class="tab" onclick="show('mlb', this)">⚾ MLB</button>
        <button class="tab" onclick="show('nhl', this)">🏒 NHL</button>
    </div>

    <div id="nfl" class="section active">{games_html(nfl_games)}</div>
    <div id="nba" class="section">{games_html(nba_games)}</div>
    <div id="mlb" class="section">{games_html(mlb_games)}</div>
    <div id="nhl" class="section">{games_html(nhl_games)}</div>

    <footer>Data from ESPN · Refreshes daily · Free &amp; open</footer>

    <script>
        function show(id, el) {{
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            el.classList.add('active');
        }}

        function convertTimes() {{
            document.querySelectorAll('td[data-utc]').forEach(td => {{
                const utc = td.getAttribute('data-utc');
                const local = new Date(utc);
                const dateStr = local.toLocaleDateString(undefined, {{ weekday: 'short', month: 'short', day: 'numeric' }});
                const timeStr = local.toLocaleTimeString(undefined, {{ hour: '2-digit', minute: '2-digit' }});
                td.textContent = timeStr;
                // Also update the date cell
                const row = td.closest('tr');
                if (row) row.cells[0].textContent = dateStr;
            }});
        }}

        convertTimes();
    </script>
</body>
</html>"""

if __name__ == "__main__":
    print("Fetching NFL games...")
    nfl = fetch_games("football", "football/nfl", "NFL")
    print(f"  Got {len(nfl)} games")

    print("Fetching NBA games...")
    nba = fetch_games("basketball", "basketball/nba", "NBA")
    print(f"  Got {len(nba)} games")

    print("Fetching MLB games...")
    mlb = fetch_games("baseball", "baseball/mlb", "MLB")
    print(f"  Got {len(mlb)} games")

    print("Fetching NHL games...")
    nhl = fetch_games("hockey", "hockey/nhl", "NHL")
    print(f"  Got {len(nhl)} games")

    html = build_html(nfl, nba, mlb, nhl)
    with open("index.html", "w") as f:
        f.write(html)
    print("Done! index.html written.")
        
