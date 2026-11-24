"""Regression tests for scripts/acpx-dispatch using a fake acpx; no model calls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'acpx-dispatch'

# Fake acpx: logs argv, answers sessions new / set with JSON actions, and for prompts runs
# $FAKE_BODY in --cwd and emits an ACP event stream (preamble, tool call, final report, stopReason).
FAKE_ACPX = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
args = sys.argv[1:]
log = os.environ['FAKE_LOG']
with open(os.path.join(log, 'calls.jsonl'), 'a') as f:
    f.write(json.dumps(args) + '\n')
cwd = args[args.index('--cwd') + 1]
if 'sessions' in args and 'new' in args:
    if os.environ.get('FAKE_FAIL_NEW'):
        print(json.dumps({'jsonrpc': '2.0', 'id': None, 'error': {'message': 'Cannot apply --model'}}))
        sys.exit(1)
    print('[acpx] created session x')
    print(json.dumps({'action': 'session_ensured', 'created': True, 'name': 'x'}))
    sys.exit(0)
if 'set' in args:
    print(json.dumps({'action': 'config_set', 'configId': args[-4], 'value': args[-3]}))
    sys.exit(0)
body = os.environ.get('FAKE_BODY', '')
if body:
    subprocess.run(['bash', '-c', body], cwd=cwd, check=False)
def upd(u):
    print(json.dumps({'jsonrpc': '2.0', 'method': 'session/update', 'params': {'update': u}}))
upd({'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text', 'text': 'preamble'}})
upd({'sessionUpdate': 'tool_call', 'title': 'edit'})
upd({'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text', 'text': '## 改动文件\n'}})
upd({'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text', 'text': 'ok'}})
print(json.dumps({'jsonrpc': '2.0', 'id': 3, 'result': {'stopReason': 'end_turn'}}))
sys.exit(int(os.environ.get('FAKE_RC', '0')))
'''


class DispatchTests(unittest.TestCase):
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
        fake = self.bin / 'acpx'
        fake.write_text(FAKE_ACPX)
        fake.chmod(0o755)
        self.env = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}', FAKE_LOG=str(self.log),
                        ACPX_DISPATCH_HOME=str(self.root / 'runs'))
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.repo / 'base').write_text('base\n')
        self.git('add', 'base')
        self.git('commit', '-qm', 'fixture')
        self.task = self.root / 'task.md'
        self.task.write_text('mock task')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True, text=True)

    def dispatch(self, *args, **env):
        return subprocess.run(['bash', str(SCRIPT), *args], cwd=self.root, env=dict(self.env, **env),
                              capture_output=True, text=True, timeout=30)

    def calls(self):
        path = self.log / 'calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def run_dir(self, name):
        return self.root / 'runs' / 'repo' / name

    def test_worktree_run_sets_options_and_extracts_final_report(self):
        r = self.dispatch('run', 'codex', 't1', str(self.task), '--repo', str(self.repo),
                          '--model', 'm1', '--effort', 'high', FAKE_BODY='echo hi > new.txt')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        wt = self.root / 'repo-wt' / 't1'
        self.assertTrue((wt / 'new.txt').exists())
        self.assertFalse((self.repo / 'new.txt').exists())
        new, set_effort, prompt = self.calls()
        self.assertIn('--model', new)
        self.assertEqual(set_effort[-4:], ['reasoning_effort', 'high', '-s', 't1'])
        self.assertNotIn('--model', prompt)
        for flag in ('--approve-all', '--format', '--ttl', '--suppress-reads'):
            self.assertIn(flag, prompt)
        self.assertEqual(prompt[prompt.index('--ttl') + 1], '3600')
        self.assertEqual((self.run_dir('t1') / 'final.md').read_text(), '## 改动文件\nok')
        self.assertIn('stopReason=end_turn', r.stdout)
        self.assertIn('?? new.txt', r.stdout)

    def test_revise_reuses_session_and_increments_round(self):
        self.dispatch('run', 'claude', 't1', str(self.task), '--repo', str(self.repo))
        r = self.dispatch('revise', 't1', str(self.task), '--repo', str(self.repo))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        last = self.calls()[-1]
        self.assertEqual(last[last.index('-s') + 1], 't1')
        self.assertIn('--approve-all', last)
        self.assertTrue((self.run_dir('t1') / 'events-2.jsonl').exists())
        self.assertIn('第 2 轮', r.stdout)

    def test_read_only_uses_exec_with_adapter_read_only_mode(self):
        for worker, mode in (('codex', 'mode=read-only'), ('claude', 'mode=default'),
                             ('cc-api', 'mode=default'), ('agy', 'mode=plan')):
            r = self.dispatch('run', worker, f'ro-{worker}', str(self.task), '--repo', str(self.repo),
                              '--mode', 'read-only')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            call = self.calls()[-1]
            self.assertIn('exec', call)
            self.assertEqual(call[call.index('--config-option') + 1], mode)
            self.assertIn('--no-terminal', call)
        r = self.dispatch('run', 'grok', 'ro-grok', str(self.task), '--repo', str(self.repo), '--mode', 'read-only')
        self.assertNotIn('--config-option', self.calls()[-1])

    def test_read_only_violation_exits_6(self):
        (self.repo / 'base').write_text('dirty\n')
        r = self.dispatch('run', 'codex', 'ro', str(self.task), '--repo', str(self.repo), '--mode', 'read-only',
                          FAKE_BODY='echo again >> base')
        self.assertEqual(r.returncode, 6, r.stdout + r.stderr)
        self.assertIn('违规', r.stdout)

    def test_in_place_sets_claude_default_mode_and_rejects_agy(self):
        r = self.dispatch('run', 'claude', 'ip', str(self.task), '--repo', str(self.repo), '--mode', 'in-place')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        new, set_mode, prompt = self.calls()
        self.assertEqual(set_mode[-4:], ['mode', 'default', '-s', 'ip'])
        self.assertIn('--no-fs', new)
        self.assertIn('--no-fs', prompt)
        r = self.dispatch('run', 'agy', 'ip2', str(self.task), '--repo', str(self.repo), '--mode', 'in-place')
        self.assertEqual(r.returncode, 2)

    def test_failed_session_creation_rolls_back_worktree(self):
        r = self.dispatch('run', 'codex', 't1', str(self.task), '--repo', str(self.repo), '--model', 'bad',
                          FAKE_FAIL_NEW='1')
        self.assertEqual(r.returncode, 2)
        self.assertIn('已回滚', r.stderr)
        self.assertFalse((self.root / 'repo-wt' / 't1').exists())
        self.assertFalse(self.run_dir('t1').exists())
        self.assertNotIn('agent/t1', self.git('branch').stdout)

    def test_propagates_acpx_exit_code(self):
        r = self.dispatch('run', 'codex', 't1', str(self.task), '--repo', str(self.repo), FAKE_RC='3')
        self.assertEqual(r.returncode, 3)


if __name__ == '__main__':
    unittest.main()
