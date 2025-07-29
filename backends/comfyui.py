import json
import urllib.error, urllib.request

from typing import List

from aibackend import AIBackend

class ComfyUI(AIBackend):
    supports_attaching_to_running_instance = True
    supports_model_unloading               = True


    def _modifyParameters(self, parameters: List = []) -> List:
            return parameters + ["--port", str(self.backend_port)]

    def attachInstance(self) -> bool:
        if self.attached_instance is None:
            raise RuntimeError(f"{self.service_name} is not configured to attach to a running instance.")

        if self._testBackendAPI(True):
            self._is_attached = True
            self.checkpoint_potentially_loaded = True
            print(f"Attached to {self.attached_instance}.")
            return True

        print(f"Failed to attach to {self.attached_instance}. The backend API is not responding.")
        return False

    def isReady(self) -> bool:
        self.checkpoint_potentially_loaded = True
        if super().isReady():
            return True

        return self._testBackendAPI()

    def _postStartup(self):
        self.checkpoint_potentially_loaded = True

    def _testBackendAPI(self, force_attached: bool = False) -> bool:
        try:
            backend_url = self.attached_instance if force_attached else self.backendURL()
            with urllib.request.urlopen(f'{backend_url}/system_stats') as response:
                if response.status == 200:
                    self.is_ready = True
                    self.checkpoint_potentially_loaded = True
                    return True

                return False

        except urllib.error.URLError as _:
            return False


    def unloadModel(self) -> bool:
        if not self.isAttached() and self.isRunning():
            return False

        if not self.checkpoint_potentially_loaded:
            return True

        try:
            data = json.dumps({"unload_models": True}).encode('utf-8')
            request = urllib.request.Request(
                f'http://{self.backendURL()}/free',
                method='POST',
                data=data,
            )
            request.add_header('Content-Type', 'application/json')
            with urllib.request.urlopen(request) as response:
                if response.status == 200:
                    print(f"{self.service_name} checkpoint unloaded successfully.")
                    self.checkpoint_potentially_loaded = False
                    return True

                return False
        except urllib.error.URLError as _:
            return False

    def backendURL(self) -> str:
        if self.isAttached():
            assert self.attached_instance is not None, "Attached instance cannot be None (MyPy...)"
            return self.attached_instance

        return super().backendURL()
