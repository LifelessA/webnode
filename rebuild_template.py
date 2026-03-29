"""
rebuild_template.py — Build _project_template from project_code_for_gamma.txt
Run: python rebuild_template.py
"""
import os
import re
import shutil

SRC_FILE    = 'project_code_for_gamma.txt'
TEMPLATE    = 'webnode/_project_template'

# ── 1. Read source ──────────────────────────────────────────────────
print(f'Reading {SRC_FILE} ...')
with open(SRC_FILE, 'r', encoding='utf-8') as f:
    raw = f.read()
print(f'  {len(raw)} chars, {raw.count(chr(10))} lines')

# ── 2. Parse file blocks ─────────────────────────────────────────────
#  Format:
#  === FILE: .\path\to\file.py ===
#  ...content...
#  ========================================
FILE_HEADER = re.compile(r'^=== FILE: (.+?) ===$', re.MULTILINE)
SEP = re.compile(r'^={30,}$', re.MULTILINE)

headers = list(FILE_HEADER.finditer(raw))
files   = {}

for idx, hdr in enumerate(headers):
    path_raw = hdr.group(1).strip()
    body_start = hdr.end()

    # End = next FILE header OR next long separator, whichever is first
    next_hdr_pos = headers[idx + 1].start() if idx + 1 < len(headers) else len(raw)
    body = raw[body_start:next_hdr_pos]

    # Strip trailing separator line
    body = re.sub(r'\n={30,}\s*$', '', body).strip('\r\n')

    # Normalize path: remove leading .\  or ./ convert \ → /
    rel = path_raw.replace('.\\', '').replace('./', '').replace('\\', '/')
    files[rel] = body

print(f'  Files parsed: {len(files)}')
for k in sorted(files):
    print(f'    {k:50s}  ({len(files[k])} chars)')

# ── 3. Skip files that should NOT be in the template ────────────────
# (log files, pycache, sqlite, temp/test files)
def should_skip(rel):
    SKIP_EXACT = {
        'test_logger.py', 'test_zoom.html',
        'db.sqlite3', 'db.sqlite3-shm', 'db.sqlite3-wal',
        '.secret_key', '.env',
    }
    SKIP_DIRS = {'__pycache__', 'core/logs'}
    SKIP_EXT  = {'.pyc', '.jsonl', '.log', '.txt' }   # log/cache

    fname = rel.split('/')[-1]
    if fname in SKIP_EXACT:
        return True
    for sd in SKIP_DIRS:
        if rel.startswith(sd):
            return True
    ext = os.path.splitext(fname)[1].lower()
    if ext in SKIP_EXT and 'templates/' not in rel:
        return True
    return False

# ── 4. Wipe and recreate template dir ───────────────────────────────
print(f'\nResetting {TEMPLATE} ...')
if os.path.exists(TEMPLATE):
    shutil.rmtree(TEMPLATE)
os.makedirs(TEMPLATE)

# ── 5. Write every valid file ────────────────────────────────────────
written = []
skipped = []

for rel, content in files.items():
    if should_skip(rel):
        skipped.append(rel)
        continue
    dest = os.path.join(TEMPLATE, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    written.append(rel)

print('\nWRITTEN:')
for w in sorted(written):
    print(f'  [ok] {w}')
print('\nSKIPPED:')
for s in sorted(skipped):
    print(f'  [--] {s}')

# ── 6. Add structural extras that aren't in the source file ─────────
extras = {
    'nodes/middleware/__init__.py': '',
    'nodes/__init__.py':            '',
    'core/__init__.py':             '',
    'plugins/__init__.py':          '',
    'static/__init__.py':           '',
    '.env.example': (
        '# Copy this file to .env and fill in your values\n'
        'DEBUG=True\n'
        'HOST=127.0.0.1\n'
        'PORT=8000\n'
    ),
    'core/logs/.gitkeep':           '',
    'core/logs/errors/.gitkeep':    '',
    'static/img/.gitkeep':          '',
}

print('\nEXTRAS:')
for rel, body in extras.items():
    dest = os.path.join(TEMPLATE, rel.replace('/', os.sep))
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(body)
        print(f'  [ok] {rel}')
    else:
        print(f'  [exists] {rel}')

print(f'\nDone — {len(written)} files written, {len(skipped)} skipped.')
