import socket
import time

from pathlib import Path
from subprocess import Popen, PIPE
from typing import Dict, List

from .config import AIBackendConfig, EndpointConfig, getConfig, ServerConfig

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


class AIBackend:
    supports_executing_directly            = False
    supports_attaching_to_running_instance = False
    supports_kv_cache_restoring            = False
    supports_model_unloading               = False

    def __init__(self, config: AIBackendConfig, server: ServerConfig, endpoint: EndpointConfig):

        self.service_process = None
        self.is_ready = False
        self.backend_port = None
        self.host = server.host

        self.type = config.type
        self.service_name = f"{self.type} backend ({server.name}, {endpoint.name})"
        self.endpoint = endpoint

        self.service_binary = config.binary
        self.service_parameters = config.default_parameters + endpoint.parameters

        self.attached_instance = config.attached_instance
        self._is_attached = False

        self.model_unloading = config.model_unloading

        self.kv_cache_save_path = getConfig().temp_dir / 'kv_cache' if endpoint.kv_cache_saving else None

        self.initial_startup_delay = 0.15  # seconds
        self.subsequent_startup_delay = 0.3  # seconds
        self.startup_delay_multiplier = 1.1

    def isRunning(self) -> bool:
        if self.service_process is None:
            return False

        if self.service_process.poll() is not None:
            self.service_process = None
            self.is_ready = False
            self.backend_port = None
            return False

        return True

    def isAttached(self) -> bool:
        return self._is_attached


    def isReady(self) -> bool:
        if self.isAttached() is True:
            return True

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
        if not self.isRunning() and not self.isAttached():
            return

        if self.kv_cache_save_path is not None:
            self.saveKVCache()

        if not force and self.model_unloading is True:
            self.unloadModel()

        else:
            self.shutdown()

    def attachInstance(self) -> bool:
        raise NotImplementedError(f"Instance attachment is not implemented for {type(self).__name__} backend.")

    def unloadModel(self):
        raise NotImplementedError("Model unloading is not implemented for this backend.")

    def saveKVCache(self) -> bool:
        raise NotImplementedError("KV cache saving is not implemented for this backend.")

    def restoreKVCache(self) -> bool:
        raise NotImplementedError("KV cache restoring is not implemented for this backend.")


    def readyService(self) -> bool:
        if self.isAttached():
            return True

        if self.isRunning():
            return True

        if self.attached_instance is not None:
            if self.attachInstance():
                return True

        if self.service_binary is not None:
            return self.startService()

        print(f"Service {self.type} binary is not set and no instance is attached.")
        return False


    def startService(self) -> bool:
        elapsed_time_reference = time.monotonic()

        if self.isRunning():
            return True

        if not Path(self._getServiceBinaryPath()).exists():
            raise FileNotFoundError(f"Service binary {self.service_binary} does not exist.")

        print(f"Starting {self.service_name}...")

        self.backend_port = free_port()

        parameters = self._modifyParameters(self.service_parameters)

        self.service_process = Popen(
                [self._getServiceBinaryPath(), *parameters],
                stdout=PIPE,
                stderr=PIPE,
                text=True,
                bufsize=1,
                env=self._modifyEnvironment())

        time.sleep(self.initial_startup_delay)  # give the service some time to start

        if not self.isRunning():
            raise RuntimeError("Service failed to start.")


        delay = self.startup_delay_multiplier
        while True:
            if self.isReady():
                if self.kv_cache_save_path is not None:
                    self.restoreKVCache()

                self._postStartUp()

                elapsed_time = time.monotonic() - elapsed_time_reference
                print(f"{self.service_name} (PID: {self.service_process.pid}) started in {elapsed_time:.2f} seconds.")
                print(f"{self.service_name} is running on port {self.backend_port}.")

                return True


            # wait for the service to be ready
            time.sleep(delay)
            delay *= self.startup_delay_multiplier

    def backendURL(self) -> str:
        if not self.isRunning():
            raise RuntimeError("Service is not running.")

        return f"http://{self.host}:{self.backend_port}"

    def _modifyParameters(self, parameters: List) -> List:
        return parameters

    def _modifyEnvironment(self, env: Dict|None = None) -> Dict|None:
        return env

    def _postStartUp(self):
        pass

    def _preShutdown(self):
        pass

    def _getServiceBinaryPath(self) -> Path:
        if self.service_binary is None:
            raise RuntimeError("Service binary path is not set.")

        return self.service_binary

    def _getAttachedInstance(self) -> str:
        if self.attached_instance is None:
            raise RuntimeError("Attached instance is not set.")

        return self.attached_instance
