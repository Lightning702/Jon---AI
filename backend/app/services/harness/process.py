from __future__ import annotations

import asyncio
import os
import signal
import subprocess


async def run_command(command: str, cwd: str, timeout: int = 180) -> dict:
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    argv = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "$ErrorActionPreference = 'Stop'\n" + command + "\nif ($null -ne $LASTEXITCODE) { exit $LASTEXITCODE }"] if os.name == "nt" else ["/bin/sh", "-c", command]
    process = await asyncio.create_subprocess_exec(*argv, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, **options)
    job = None
    if os.name == "nt":
        from app.services.harness.windows_job import WindowsJob

        try:
            job = WindowsJob(process.pid)
        except OSError:
            process.kill()
            await process.wait()
            raise
    output = bytearray()

    async def read_output() -> None:
        while chunk := await process.stdout.read(8192):
            output.extend(chunk)
            if len(output) > 64000:
                del output[:-64000]

    async def terminate() -> None:
        if job:
            job.close()
        elif os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        await process.wait()

    reader = asyncio.create_task(read_output())
    timed_out = False
    try:
        await asyncio.wait_for(asyncio.shield(process.wait()), timeout=max(1, min(timeout, 600)))
        await asyncio.wait_for(asyncio.shield(reader), timeout=3)
    except asyncio.TimeoutError:
        timed_out = True
        await terminate()
    except asyncio.CancelledError:
        await terminate()
        raise
    finally:
        await terminate()
        if not reader.done():
            reader.cancel()
        await asyncio.gather(reader, return_exceptions=True)
    return {"command": command, "exit_code": process.returncode, "timed_out": timed_out, "output": output.decode("utf-8", errors="replace"), "ok": process.returncode == 0 and not timed_out}
