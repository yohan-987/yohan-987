"""Generate assets/stats.svg and assets/langs.svg from the GitHub GraphQL API."""
import html, json, os, sys, urllib.request

SANS = "'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Consolas,'Courier New',monospace"
RED, TXT, MUT = '#ff4d5a', '#e6edf3', '#8b98a9'

QUERY = """
query($login: String!) {
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
    contributionsCollection { totalCommitContributions }
  }
}
"""

def fetch(login, token):
    req = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({'query': QUERY, 'variables': {'login': login}}).encode(),
        headers={'Authorization': f'bearer {token}', 'Content-Type': 'application/json',
                 'User-Agent': 'profile-stats'})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if 'errors' in payload or not payload.get('data', {}).get('user'):
        raise RuntimeError(f'GraphQL error: {payload.get("errors")}')
    return payload['data']['user']

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
    rows = [('Stars earned', v('stars')), ('Commits, last year', v('commits')),
            ('Pull requests', v('prs')), ('Issues', v('issues')), ('Public repos', v('repos'))]
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

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'assets'
    os.makedirs(out, exist_ok=True)
    if os.environ.get('PLACEHOLDER'):
        data = None
    elif os.environ.get('MOCK_JSON'):
        data = summarise(json.load(open(os.environ['MOCK_JSON'])))
    else:
        data = summarise(fetch(os.environ['GH_USER'], os.environ['GITHUB_TOKEN']))
    open(os.path.join(out, 'stats.svg'), 'w', encoding='utf-8').write(render_stats(data))
    open(os.path.join(out, 'langs.svg'), 'w', encoding='utf-8').write(render_langs(data))
    print('ok', data and {k: v for k, v in data.items() if k != 'langs'})

if __name__ == '__main__':
    main()
