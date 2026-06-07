import urllib.request
import json
from datetime import datetime
import uuid

def fetch_games(sport, league_path, league_name, days_ahead=28):
    from datetime import timedelta
    today = datetime.utcnow()
    end = today + timedelta(days=days_ahead)
    date_from = today.strftime("%Y%m%d")
    date_to = end.strftime("%Y%m%d")
    url = (f"https://site.api.espn.com/apis/site/v2/sports/{league_path}/scoreboard"
           f"?limit=100&dates={date_from}-{date_to}")
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

SPORT_DURATIONS = {
    "NFL": 210,
    "NBA": 150,
    "MLB": 180,
    "NHL": 150,
}

def fetch_cricket_games(league, days_ahead=28):
    from datetime import timedelta
    today = datetime.utcnow()
    end = today + timedelta(days=days_ahead)
    date_from = today.strftime("%Y-%m-%dT00:00:00Z")
    date_to = end.strftime("%Y-%m-%dT23:59:59Z")
    url = (f"https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/events"
           f"?limit=100&dates={today.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}")
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
    except Exception as e:
        print(f"  Error fetching cricket league {league}: {e}")
        print(f"  URL was: {url}")
        return []

    games = []
    for item in data.get("items", []):
        try:
            ref_url = item.get("$ref", "")
            with urllib.request.urlopen(ref_url) as r:
                event = json.loads(r.read())

            date_str = event.get("date", "")
            if not date_str:
                continue
            dt = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
            if dt < today or dt > end:
                continue

            readable_date = dt.strftime("%a %b %d")
            readable_time = dt.strftime("%Y-%m-%dT%H:%M:00Z")

            competitors = event.get("competitions", [{}])[0].get("competitors", [])
            if len(competitors) < 2:
                continue

            home = next((t for t in competitors if t.get("homeAway") == "home"), competitors[0])
            away = next((t for t in competitors if t.get("homeAway") == "away"), competitors[1])

            home_name = home.get("team", {}).get("displayName", "TBD")
            away_name = away.get("team", {}).get("displayName", "TBD")
            home_logo = home.get("team", {}).get("logo", "")
            away_logo = away.get("team", {}).get("logo", "")

            games.append({
                "date": readable_date,
                "time": readable_time,
                "home": home_name,
                "away": away_name,
                "home_logo": home_logo,
                "away_logo": away_logo,
                "status": event.get("status", {}).get("type", {}).get("description", "Scheduled")
            })
        except Exception:
            continue

    return games

def build_ical(games, sport_name):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Global Sports Calendar//EN",
        f"X-WR-CALNAME:{sport_name} Schedule",
        "X-WR-TIMEZONE:UTC",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    duration_minutes = SPORT_DURATIONS.get(sport_name, 120)

    for g in games:
        try:
            dt = datetime.strptime(g["time"], "%Y-%m-%dT%H:%M:00Z")
            dtstart = dt.strftime("%Y%m%dT%H%M%SZ")
            duration = f"PT{duration_minutes}M"
            summary = f"{g['away']} vs {g['home']}"
            uid = str(uuid.uuid4())
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART:{dtstart}",
                f"DURATION:{duration}",
                f"SUMMARY:{summary}",
                f"STATUS:{g['status'].upper()}",
                "END:VEVENT",
            ]
        except Exception:
            continue
    
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)

def build_html(nfl_games, nba_games, mlb_games, nhl_games, epl_games, cricket_games):
    def games_html(games):
        if not games:
            return "<p class='no-games'>No games scheduled.</p>"

        by_date = {}
        for g in games:
            by_date.setdefault(g['date'], []).append(g)

        html = ""
        for date, day_games in by_date.items():
            html += f"<div class='date-header'>{date}</div>"
            for g in day_games:
                html += f"""
                <div class='game-row'>
                    <div class='team-pill'>
                        <img class='team-logo' src='{g['away_logo']}' alt='{g['away']}'/>
                        <span class='team-name'>{g['away']}</span>
                    </div>
                    <span class='vs-text'>vs</span>
                    <div class='team-pill'>
                        <img class='team-logo' src='{g['home_logo']}' alt='{g['home']}'/>
                        <span class='team-name'>{g['home']}</span>
                    </div>
                    <span class='game-time' data-utc='{g['time']}'>{g['time']}</span>
                </div>"""
        return html

    updated = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

    nfl_html     = games_html(nfl_games)
    nba_html     = games_html(nba_games)
    mlb_html     = games_html(mlb_games)
    nhl_html     = games_html(nhl_games)
    epl_html     = games_html(epl_games)
    cricket_html = games_html(cricket_games)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PlyCal — Every game. Every timezone. Free.</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: #f7f8fc; color: #1a1f2e; min-height: 100vh; }}

        /* Header */
        header {{ background: #ffffff; border-bottom: 1px solid #eaecf4; padding: 0.9rem 1.5rem;
                  display: flex; align-items: center; justify-content: space-between; }}
        .logo-wrap {{ display: flex; align-items: center; gap: 9px; text-decoration: none; }}
        .logo-icon {{ width: 30px; height: 30px; background: #1a6ef5; border-radius: 7px;
                      display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
        .logo-icon svg {{ width: 16px; height: 16px; }}
        .logo-text {{ font-size: 20px; font-weight: 700; color: #111827; letter-spacing: -0.5px; }}
        .logo-text span {{ color: #1a6ef5; }}
        nav {{ display: flex; gap: 1.5rem; }}
        nav a {{ font-size: 13px; color: #9099b0; text-decoration: none; }}
        nav a.active {{ color: #1a6ef5; font-weight: 500; }}

        /* Tabs */
        .tabs-bar {{ background: #ffffff; border-bottom: 1px solid #eaecf4;
                     display: flex; padding: 0 1.5rem; overflow-x: auto; }}
        .tab {{ padding: 0.75rem 1.1rem; font-size: 13px; color: #9099b0; border: none;
                border-bottom: 2px solid transparent; background: none; cursor: pointer;
                white-space: nowrap; transition: color 0.15s; }}
        .tab.active {{ color: #1a6ef5; border-bottom-color: #1a6ef5; font-weight: 500; }}
        .tab:hover {{ color: #1a6ef5; }}

        /* Subscribe bar */
        .subscribe-bar {{ background: #f0f5ff; border-bottom: 1px solid #dde8fd;
                          padding: 0.6rem 1.5rem; display: flex; align-items: center;
                          gap: 0.75rem; flex-wrap: wrap; }}
        .subscribe-bar span {{ font-size: 12px; color: #6b7a9e; }}
        .sub-btn {{ font-size: 12px; color: #1a6ef5; border: 1px solid #c0d4fb;
                    border-radius: 20px; padding: 3px 12px; background: #ffffff;
                    cursor: pointer; text-decoration: none; transition: background 0.15s; }}
        .sub-btn:hover {{ background: #1a6ef5; color: #ffffff; }}

        /* Main content */
        main {{ max-width: 820px; margin: 1.25rem auto; padding: 0 1rem; }}
        .section {{ display: none; }}
        .section.active {{ display: block; }}
        .card {{ background: #ffffff; border: 0.5px solid #eaecf4; border-radius: 10px;
                 overflow: hidden; }}

        /* Date headers */
        .date-header {{ font-size: 11px; font-weight: 600; color: #9099b0;
                        letter-spacing: 1.5px; text-transform: uppercase;
                        padding: 0.75rem 1.25rem 0.4rem;
                        border-top: 0.5px solid #f0f2f8; }}
        .date-header:first-child {{ border-top: none; }}

        /* Game rows */
        .game-row {{ display: flex; align-items: center; gap: 8px;
                     padding: 0.6rem 1.25rem; border-bottom: 0.5px solid #f0f2f8; }}
        .game-row:last-child {{ border-bottom: none; }}
        .team-pill {{ display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }}
        .team-logo {{ width: 26px; height: 26px; object-fit: contain; flex-shrink: 0; }}
        .team-name {{ font-size: 13px; color: #1a1f2e; white-space: nowrap;
                      overflow: hidden; text-overflow: ellipsis; }}
        .vs-text {{ font-size: 11px; color: #c0c5d4; padding: 0 4px; flex-shrink: 0; }}
        .game-time {{ font-size: 12px; color: #1a6ef5; font-weight: 500;
                      margin-left: auto; white-space: nowrap; padding-left: 8px;
                      flex-shrink: 0; }}
        .no-games {{ padding: 2rem; text-align: center; color: #9099b0; font-size: 14px; }}

        /* Footer */
        footer {{ text-align: center; padding: 2rem 1rem; color: #b0b7c9; font-size: 12px; }}
        footer a {{ color: #9099b0; text-decoration: none; }}
    </style>
</head>
<body>

<header>
    <a class="logo-wrap" href="/">
        <div class="logo-icon">
            <svg viewBox="0 0 16 16" fill="none">
                <rect x="1" y="3" width="14" height="12" rx="2" stroke="white" stroke-width="1.5"/>
                <path d="M1 6.5h14" stroke="white" stroke-width="1.5"/>
                <path d="M5 1v3M11 1v3" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
                <circle cx="5.5" cy="10" r="1" fill="white"/>
                <circle cx="8" cy="10" r="1" fill="white"/>
                <circle cx="10.5" cy="10" r="1" fill="white"/>
            </svg>
        </div>
        <div class="logo-text">Ply<span>Cal</span></div>
    </a>
    <nav>
        <a href="/" class="active">Schedule</a>
        <a href="#subscribe">Subscribe</a>
    </nav>
</header>

<div class="tabs-bar">
    <button class="tab active" onclick="show('nfl', this)">🏈 NFL</button>
    <button class="tab" onclick="show('nba', this)">🏀 NBA</button>
    <button class="tab" onclick="show('mlb', this)">⚾ MLB</button>
    <button class="tab" onclick="show('nhl', this)">🏒 NHL</button>
    <button class="tab" onclick="show('epl', this)">⚽ Premier League</button>
    <button class="tab" onclick="show('cricket', this)">🏏 Cricket</button>
</div>

<div class="subscribe-bar" id="subscribe">
    <span>📅 Subscribe in your calendar app:</span>
    <a class="sub-btn" href="nfl.ics">🏈 NFL</a>
    <a class="sub-btn" href="nba.ics">🏀 NBA</a>
    <a class="sub-btn" href="mlb.ics">⚾ MLB</a>
    <a class="sub-btn" href="nhl.ics">🏒 NHL</a>
    <a class="sub-btn" href="epl.ics">⚽ EPL</a>
    <a class="sub-btn" href="cricket.ics">🏏 Cricket</a>
</div>

<main>
    <div id="nfl" class="section active"><div class="card">{nfl_html}</div></div>
    <div id="nba" class="section"><div class="card">{nba_html}</div></div>
    <div id="mlb" class="section"><div class="card">{mlb_html}</div></div>
    <div id="nhl" class="section"><div class="card">{nhl_html}</div></div>
    <div id="epl" class="section"><div class="card">{epl_html}</div></div>
    <div id="cricket" class="section"><div class="card">{cricket_html}</div></div>
</main>

<footer>
    <p>Updated: {updated} &nbsp;·&nbsp; Data from ESPN &nbsp;·&nbsp;
    <a href="#subscribe">Subscribe via iCal</a> &nbsp;·&nbsp; Free forever</p>
</footer>

<script>
    function show(id, el) {{
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        el.classList.add('active');
    }}

    function convertTimes() {{
        document.querySelectorAll('.game-time[data-utc]').forEach(el => {{
            const utc = el.getAttribute('data-utc');
            const local = new Date(utc);
            if (!isNaN(local)) {{
                el.textContent = local.toLocaleTimeString(undefined, {{
                    hour: '2-digit', minute: '2-digit'
                }});
            }}
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

    print("Fetching Premier League games...")
    epl = fetch_games("soccer", "soccer/eng.1", "Premier League")
    print(f"  Got {len(epl)} games")

    print("Fetching Cricket games...")
    cricket_leagues = [
        "icc.t20",
        "icc.odi",
        "icc.test",
        "ipl",
        "mlc",
    ]
    cricket = []
    for league in cricket_leagues:
        matches = fetch_cricket_games(league)
        cricket.extend(matches)
    cricket = list({f"{g['date']}{g['home']}{g['away']}": g for g in cricket}.values())
    cricket.sort(key=lambda x: x['time'])
    print(f"  Got {len(cricket)} cricket games total")

    html = build_html(nfl, nba, mlb, nhl, epl, cricket)
    with open("index.html", "w") as f:
        f.write(html)
    print("index.html written.")

    for sport_name, games in [("NFL", nfl), ("NBA", nba), ("MLB", mlb), ("NHL", nhl), ("EPL", epl), ("Cricket", cricket)]:
        ical = build_ical(games, sport_name)
        filename = f"{sport_name.lower()}.ics"
        with open(filename, "w") as f:
            f.write(ical)
        print(f"{filename} written.")

    print("Done!")
        
