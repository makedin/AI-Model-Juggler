import socket
import time

from pathlib import Path
from subprocess import Popen, PIPE

from config import AIBackendConfig, AIModelConfig

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


class AIBackend:
    def __init__(self, config: AIBackendConfig, model: AIModelConfig, host: str):
        self.service_process = None
        self.is_ready = False
        self.backend_port = None
        self.host = host

        self.type = config.type
        self.service_name = "[Service name not set]"
        self.model_name = model.name

        self.service_binary = config.binary
        self.service_parameters = model.parameters or []

        self.initial_startup_delay = 0.15  # seconds
        self.subsequent_startup_delay = 0.3  # seconds
        self.startup_delay_multiplier = 1.1

    def isRunning(self):
        if self.service_process is None:
            return False

        if self.service_process.poll() is not None:
            self.service_process = None
            self.is_ready = False
            self.backend_port = None
            return False

        return True


    def isReady(self) -> bool:
        if not self.isRunning():
            raise RuntimeError(f"{self.service_name} is not running.")

        return self.is_ready

    def shutdown(self):
        if not self.isRunning():
            return

        self._preShutdown()

        if self.service_process is not None:
            self.service_process.terminate()
            self.service_process.wait()

        self.service_process = None
        self.is_ready = False
        self.backend_port = None

        print(f"{self.service_name} stopped.")


    def stopService(self, force: bool = False):
        self.shutdown()

    def startService(self) -> bool:
        elapsed_time_reference = time.monotonic()

        if self.isRunning():
            return True

        if not Path(self.service_binary).exists():
            raise FileNotFoundError(f"Service binary {self.service_binary} does not exist.")

        print(f"Starting {self.service_name}...")

        self.backend_port = free_port()

        extra_parameters = self._extraPopenParameters()

        self.service_process = Popen(
                [self.service_binary, *self.service_parameters, *extra_parameters],
                stdout=PIPE,
                stderr=PIPE,
                text=True,
                bufsize=1)

        time.sleep(self.initial_startup_delay)  # give the service some time to start

        if not self.isRunning():
            raise RuntimeError("Service failed to start.")


        print(self.service_process.pid)
        print(self.backend_port)

        delay = self.startup_delay_multiplier
        while True:
            if self.isReady():
                elapsed_time = time.monotonic() - elapsed_time_reference
                print(f"{self.service_name} started in {elapsed_time:.2f} seconds.")
                print(f"{self.service_name} is running on port {self.backend_port}.")
                self._postStartUp()
                return True

            # wait for the service to be ready
            time.sleep(delay)
            delay *= self.startup_delay_multiplier

    def _extraPopenParameters(self) -> list:
        """
        Override this method in subclasses to provide additional parameters for the Popen command.
        """
        return []

    def _postStartUp(self):
        """
        Override this method in subclasses to perform additional actions after the service has started.
        """
        pass

    def _preShutdown(self):
        """
        Override this method in subclasses to perform additional actions before the service is stopped.
        """
        pass
