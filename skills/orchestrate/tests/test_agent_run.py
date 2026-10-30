"""Regression tests using isolated repositories and fake workers; no model calls."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'agent-run'

# Fake claude: records its argv and environment, runs BODY, then emits a stream-json result.
FAKE_CLAUDE = '''#!/bin/bash
printf '%s\\n' "$@" > "$FAKE_LOG/argv"
printf '%s\\n' "${CLAUDE_CONFIG_DIR:-}" > "$FAKE_LOG/config_dir"
printf '%s\\n' "${AGENT_RUN_WORKER:-}" > "$FAKE_LOG/worker_flag"
BODY
echo '{"type":"result","result":"## 改动文件\\nok"}'
'''


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.log = self.root / 'log'
        self.log.mkdir()
        self.config = self.root / 'config'
        self.env = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}', FAKE_LOG=str(self.log),
                        AGENT_RUN_HOME=str(self.root / 'runs'), AGENT_RUN_CONFIG=str(self.config))
        self.env.pop('AGENT_RUN_WORKER', None)
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.repo / 'base').write_text('base\n')
        self.git('add', 'base')
        self.git('commit', '-qm', 'fixture')
        self.task = self.root / 'task.md'
        self.task.write_text('mock task')
        self.worker('')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True, text=True)

    def worker(self, body):
        path = self.bin / 'claude'
        path.write_text(FAKE_CLAUDE.replace('BODY', body))
        path.chmod(0o755)

    def run_agent(self, *args, agent='claude', name='t1'):
        return subprocess.run(['bash', str(SCRIPT), agent, name, str(self.task), '--repo', str(self.repo), *args],
                              cwd=self.root, env=self.env, capture_output=True, text=True, timeout=30)

    def run_dir(self, name='t1'):
        return self.root / 'runs' / 'repo' / name

    def argv(self):
        return (self.log / 'argv').read_text().splitlines()

    def test_build_runs_in_worktree_and_patch_includes_new_files(self):
        (self.repo / 'base').write_text('user edit\n')
        self.worker('printf "worker\\n" > base; printf "new\\n" > added')
        result = self.run_agent()
        self.assertEqual(result.returncode, 0, result.stderr)
        worktree = self.root / 'repo-wt' / 't1'
        self.assertEqual((worktree / 'base').read_text(), 'worker\n')
        self.assertEqual((self.repo / 'base').read_text(), 'user edit\n')
        patch = (self.run_dir() / 'patch.diff').read_text()
        self.assertIn('+worker', patch)
        self.assertIn('added', patch)
        self.assertIn('--dangerously-skip-permissions', self.argv())

    def test_in_place_keeps_permission_controls(self):
        result = self.run_agent('--in-place')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('--dangerously-skip-permissions', self.argv())
        self.assertIn('acceptEdits', self.argv())
        self.assertFalse((self.root / 'repo-wt').exists())

    def test_plan_mode_flags_file_changes(self):
        self.worker('touch sneaky')
        result = self.run_agent('--mode', 'plan')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Edit Write NotebookEdit', self.argv())
        self.assertIn('只读任务改动了工作区', (self.run_dir() / 'changes.txt').read_text())

    def test_nested_dispatch_is_refused(self):
        self.worker('bash "$AGENT_RUN_SCRIPT" claude inner "$AGENT_RUN_TASK" --repo "$PWD"; echo "rc=$?" > "$FAKE_LOG/inner"')
        self.env.update(AGENT_RUN_SCRIPT=str(SCRIPT), AGENT_RUN_TASK=str(self.task))
        result = self.run_agent('--in-place')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.log / 'worker_flag').read_text().strip(), '1')
        self.assertEqual((self.log / 'inner').read_text().strip(), 'rc=2')
        self.assertFalse(self.run_dir('inner').exists())

    def test_config_overrides_tier_and_cc_api_config_dir(self):
        self.config.write_text('TIER_cc_api_hard="glm-x max"\nCC_API_CONFIG_DIR=/opt/cc\n')
        result = self.run_agent('--tier', 'hard', '--in-place', agent='cc-api')
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = self.argv()
        self.assertEqual(argv[argv.index('--model') + 1], 'glm-x')
        self.assertEqual(argv[argv.index('--effort') + 1], 'max')
        self.assertEqual((self.log / 'config_dir').read_text().strip(), '/opt/cc')

    def test_explicit_model_beats_tier(self):
        self.config.write_text('TIER_claude_complex="from-config high"\n')
        result = self.run_agent('--in-place', '--model', 'manual')
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = self.argv()
        self.assertEqual(argv[argv.index('--model') + 1], 'manual')
        self.assertEqual(argv[argv.index('--effort') + 1], 'high')

    def test_timeout_kills_process_group(self):
        self.worker('(sleep 3; touch "$FAKE_LOG/leaked") & wait')
        result = self.run_agent('--timeout', '1', '--in-place')
        self.assertEqual(result.returncode, 124, result.stderr)
        time.sleep(3)
        self.assertFalse((self.log / 'leaked').exists())
        self.assertTrue((self.run_dir() / 'status').read_text().startswith('timeout'))

    def test_failure_is_not_reported_as_success(self):
        self.worker('exit 7')
        result = self.run_agent('--in-place')
        self.assertEqual(result.returncode, 1)
        self.assertIn('failed rc=7', (self.run_dir() / 'status').read_text())

    def test_failed_check_is_recorded(self):
        result = self.run_agent('--in-place', '--check', 'false')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('check=fail', (self.run_dir() / 'status').read_text())


if __name__ == '__main__':
    unittest.main()
