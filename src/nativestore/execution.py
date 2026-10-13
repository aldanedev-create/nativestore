"""Bound waiting and serialize application execution without unsafe thread termination."""

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class ExecutionTimeout(Exception):
    pass


class ExecutionBusy(Exception):
    pass


@dataclass
class Job:
    function: Callable[[], Any]
    done: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: BaseException | None = None


class Execution:
    def __init__(self):
        self.gate = threading.Lock()
        self.jobs: queue.Queue[Job | None] = queue.Queue(maxsize=1)
        self.closed = False
        self.worker = threading.Thread(
            target=self._work, daemon=True, name="nativestore-application"
        )
        self.worker.start()

    def _work(self):
        while True:
            job = self.jobs.get()
            if job is None:
                return
            try:
                job.result = job.function()
            except BaseException as exc:
                job.error = exc
            finally:
                self.gate.release()
                job.done.set()

    def run(self, function: Callable[[], Any], timeout: float) -> Any:
        if self.closed or not self.gate.acquire(blocking=False):
            raise ExecutionBusy()
        job = Job(function)
        self.jobs.put_nowait(job)
        if not job.done.wait(timeout):
            raise ExecutionTimeout()
        if job.error is not None:
            raise job.error
        return job.result

    def close(self):
        self.closed = True
        # A hung handler must never make application shutdown wait indefinitely.
        try:
            self.jobs.put_nowait(None)
        except queue.Full:
            pass
