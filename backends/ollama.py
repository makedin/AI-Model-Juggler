import json
import urllib.error, urllib.request

from os import environ
from typing import Dict, List

from aibackend import AIBackend

class Ollama(AIBackend):
    def attachInstance(self) -> bool:
        if self.attached_instance is None:
            raise RuntimeError(f"{self.service_name} is not configured to attach to a running instance.")

        if self._testBackendAPI(True):
            self.is_attached = True
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

        return f'{backend_url}/api'

    def _testBackendAPI(self, force_attached_instance: bool = False) -> bool:
        try:
            with urllib.request.urlopen(f'{self._apiBaseURL(force_attached_instance)}/version') as response:
                if response.status == 200:
                    self.is_ready = True
                    self.checkpoint_potentially_loaded = True
                    return True

                return False

        except urllib.error.URLError as _:
            return False


    def unloadModel(self) -> bool:
        if not self.isAttached() and not self.isRunning():
            return False

        if not self.checkpoint_potentially_loaded:
            return True

        try:
            models = []
            with urllib.request.urlopen(f'{self._apiBaseURL()}/ps') as response:
                if response.status != 200:
                    return False

                models = json.loads(response.read().decode('utf-8'))['models']

            for model in models:
                model_name = model['name']

                request = urllib.request.Request(
                    f'{self._apiBaseURL()}/generate',
                    method='POST',
                    headers={'Content-Type': 'application/json'},
                    data=json.dumps({
                        'model': model_name,
                        'keep_alive': 0,
                    }).encode('utf-8')
                )

                with urllib.request.urlopen(request) as response:
                    if response.status != 200:
                        print(f"Failed to unload model {model_name}.")
                        return False

        except urllib.error.URLError as _:
            return False

                      
        self.checkpoint_potentially_loaded = False
        print(f"{self.service_name} models unloaded.")
        return True

    def _modifyParameters(self, parameters: List = []) -> List:
            return ['serve'] + parameters

    def _modifyEnvironment(self, env: Dict|None = None) -> Dict|None:
        if env is None:
            env = environ.copy()

        env['OLLAMA_HOST'] = f"{self.host}:{self.backend_port}"

        return env

          
    def backendURL(self) -> str:
        if self.isAttached():
            assert self.attached_instance is not None, "Attached instance cannot be None (MyPy...)"
            return self.attached_instance

        return super().backendURL()
