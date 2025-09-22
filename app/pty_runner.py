from __future__ import annotations
import asyncio
import os
from typing import AsyncIterator, Tuple

async def run_command_stream(cmd: str) -> AsyncIterator[Tuple[str, str]]:
    """Run a shell command and yield (stream, chunk) where stream is 'stdout' or 'stderr'.
    Falls back to pipes for cross-platform simplicity.
    """
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def reader(stream, tag):
        while True:
            line = await stream.readline()
            if not line:
                break
            yield tag, line.decode(errors="ignore")

    stdout_gen = reader(proc.stdout, "stdout")
    stderr_gen = reader(proc.stderr, "stderr")

    # iterate until both generators are exhausted
    stdout_next = None
    stderr_next = None
    stdout_task = None
    stderr_task = None
    try:
        stdout_task = asyncio.create_task(stdout_gen.__anext__())
        stderr_task = asyncio.create_task(stderr_gen.__anext__())
        while True:
            done, pending = await asyncio.wait(
                {t for t in (stdout_task, stderr_task) if t is not None},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in done:
                try:
                    tag, chunk = t.result()
                    yield tag, chunk
                except StopAsyncIteration:
                    # the generator finished; set its task to None
                    if t is stdout_task:
                        stdout_task = None
                    if t is stderr_task:
                        stderr_task = None
                # restart the completed task if its generator still exists
                if t is stdout_task:
                    if stdout_task is not None:
                        try:
                            stdout_task = asyncio.create_task(stdout_gen.__anext__())
                        except StopAsyncIteration:
                            stdout_task = None
                if t is stderr_task:
                    if stderr_task is not None:
                        try:
                            stderr_task = asyncio.create_task(stderr_gen.__anext__())
                        except StopAsyncIteration:
                            stderr_task = None
            # if both are None, break
            if stdout_task is None and stderr_task is None:
                break
    finally:
        # ensure process finished
        try:
            await proc.wait()
        except Exception:
            pass
