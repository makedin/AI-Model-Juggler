import urllib.error, urllib.request

from typing import List

from aibackend import AIBackend

class SDWebUIBackend(AIBackend):
    def _modifyParameters(self, parameters: List = []) -> List:
            return parameters + ["--port", str(self.backend_port), '--nowebui']

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

    def _apiBaseURL(self, force_attached_instance: bool = False) -> str:
        if self.attached_instance is not None and (self.isAttached() or force_attached_instance):
            backend_url = self.attached_instance
        else:
            backend_url = self.backendURL()

        return f'{backend_url}/sdapi/v1'

    def _testBackendAPI(self, force_attached_instance: bool = False) -> bool:
        try:
            with urllib.request.urlopen(f'{self._apiBaseURL(force_attached_instance)}/memory') as response:
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
            request = urllib.request.Request(
                f'http://{self._apiBaseURL()}/unload-checkpoint',
                method='POST'
            )
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
