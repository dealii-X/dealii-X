#!/usr/bin/env python3
"""Generate a repository layout markdown page for the Sphinx site.

This script lists top-level directories and creates `doc/site-src/repository_layout.md`.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'doc' / 'site-src' / 'repository_layout.md'


def main():
    entries = []
    for p in sorted(ROOT.iterdir()):
        # skip hidden and doc/build folders
        if p.name.startswith('.') or p.name in ('build', 'doc'):
            continue
        if p.is_dir():
            entries.append((p.name, True))
        else:
            entries.append((p.name, False))

    with OUT.open('w', encoding='utf-8') as f:
        f.write('# Repository layout\n\n')
        f.write('Auto-generated list of top-level files and directories.\n\n')
        for name, is_dir in entries:
            if is_dir:
                f.write(f'- **{name}/**: placeholder page and description.\n')
            else:
                f.write(f'- `{name}`: file.\n')

    print('Wrote', OUT)


if __name__ == '__main__':
    main()
