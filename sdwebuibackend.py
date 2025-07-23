import urllib.error, urllib.request

from typing import List

from aibackend import AIBackend

class SDWebUIBackend(AIBackend):
    def _modifyParameters(self, parameters: List = []) -> List:
            return parameters + ["--port", str(self.backend_port), '--nowebui']

    def isReady(self) -> bool:
        self.checkpoint_potentially_loaded = True
        if super().isReady():
            return True

        try:
            with urllib.request.urlopen(f'http://{self.host}:{self.backend_port}/sdapi/v1/memory') as response:
                if response.status == 200:
                    self.is_ready = True
                    self.checkpoint_potentially_loaded = True
                    return True

                return False

        except urllib.error.URLError as _:
            return False


    def _postStartup(self):
        self.checkpoint_potentially_loaded = True

    def unloadModel(self) -> bool:
        if not self.isRunning():
            return False

        if not self.checkpoint_potentially_loaded:
            return True

        try:
            request = urllib.request.Request(
                f'http://{self.host}:{self.backend_port}/sdapi/v1/unload-checkpoint',
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
