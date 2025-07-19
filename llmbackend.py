import json
import urllib.error, urllib.request

from pathlib import Path

from aibackend import AIBackend
from config import AIBackendType, AIModelConfig, InferenceBackendConfig

class LLMBackend(AIBackend):
    def __init__(self, config: InferenceBackendConfig, model: AIModelConfig, host: str):
        super().__init__(config, model, host)

        self.service_name = f"LLM backend ({config.type.name.lower()}/{model.name})"

        if self.type == AIBackendType.LLAMACPP:
            self.kv_cache_save_path = config.kv_cache_save_path
            if self.kv_cache_save_path is not None:
                # create the kv cache save path if it doesn't exist
                if not Path(self.kv_cache_save_path).exists():
                    Path(self.kv_cache_save_path).mkdir(parents=True, exist_ok=True)


            self.kv_cache_save_file_name = f"kv_cache-{host}-{model.name.lower}.bin"

        self.kv_cache_saved = False



    def _extraPopenParameters(self) -> list:
        if self.type == AIBackendType.LLAMACPP:
            parameters = ["--port", str(self.backend_port)]
            if self.kv_cache_save_path is not None:
                parameters += ["--slot-save-path", str(self.kv_cache_save_path)]
            return parameters

        raise NotImplementedError(f"Service type {self.type} is not implemented.")


    def _llamacpp_is_ready(self) -> bool:
        # just to appeace MyPy
        assert self.backend_port is not None, "Process port is not set."

        try:
            with urllib.request.urlopen(f'http://localhost:{self.backend_port}/health') as response:
                if response.status == 200:
                    self.is_ready = True
                    return True
                return False

        # we'll assume that the server is not ready if we can't connect to it
        except urllib.error.URLError as _:
            return False


    def isReady(self) -> bool:
        if super().isReady():
            return True

        if self.type == AIBackendType.LLAMACPP:
            return self._llamacpp_is_ready()

        raise NotImplementedError(f"Service type {self.type} is not implemented.")


    def saveKVCache(self) -> bool:
        if not self.isRunning():
            return False

        if self.type == AIBackendType.LLAMACPP:
            try:
                data = json.dumps({"filename": self.kv_cache_save_file_name}).encode('utf-8')
                request = urllib.request.Request(
                    f'http://{self.host}:{self.backend_port}/slots/0?action=save',
                    method='POST',
                    data=data
                )
                with urllib.request.urlopen(request) as response:
                    if response.status == 200:
                        print(f"{self.service_name} KV cache saved successfully.")
                        self.kv_cache_saved = True
                        return True

                    return False
            except urllib.error.URLError as _:
                return False

        raise NotImplementedError(f"Service type {self.type} is not implemented.")

    def restoreKVCache(self) -> bool:
        if not self.isRunning():
            return False

        if not self.kv_cache_saved:
            return False

        if self.type == AIBackendType.LLAMACPP:
            try:
                data = json.dumps({"filename": self.kv_cache_save_file_name}).encode('utf-8')
                request = urllib.request.Request(
                    f'http://{self.host}:{self.backend_port}/slots/0?action=restore',
                    method='POST',
                    data=data
                )
                with urllib.request.urlopen(request) as response:
                    if response.status == 200:
                        print(f"{self.service_name} KV cache restored successfully.")
                        return True

                    return False
            except urllib.error.URLError as _:
                return False

        raise NotImplementedError(f"Service type {self.type} is not implemented.")

    def _postStartUp(self):
        """
        Override this method in subclasses to perform additional actions after the service has started.
        """
        if self.type == AIBackendType.LLAMACPP:
            # try to restore the KV cache if it exists
            if self.kv_cache_saved:
                self.restoreKVCache()
            else:
                print(f"{self.service_name} KV cache not saved. Skipping restore.")

    def _preShutdown(self):
        """
        Override this method in subclasses to perform additional actions before the service is stopped.
        """
        if self.type == AIBackendType.LLAMACPP:
            # save the KV cache before shutting down
            if self.kv_cache_save_path is not None:
                self.saveKVCache()
            else:
                print(f"{self.service_name} KV cache save path is not set. Skipping saving.")
