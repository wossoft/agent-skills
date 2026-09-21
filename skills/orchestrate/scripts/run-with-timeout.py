#!/usr/bin/env python3
"""Bound a worker process group, including subprocesses, on POSIX hosts."""
import os
import signal
import subprocess
import sys


def run(seconds, command):
    process = subprocess.Popen(command, start_new_session=True)

    def stop(signum, _frame=None):
        # Kill the whole group, even if its leader has already exited.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        return 124 if signum is None else 128 + signum

    def interrupted(signum, frame):
        sys.exit(stop(signum, frame))

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupted)
    try:
        result = process.wait(timeout=seconds)
        return result if result >= 0 else 128 - result
    except subprocess.TimeoutExpired:
        print(f"agent-run: worker exceeded {seconds}s; process group terminated", file=sys.stderr)
        return stop(None)


if __name__ == '__main__':
    sys.exit(run(int(sys.argv[1]), sys.argv[2:]))
