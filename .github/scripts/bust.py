"""Append a content hash to generated image URLs in README.md so GitHub's image cache refetches changed files."""
import hashlib, pathlib, re

readme = pathlib.Path('README.md')
text = readme.read_text(encoding='utf-8', newline='')
for name in ('stats', 'langs', 'streak', 'highlights'):
    digest = hashlib.sha1(pathlib.Path(f'assets/{name}.svg').read_bytes()).hexdigest()[:8]
    text = re.sub(rf'assets/{name}\.svg(\?v=[0-9a-f]+)?', f'assets/{name}.svg?v={digest}', text)
readme.write_text(text, encoding='utf-8', newline='')
print('cache keys updated')
