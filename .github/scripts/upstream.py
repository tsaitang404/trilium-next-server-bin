#!/usr/bin/env python3
"""Check the official release digest, or prepare a stable upstream update."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

update = sys.argv[1:] == ['--update']
path = Path('PKGBUILD')
text = path.read_text()
current = re.search(r'^pkgver=(\S+)$', text, re.M)[1]
endpoint = 'latest' if update else 'tags/v' + current
headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'trilium-aur-ci'}
if os.environ.get('GH_TOKEN'):
    headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
request = urllib.request.Request('https://api.github.com/repos/TriliumNext/Trilium/releases/' + endpoint, headers=headers)
with urllib.request.urlopen(request, timeout=60) as response:
    release = json.load(response)
version = release['tag_name'].removeprefix('v')
if not re.fullmatch(r'\d+\.\d+\.\d+', version) or release['draft'] or release['prerelease']:
    raise SystemExit('Expected a stable numeric upstream release')
name = f'TriliumNotes-Server-v{version}-linux-x64.tar.xz'
assets = [a for a in release['assets'] if a['name'] == name]
if len(assets) != 1:
    raise SystemExit('Expected exactly one Linux x64 server asset')
asset = assets[0]
url = f'https://github.com/TriliumNext/Trilium/releases/download/v{version}/{name}'
if asset['browser_download_url'] != url or not re.fullmatch(r'sha256:[0-9a-f]{64}', asset.get('digest') or ''):
    raise SystemExit('Missing official SHA256 or unexpected asset URL')
digest = asset['digest'].split(':')[1]
if update:
    # Never silently downgrade if upstream latest points at an older release.
    if tuple(map(int, version.split('.'))) < tuple(map(int, current.split('.'))):
        raise SystemExit('Refusing upstream downgrade')
    text = re.sub(r'^pkgver=.*$', 'pkgver=' + version, text, flags=re.M)
    if version != current:
        text = re.sub(r'^pkgrel=.*$', 'pkgrel=1', text, flags=re.M)
    sums = [digest] + [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('trilium-next-server.sh', 'trilium-next-server.service')]
    text = re.sub(r"sha256sums=\([^)]*\)", "sha256sums=(" + '\n    '.join(repr(s) for s in sums) + ")", text)
    path.write_text(text)
else:
    sums = re.search(r'sha256sums=\(([^)]*)\)', text, re.S)[1]
    if re.findall(r"'([0-9a-f]{64})'", sums) != [digest] + [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('trilium-next-server.sh', 'trilium-next-server.service')]:
        raise SystemExit('PKGBUILD checksums differ from official asset or local sources')
print(f'Official upstream: v{version}, {name}, SHA256 {digest}')
