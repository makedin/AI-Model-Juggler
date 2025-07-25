import json
import urllib.request, urllib.error

from pathlib import Path
from typing import List

from aibackend import AIBackend
from config import AIBackendConfig, EndpointConfig

class LLamaCPPBackend(AIBackend):
    def __init__(self, config: AIBackendConfig, server: str, endpoint: EndpointConfig):
        super().__init__(config, server, endpoint)

        if self.kv_cache_save_path is not None:
            # create the kv cache save path if it doesn't exist
            if not Path(self.kv_cache_save_path).exists():
                Path(self.kv_cache_save_path).mkdir(parents=True, exist_ok=True)

            self.kv_cache_save_file_name = f"kv_cache-{server}-{endpoint.name}.bin"

        self.kv_cache_saved = False

    def _modifyParameters(self, parameters: List) -> List:
        modified_parameters = parameters + ["--port", str(self.backend_port)]
        if self.kv_cache_save_path is not None:
            modified_parameters += ["--slot-save-path", str(self.kv_cache_save_path)]

        return modified_parameters


    def isReady(self) -> bool:
        if super().isReady():
            return True

        try:
            with urllib.request.urlopen(f'http://localhost:{self.backend_port}/health') as response:
                if response.status == 200:
                    self.is_ready = True
                    return True
                return False

        # we'll assume that the server is not ready if we can't connect to it
        except urllib.error.URLError as _:
            return False


    def saveKVCache(self) -> bool:
        if not self.isRunning():
            return False

        if self.kv_cache_save_path is None:
            print(f"{self.service_name} KV cache save path is not set. Skipping saving.")
            return False

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


    def restoreKVCache(self) -> bool:
        if not self.isRunning():
            return False

        if not self.kv_cache_saved:
            print(f"{self.service_name} KV cache not saved. Skipping restore.")
            return False

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
