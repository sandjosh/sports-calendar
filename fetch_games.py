import urllib.request
import json
from datetime import datetime
import uuid
import os

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

def fetch_cricket_games(days_ahead=28):
    api_key = os.environ.get("CRICKET_API_KEY", "")
    if not api_key:
        print("  No CRICKET_API_KEY found, skipping cricket")
        return []
    from datetime import timedelta
    today = datetime.utcnow()
    end = today + timedelta(days=days_ahead)
    games = []
    for offset in [0, 25, 50]:
        url = f"https://api.cricapi.com/v1/matches?apikey={api_key}&offset={offset}&per_page=25"
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read())
        except Exception as e:
            print(f"  Error fetching cricket offset {offset}: {e}")
            continue
        if data.get("status") != "success":
            print(f"  Cricket API error at offset {offset}: {data.get('status')}")
            continue
        for match in data.get("data", []):
            try:
                date_str = match.get("dateTimeGMT", "")
                if not date_str:
                    continue
                dt = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
                if dt < today or dt > end:
                    continue
                teams = match.get("teams", [])
                if len(teams) < 2:
                    continue
                match_type = match.get("matchType", "").upper()
                series = match.get("series", "")
                games.append({
                    "date": dt.strftime("%a %b %d"),
                    "time": dt.strftime("%Y-%m-%dT%H:%M:00Z"),
                    "home": teams[1],
                    "away": teams[0],
                    "home_logo": "",
                    "away_logo": "",
                    "status": f"{match_type} · {series}" if series else match_type
                })
            except Exception:
                continue
    return games

def fetch_cricket_from_ics(folder="cricket_ics", days_ahead=90):
    FLAG_CODES = {
        "India": "in", "England": "gb", "Australia": "au",
        "Pakistan": "pk", "South Africa": "za", "New Zealand": "nz",
        "West Indies": "wi", "Sri Lanka": "lk", "Bangladesh": "bd",
        "Zimbabwe": "zw", "Afghanistan": "af", "Ireland": "ie",
        "Scotland": "gb-sct", "Netherlands": "nl", "Canada": "ca",
        "United States Of America": "us", "USA": "us", "Kenya": "ke",
        "Namibia": "na", "Uganda": "ug", "Nepal": "np",
        "Oman": "om", "UAE": "ae", "Papua New Guinea": "pg",
        "Jersey": "je", "Guernsey": "gg", "Nigeria": "ng",
        "Hong Kong": "hk", "Singapore": "sg", "Malaysia": "my",
        "India Women": "in", "England Women": "gb", "Australia Women": "au",
        "Pakistan Women": "pk", "South Africa Women": "za",
        "New Zealand Women": "nz", "West Indies Women": "wi",
        "Sri Lanka Women": "lk", "Bangladesh Women": "bd",
        "Ireland Women": "ie", "Scotland Women": "gb-sct",
        "Netherlands Women": "nl",
    }
    from datetime import timedelta
    try:
        from icalendar import Calendar
    except ImportError:
        print("  icalendar library not available")
        return []

    today = datetime.utcnow()
    end = today + timedelta(days=days_ahead)
    games = []

    import os as _os
    ics_files = [f for f in _os.listdir(folder) if f.endswith(".ics")]
    print(f"  Found {len(ics_files)} .ics files in {folder}/")

    for filename in ics_files:
        filepath = _os.path.join(folder, filename)
        try:
            with open(filepath, "rb") as f:
                cal = Calendar.from_ical(f.read())
            for component in cal.walk("VEVENT"):
                try:
                    dtstart = component.get("DTSTART").dt
                    if hasattr(dtstart, "hour"):
                        # datetime object — strip timezone
                        dt = dtstart.replace(tzinfo=None)
                    else:
                        # date object — convert to datetime
                        from datetime import datetime as dt_cls
                        dt = dt_cls.combine(dtstart, dt_cls.min.time())

                    if dt < today or dt > end:
                        continue

                    summary = str(component.get("SUMMARY", "Cricket Match"))
                    location = str(component.get("LOCATION", ""))

                    import re
                    # Extract match type prefix e.g. "1st T20I", "2nd ODI", "3rd Test"
                    prefix_match = re.match(r'^(\d+\w+\s+(?:T20I|ODI|Test|T20))\s+(.+)$', summary)
                    if prefix_match:
                        match_label = prefix_match.group(1)
                        rest = prefix_match.group(2)
                    else:
                        match_label = ""
                        rest = summary

                    # Split teams on " v " or " vs "
                    if " v " in rest:
                        parts = rest.split(" v ", 1)
                    elif " vs " in rest:
                        parts = rest.split(" vs ", 1)
                    else:
                        parts = [rest, ""]

                    home = parts[0].strip()
                    away = parts[1].strip() if len(parts) > 1 else ""

                    # Skip Tour matches
                    if "Tour Match" in home or "Tour Match" in away:
                        continue

                    # Extract (Day X) from team names
                    import re as re2
                    day_match_home = re2.search(r'\(Day (\d+)\)', home)
                    day_match_away = re2.search(r'\(Day (\d+)\)', away)
                    if day_match_home:
                        day_label = f"Day {day_match_home.group(1)}"
                        home = re2.sub(r'\s*\(Day \d+\)', '', home).strip()
                        match_label = f"{match_label} · {day_label}" if match_label else day_label
                    elif day_match_away:
                        day_label = f"Day {day_match_away.group(1)}"
                        away = re2.sub(r'\s*\(Day \d+\)', '', away).strip()
                        match_label = f"{match_label} · {day_label}" if match_label else day_label

                    status = match_label
                    if location:
                        status += f" · {location}" if match_label else location

                    games.append({
                        "date": dt.strftime("%a %b %d"),
                        "time": dt.strftime("%Y-%m-%dT%H:%M:00Z"),
                        "home": home,
                        "away": away,
                        "home_logo": "https://www.cricketwi.com/wp-content/uploads/2020/02/CWI-Logo.png" if FLAG_CODES.get(home) == "wi" else (f"https://flagsapi.com/{FLAG_CODES.get(home, '').upper()}/flat/32.png" if FLAG_CODES.get(home) else ""),
                        "away_logo": "https://www.cricketwi.com/wp-content/uploads/2020/02/CWI-Logo.png" if FLAG_CODES.get(away) == "wi" else (f"https://flagsapi.com/{FLAG_CODES.get(away, '').upper()}/flat/32.png" if FLAG_CODES.get(away) else ""),
                        "status": status or "Cricket"
                    })

                except Exception:
                    continue
        except Exception as e:
            print(f"  Error reading {filename}: {e}")
            continue

    games.sort(key=lambda x: x["time"])
    print(f"  Got {len(games)} cricket matches from .ics files")
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

def build_html(nfl_games, nba_games, mlb_games, nhl_games, epl_games, wc_games, tennis_games, cricket_games):
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
                <div class='game-row-wrapper'>
                    <div class='match-label'>{g['status']}</div>
                    <div class='game-row'>
                    <div class='team-pill'>
                        <img class='team-logo' src='{g['away_logo']}' alt='{g['away']}' onerror='this.style.display="none"'/>
                        <span class='team-name'>{g['away']}</span>
                    </div>
                    <span class='vs-text'>vs</span>
                    <div class='team-pill'>
                        <img class='team-logo' src='{g['home_logo']}' alt='{g['home']}' onerror='this.style.display="none"'/>
                        <span class='team-name'>{g['home']}</span>
                    </div>
                    <span class='game-time' data-utc='{g['time']}'>{g['time']}</span>
                    <div class='ticket-wrap'>
                        <button class='tickets-btn' onclick='toggleDropdown(this)'>🎟 Tickets ▾</button>
                        <div class='ticket-dropdown'>
                            <a href='https://www.seatgeek.com/search?q={g["away"].replace(" ", "+")}+vs+{g["home"].replace(" ", "+")}' target='_blank'><img src='https://www.google.com/s2/favicons?domain=seatgeek.com&sz=16' class='vendor-logo'/>SeatGeek</a>
                            <a href='https://www.stubhub.com/search?q={g["away"].replace(" ", "+")}+{g["home"].replace(" ", "+")}' target='_blank'><img src='https://www.google.com/s2/favicons?domain=stubhub.com&sz=16' class='vendor-logo'/>StubHub</a>
                        </div>
                    </div>
                </div></div>"""
        return html

    updated = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

    nfl_html     = games_html(nfl_games)
    nba_html     = games_html(nba_games)
    mlb_html     = games_html(mlb_games)
    nhl_html     = games_html(nhl_games)
    epl_html     = games_html(epl_games)
    cricket_html = games_html(cricket_games)
    wc_html      = games_html(wc_games)
    tennis_html  = games_html(tennis_games)
    cricket_html = games_html(cricket_games)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PlyCal - Every game. Every timezone. Free.</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: #f7f8fc; color: #1a1f2e; min-height: 100vh; }}

        /* Header */
        header {{ background: #ffffff; border-bottom: 1px solid #eaecf4; padding: 0.9rem 1.5rem;
                  display: flex; align-items: center; justify-content: space-between; }}
        .logo-wrap {{ display: flex; align-items: center; gap: 9px; text-decoration: none; }}
        .logo-icon {{ width: 30px; height: 30px; background: #1a6ef5; border-radius: 7px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
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
        .team-logo[src=''] {{ display: none; }}
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
        .ticket-wrap {{ position: relative; flex-shrink: 0; margin-left: 8px; }}
        .tickets-btn {{ font-size: 11px; color: #1a6ef5; border: 1px solid #d0e0fd;
                        border-radius: 20px; padding: 3px 10px; background: #f0f5ff;
                        white-space: nowrap; cursor: pointer; }}
        .tickets-btn:hover {{ background: #1a6ef5; color: #ffffff; }}
        .ticket-dropdown {{ display: none; position: absolute; right: 0; top: 110%;
                            background: #ffffff; border: 1px solid #eaecf4;
                            border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                            z-index: 100; min-width: 130px; overflow: hidden; }}
        .ticket-dropdown a {{ display: block; padding: 0.6rem 1rem; font-size: 13px;
                              color: #1a1f2e; text-decoration: none; }}
        .ticket-dropdown a:hover {{ background: #f0f5ff; color: #1a6ef5; }}
        .ticket-dropdown.open {{ display: block; }}
        .vendor-logo {{ width: 16px; height: 16px; margin-right: 6px; vertical-align: middle; border-radius: 3px; }}
        .about-btn {{ background: #1a6ef5; color: #ffffff !important; padding: 5px 16px;
                      border-radius: 20px; font-weight: 500; }}
        .about-btn:hover {{ background: #1557d0; }}
        .match-label {{ font-size: 11px; color: #9099b0; white-space: nowrap; flex-shrink: 0; min-width: 70px; }}
        .game-row-wrapper {{ border-bottom: 0.5px solid #f0f2f8; }}
        .game-row-wrapper:last-child {{ border-bottom: none; }}
        .game-row {{ border-bottom: none !important; padding-bottom: 0.2rem; }}
        .match-label {{ font-size: 11px; color: #9099b0; padding: 0.5rem 1.25rem 0; }}
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
        <a href="/about.html" class="about-btn">About</a>
    </nav>
</header>

<div class="tabs-bar">
    <button class="tab active" onclick="show('nfl', this)">🏈 NFL</button>
    <button class="tab" onclick="show('nba', this)">🏀 NBA</button>
    <button class="tab" onclick="show('mlb', this)">⚾ MLB</button>
    <button class="tab" onclick="show('nhl', this)">🏒 NHL</button>
    <button class="tab" onclick="show('wc', this)">🏆 World Cup</button>
    <button class="tab" onclick="show('tennis', this)">🎾 Tennis</button>
    <button class="tab" onclick="show('epl', this)">⚽ Premier League</button>
    <button class="tab" onclick="show('cricket', this)">🏏 Cricket</button>
</div>

<div class="subscribe-bar" id="subscribe">
    <span>📅 Subscribe in your calendar app:</span>
    <a class="sub-btn" href="nfl.ics">🏈 NFL</a>
    <a class="sub-btn" href="nba.ics">🏀 NBA</a>
    <a class="sub-btn" href="mlb.ics">⚾ MLB</a>
    <a class="sub-btn" href="nhl.ics">🏒 NHL</a>
    <a class="sub-btn" href="wc.ics">🏆 World Cup</a>
    <a class="sub-btn" href="tennis.ics">🎾 Tennis</a>
    <a class="sub-btn" href="epl.ics">⚽ EPL</a>
    <a class="sub-btn" href="cricket.ics">🏏 Cricket</a>
</div>

<main>
    <div id="nfl" class="section active"><div class="card">{nfl_html}</div></div>
    <div id="nba" class="section"><div class="card">{nba_html}</div></div>
    <div id="mlb" class="section"><div class="card">{mlb_html}</div></div>
    <div id="nhl" class="section"><div class="card">{nhl_html}</div></div>
    <div id="wc" class="section"><div class="card">{wc_html}</div></div>
    <div id="tennis" class="section"><div class="card">{tennis_html}</div></div>
    <div id="epl" class="section"><div class="card">{epl_html}</div></div>
    <div id="cricket" class="section"><div class="card">{cricket_html}</div></div>
</main>

<footer>
    <p>Updated: {updated} &nbsp;·&nbsp; Data from ESPN & ESPNCricinfo &nbsp;·&nbsp;
    <a href="#subscribe">Subscribe via iCal</a> &nbsp;·&nbsp; Free forever</p>
</footer>

<script>
    function toggleDropdown(btn) {{
        const dropdown = btn.nextElementSibling;
        dropdown.classList.toggle('open');
        document.addEventListener('click', function closeHandler(e) {{
            if (!btn.parentElement.contains(e.target)) {{
                dropdown.classList.remove('open');
                document.removeEventListener('click', closeHandler);
            }}
        }});
    }}
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

    print("Fetching FIFA World Cup games...")
    wc = fetch_games("soccer", "soccer/fifa.world", "FIFA World Cup")
    print(f"  Got {len(wc)} games")

    print("Fetching Tennis games...")
    atp = fetch_games("tennis", "tennis/atp", "ATP")
    wta = fetch_games("tennis", "tennis/wta", "WTA")
    tennis = atp + wta
    tennis.sort(key=lambda x: x['time'])
    print(f"  Got {len(tennis)} tennis matches total")

    print("Fetching Cricket games from .ics files...")
    cricket = fetch_cricket_from_ics()

    html = build_html(nfl, nba, mlb, nhl, epl, wc, tennis, cricket)
    with open("index.html", "w") as f:
        f.write(html)
    print("index.html written.")

    for sport_name, games in [("NFL", nfl), ("NBA", nba), ("MLB", mlb), ("NHL", nhl), ("EPL", epl), ("WC", wc), ("Tennis", tennis), ("Cricket", cricket)]:
        ical = build_ical(games, sport_name)
        filename = f"{sport_name.lower()}.ics"
        with open(filename, "w") as f:
            f.write(ical)
        print(f"{filename} written.")

    print("Done!")
        
