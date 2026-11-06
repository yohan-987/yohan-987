"""Generate assets/stats.svg and assets/langs.svg from the GitHub GraphQL API."""
import datetime as dt, html, json, os, sys, urllib.request

SANS = "'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Consolas,'Courier New',monospace"
RED, TXT, MUT = '#ff4d5a', '#e6edf3', '#8b98a9'

QUERY = """
query($login: String!, $from: DateTime!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, first: 100, orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection(from: $from) { totalCommitContributions }
  }
}
"""

def gql(query, variables, token):
    req = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({'query': query, 'variables': variables}).encode(),
        headers={'Authorization': f'bearer {token}', 'Content-Type': 'application/json',
                 'User-Agent': 'profile-stats'})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if 'errors' in payload or not payload.get('data', {}).get('user'):
        raise RuntimeError(f'GraphQL error: {payload.get("errors")}')
    return payload['data']['user']

def fetch(login, token):
    year = dt.datetime.now(dt.timezone.utc).year
    return gql(QUERY, {'login': login, 'from': f'{year}-01-01T00:00:00Z'}, token)

def fetch_days(login, token):
    """Return ({date: contribution_count}, lifetime commit count) for the whole life of the account."""
    created = gql('query($l:String!){user(login:$l){createdAt}}', {'l': login}, token)['createdAt']
    cur = dt.datetime.fromisoformat(created.replace('Z', '+00:00'))
    now = dt.datetime.now(dt.timezone.utc)
    windows = []
    while cur < now:
        end = min(cur + dt.timedelta(days=360), now)
        windows.append((cur, end))
        cur = end
    body = ''.join(
        f'y{i}:contributionsCollection(from:"{a.isoformat()}",to:"{b.isoformat()}")'
        '{totalCommitContributions contributionCalendar{weeks{contributionDays{date contributionCount}}}}'
        for i, (a, b) in enumerate(windows))
    data = gql('query($l:String!){user(login:$l){' + body + '}}', {'l': login}, token)
    days, commits = {}, 0
    for key in data:
        commits += data[key]['totalCommitContributions']
        for w in data[key]['contributionCalendar']['weeks']:
            for d in w['contributionDays']:
                day = dt.date.fromisoformat(d['date'])
                days[day] = max(days.get(day, 0), d['contributionCount'])
    return days, commits

def streaks(days, today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    days = {d: c for d, c in days.items() if d <= today}
    longest, run, start, last = (0, None, None), 0, None, None
    for d in sorted(days):
        if days[d] > 0:
            if run > 0 and last is not None and (d - last).days == 1:
                run += 1
            else:
                run, start = 1, d
            last = d
            if run > longest[0]:
                longest = (run, start, d)
        else:
            run = 0
    d = today if days.get(today, 0) > 0 else today - dt.timedelta(days=1)
    n, end = 0, d
    while days.get(d, 0) > 0:
        n += 1
        d -= dt.timedelta(days=1)
    current = (n, d + dt.timedelta(days=1) if n else None, end if n else None)
    active = [x for x in days if days[x] > 0]
    cutoff = today - dt.timedelta(days=365)
    year_total = sum(c for d, c in days.items() if d > cutoff)
    cal_year = sum(c for d, c in days.items() if d.year == today.year)
    return {'total': sum(days.values()), 'year': today.year, 'year_total': year_total, 'cal_year': cal_year, 'since': min(active) if active else None,
            'current': current, 'longest': longest}

def summarise(u):
    repos = u['repositories']['nodes']
    langs = {}
    for r in repos:
        for e in r['languages']['edges']:
            name = e['node']['name']
            cur = langs.setdefault(name, {'size': 0, 'color': e['node']['color'] or MUT})
            cur['size'] += e['size']
    total = sum(v['size'] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1]['size'])[:5]
    return {
        'stars': sum(r['stargazerCount'] for r in repos),
        'commits': u['contributionsCollection']['totalCommitContributions'],
        'prs': u['pullRequests']['totalCount'],
        'issues': u['issues']['totalCount'],
        'repos': u['repositories']['totalCount'],
        'langs': [(n, v['size'] / total * 100, v['color']) for n, v in top],
    }

def frame(w, h, label, inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{label}">'
            f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b0f17"/>'
            f'<stop offset="1" stop-color="#151d2b"/></linearGradient></defs>'
            f'<rect width="{w}" height="{h}" rx="16" fill="url(#bg)"/>'
            f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="16" fill="none" stroke="#fff" stroke-opacity=".10"/>'
            f'{inner}</svg>')

def render_stats(d):
    v = lambda k: '-' if d is None else f'{d[k]:,}'
    yr = dt.datetime.now(dt.timezone.utc).year
    rows = [(f'Contributions in {yr}', v('year_contribs')), (f'Commits in {yr}', v('commits')),
            ('Pull requests', v('prs')), ('Stars earned', v('stars')), ('Public repos', v('repos'))]
    s = f'<text x="24" y="40" font-family="{SANS}" font-size="18" font-weight="700" fill="{TXT}">Stats</text>'
    for i, (k, val) in enumerate(rows):
        y = 78 + i * 28
        s += (f'<circle cx="30" cy="{y-4}" r="3" fill="{RED}"/>'
              f'<text x="44" y="{y}" font-family="{SANS}" font-size="13.5" fill="{MUT}">{k}</text>'
              f'<text x="416" y="{y}" text-anchor="end" font-family="{SANS}" font-size="14" font-weight="700" fill="{TXT}">{val}</text>')
    return frame(440, 200, 'GitHub stats', s)

def render_langs(d):
    s = f'<text x="24" y="40" font-family="{SANS}" font-size="18" font-weight="700" fill="{TXT}">Top languages</text>'
    langs = [] if d is None else d['langs']
    if not langs:
        s += f'<text x="24" y="90" font-family="{SANS}" font-size="13" fill="{MUT}">Generating on the next workflow run...</text>'
    for i, (name, pct, color) in enumerate(langs):
        y = 72 + i * 25
        bw = max(4, 392 * pct / 100)
        s += (f'<text x="24" y="{y}" font-family="{SANS}" font-size="13" fill="{TXT}">{html.escape(name)}</text>'
              f'<text x="416" y="{y}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{MUT}">{pct:.1f}%</text>'
              f'<rect x="24" y="{y+6}" width="392" height="6" rx="3" fill="#fff" fill-opacity=".07"/>'
              f'<rect x="24" y="{y+6}" width="{bw:.1f}" height="6" rx="3" fill="{html.escape(color)}">'
              f'<animate attributeName="width" from="0" to="{bw:.1f}" dur=".9s" begin="{i*0.12:.2f}s" fill="freeze"/></rect>')
    return frame(440, 200, 'Top languages', s)

def fmt(d, year=False):
    return f"{d.strftime('%b')} {d.day}" + (f", {d.year}" if year else '')

def span(t):
    return '' if not t[1] else f'{fmt(t[1])} - {fmt(t[2])}'

def render_streak(c):
    W, H = 900, 170
    cols = [(150, 'Total contributions',
             None if c is None else f"{c['total']:,}",
             '' if c is None or not c['since'] else f"since {fmt(c['since'], True)}"),
            (450, 'Current streak', None if c is None else str(c['current'][0]),
             '' if c is None else span(c['current'])),
            (750, 'Longest streak', None if c is None else str(c['longest'][0]),
             '' if c is None else span(c['longest']))]
    s = ''
    for x in (300, 600):
        s += f'<line x1="{x}" y1="28" x2="{x}" y2="{H-28}" stroke="#fff" stroke-opacity=".12"/>'
    circ = 2 * 3.14159265 * 42
    frac = 0 if c is None else min(1, c['current'][0] / max(c['longest'][0], 1))
    for i, (cx, label, val, rng) in enumerate(cols):
        val_txt = '-' if val is None else val
        if i == 1:
            s += (f'<circle cx="{cx}" cy="70" r="42" fill="none" stroke="#fff" stroke-opacity=".08" stroke-width="5"/>'
                  f'<circle cx="{cx}" cy="70" r="42" fill="none" stroke="{RED}" stroke-width="5" stroke-linecap="round" '
                  f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ*(1-frac):.1f}" transform="rotate(-90 {cx} 70)">'
                  f'<animate attributeName="stroke-dashoffset" from="{circ:.1f}" to="{circ*(1-frac):.1f}" dur="1.2s" fill="freeze"/></circle>'
                  f'<text x="{cx}" y="82" text-anchor="middle" font-family="{SANS}" font-size="34" font-weight="800" fill="{TXT}">{val_txt}</text>'
                  f'<text x="{cx}" y="142" text-anchor="middle" font-family="{SANS}" font-size="14" font-weight="700" fill="{RED}">{label}</text>'
                  f'<text x="{cx}" y="160" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUT}">{rng}</text>')
        else:
            s += (f'<text x="{cx}" y="82" text-anchor="middle" font-family="{SANS}" font-size="42" font-weight="800" fill="{TXT}">{val_txt}</text>'
                  f'<text x="{cx}" y="116" text-anchor="middle" font-family="{SANS}" font-size="14" fill="{MUT}">{label}</text>'
                  f'<text x="{cx}" y="136" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUT}">{rng}</text>')
    return frame(W, H, 'Contribution streak', s)

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'assets'
    os.makedirs(out, exist_ok=True)
    if os.environ.get('PLACEHOLDER'):
        data = None
    elif os.environ.get('MOCK_JSON'):
        data = summarise(json.load(open(os.environ['MOCK_JSON'])))
    else:
        data = summarise(fetch(os.environ['GH_USER'], os.environ['GITHUB_TOKEN']))
    if os.environ.get('PLACEHOLDER'):
        cal = None
    elif os.environ.get('MOCK_JSON'):
        today = dt.date(2026, 11, 6)
        mock = {today - dt.timedelta(days=i): (0 if i in (9, 10, 30) else 1 + i % 3) for i in range(0, 60)}
        cal = streaks(mock, today)
        cal['life_commits'] = 150
    else:
        days, life = fetch_days(os.environ['GH_USER'], os.environ['GITHUB_TOKEN'])
        cal = streaks(days)
        cal['life_commits'] = life
    if data is not None and cal is not None:
        data['year_contribs'] = cal['cal_year']
    open(os.path.join(out, 'streak.svg'), 'w', encoding='utf-8').write(render_streak(cal))
    open(os.path.join(out, 'stats.svg'), 'w', encoding='utf-8').write(render_stats(data))
    open(os.path.join(out, 'langs.svg'), 'w', encoding='utf-8').write(render_langs(data))
    print('ok', data and {k: v for k, v in data.items() if k != 'langs'}, cal)

if __name__ == '__main__':
    main()
