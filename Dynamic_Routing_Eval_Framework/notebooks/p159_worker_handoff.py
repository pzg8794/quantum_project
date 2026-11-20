"""Notebook-only cleanup after the native parent validates a model result."""

from contextlib import contextmanager
from types import FunctionType, SimpleNamespace

from daqr.evaluation import model_process_executor
from macos_stderr import mute_malloc_stack_logging


class ResultWorker:
    def __init__(self, process, model):
        self.process = process
        self.model = model

    def __getattr__(self, name):
        return getattr(self.process, name)

    @property
    def exitcode(self):
        code = self.process.exitcode
        if code != 0:
            outcome = f"exit code {code}" if code is not None else "exit timed out"
            print(f"{self.model}: worker {outcome} after sending a valid result; keeping result.")
            try:
                if self.process.is_alive():
                    self.process.terminate()
                    self.process.join(timeout=5)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join(timeout=5)
            except OSError as error:
                print(f"{self.model}: worker cleanup pending: {error}")
        return 0


def result_context(method):
    context = model_process_executor.multiprocessing.get_context(method)

    def process(*, target, args):
        return ResultWorker(context.Process(target=target, args=args), args[1])

    return SimpleNamespace(Pipe=context.Pipe, Process=process)


@contextmanager
def model_worker_handoff():
    original = model_process_executor.run_models
    namespace = dict(original.__globals__, multiprocessing=SimpleNamespace(get_context=result_context))
    model_process_executor.run_models = FunctionType(original.__code__, namespace, argdefs=original.__defaults__)
    try:
        with mute_malloc_stack_logging():
            yield
    finally:
        model_process_executor.run_models = original


def report_status(operation, *args, **kwargs):
    if operation is not None:
        try:
            return operation(*args, **kwargs)
        except Exception as error:
            print(f"Workflow status pending: {error}")
