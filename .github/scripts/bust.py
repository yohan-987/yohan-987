"""Append a content hash to generated image URLs in README.md so GitHub's image cache refetches changed files."""
import hashlib, pathlib, re

readme = pathlib.Path('README.md')
with open(readme, encoding='utf-8', newline='') as f:
    text = f.read()
for name in ('stats', 'langs', 'streak', 'highlights'):
    digest = hashlib.sha1(pathlib.Path(f'assets/{name}.svg').read_bytes()).hexdigest()[:8]
    text = re.sub(rf'assets/{name}\.svg(\?v=[0-9a-f]+)?', f'assets/{name}.svg?v={digest}', text)
with open(readme, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print('cache keys updated')
