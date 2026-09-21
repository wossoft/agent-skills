"""Regression tests using isolated repositories and fake workers; no model calls."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'agent-run'


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=str(self.bin) + ':' + os.environ['PATH'],
                        AGENT_RUN_HOME=str(self.root / 'agents'))
        self.git('init')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.repo / 'base').write_text('base\n')
        self.git('add', 'base')
        self.git('commit', '-m', 'fixture')
        self.task = self.root / 'task.md'
        self.task.write_text('mock task')
        self.worker('printf "%s\\n" "$PWD"')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)

    def worker(self, body):
        path = self.bin / 'claude'
        path.write_text('#!/bin/bash\nset -eu\n' + body + '\n')
        path.chmod(0o755)

    def run_worker(self, *args):
        return subprocess.run(['bash', str(SCRIPT), 'claude', str(self.task), '--cwd', str(self.repo), *args],
                              cwd=self.root, env=self.env, capture_output=True, text=True, timeout=10)

    def runs(self):
        return list((self.root / 'agents' / 'runs').iterdir())

    def test_worktree_uses_isolated_directory(self):
        self.worker('printf "changed\\n" > base\npwd')
        result = self.run_worker('--worktree')
        self.assertEqual(result.returncode, 0, result.stderr)
        worktree = next((self.root / 'agents' / 'worktrees').iterdir())
        self.assertEqual((worktree / 'base').read_text(), 'changed\n')
        self.assertEqual((self.repo / 'base').read_text(), 'base\n')
        self.assertIn(str(worktree), (self.runs()[0] / 'stdout.txt').read_text())

    def test_dirty_worktree_is_rejected_without_launch(self):
        (self.repo / 'new').write_text('user content')
        self.worker('touch worker-ran')
        result = self.run_worker('--worktree')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('clean checkout', result.stderr)
        self.assertFalse((self.repo / 'worker-ran').exists())
        self.assertEqual((self.repo / 'new').read_text(), 'user content')

    def test_same_second_parallel_runs_are_unique(self):
        date = self.bin / 'date'
        date.write_text('#!/bin/bash\necho 20260921-120000\n')
        date.chmod(0o755)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: self.run_worker(), range(2)))
        self.assertTrue(all(r.returncode == 0 for r in results))
        self.assertEqual(len(self.runs()), 2)
        self.assertTrue(all((p / 'report.md').exists() for p in self.runs()))

    def test_timeout_kills_children_and_records_failure(self):
        self.worker('(sleep 2; touch leaked) &\nwait')
        result = self.run_worker('--timeout', '1')
        self.assertEqual(result.returncode, 124, result.stderr)
        time.sleep(1.2)
        self.assertFalse((self.repo / 'leaked').exists())
        self.assertEqual((self.runs()[0] / 'status').read_text().strip(), '124')

    def test_snapshots_preserve_baseline_and_cover_staged_and_new(self):
        (self.repo / 'base').write_text('user edit\n')
        self.worker('printf "worker edit\\n" >>base\ngit add base\nprintf "new\\n" >new-file')
        result = self.run_worker()
        self.assertEqual(result.returncode, 0, result.stderr)
        run = self.runs()[0]
        self.assertIn('user edit', (run / 'before' / 'unstaged.patch').read_text())
        self.assertIn('worker edit', (run / 'after' / 'staged.patch').read_text())
        files = json.loads((run / 'after' / 'untracked.json').read_text())
        self.assertEqual(files[0]['path'], 'new-file')
        self.assertTrue((self.repo / 'base').read_text().startswith('user edit\n'))

    def test_failure_is_not_reported_as_success(self):
        self.worker('exit 7')
        result = self.run_worker()
        self.assertEqual(result.returncode, 7)
        self.assertEqual((self.runs()[0] / 'status').read_text().strip(), '7')


if __name__ == '__main__':
    unittest.main()
