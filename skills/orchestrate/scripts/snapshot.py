#!/usr/bin/env python3
"""Record review evidence without modifying the index or copying user files."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def snapshot(cwd, destination):
    out = Path(destination)
    out.mkdir()

    def git(*args):
        return subprocess.run(['git', '-C', cwd, *args], capture_output=True)

    root = git('rev-parse', '--show-toplevel')
    if root.returncode:
        (out / 'NO_GIT.txt').write_text('No Git baseline. Host must review file changes directly.\n')
        return
    cwd = os.fsdecode(root.stdout.rstrip(b'\n'))
    for name, args in {
        'head.txt': ('rev-parse', 'HEAD'),
        'status.txt': ('status', '--short', '--untracked-files=all'),
        'unstaged.patch': ('diff', '--binary', '--no-ext-diff', '--no-textconv'),
        'staged.patch': ('diff', '--cached', '--binary', '--no-ext-diff', '--no-textconv'),
    }.items():
        result = git(*args)
        (out / name).write_bytes(result.stdout)
        if result.returncode:
            (out / (name + '.error')).write_bytes(result.stderr)
    files = git('ls-files', '--others', '--exclude-standard', '-z')
    files.check_returncode()
    manifest = []
    for raw in files.stdout.split(b'\0'):
        if not raw:
            continue
        name = os.fsdecode(raw)
        path = Path(cwd) / name
        try:
            data = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
            manifest.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'symlink': path.is_symlink()})
        except OSError as exc:
            manifest.append({'path': name, 'error': str(exc)})
    (out / 'untracked.json').write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + '\n')


if __name__ == '__main__':
    snapshot(sys.argv[1], sys.argv[2])
