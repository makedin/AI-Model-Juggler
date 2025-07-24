from typing import Dict
from aibackend import AIBackend

class AIBackendManager:
    def __init__(self):
        self._backends: Dict[str, AIBackend] = {}

    def addBackend(self, backend: AIBackend, server: str, endpoint: str):
        self._backends[f"{server}:{endpoint}"] = backend


    def stopBackend(self, server_endpoint: str):
        if server_endpoint in self._backends:
            backend = self._backends[server_endpoint]
            backend.stopService()

    def getBackend(self, server_endpoint: str) -> AIBackend:
        if server_endpoint in self._backends:
            self.stopAllBackends(exclude=[server_endpoint])
            model = self._backends[server_endpoint]
            model.readyService()
            return model

        raise ValueError(f"Backend for server:endpoint '{server_endpoint}' not found.")

    def stopAllBackends(self, exclude: list[str] = []):
        for server_endpoint, backend in self._backends.items():
            if server_endpoint not in exclude:
                backend.stopService()
