from typing import Dict, Literal, Type

from .aibackend import AIBackend

class AIBackendManager:
    def __init__(self):
        self._backends: Dict[str, AIBackend] = {}

    def addBackend(self, backend: AIBackend, server: str, endpoint: str):
        self._backends[f"{server}:{endpoint}"] = backend


    def stopBackend(self, server_endpoint: str):
        if server_endpoint in self._backends:
            backend = self._backends[server_endpoint]
            backend.stopService()

    def getBackend(self, server_endpoint: str) -> AIBackend|Literal[False]:
        if server_endpoint in self._backends:
            self.stopAllBackends(exclude=[server_endpoint])
            model = self._backends[server_endpoint]
            if model.readyService():
                return model
            else:
                return False

        raise ValueError(f"Backend for server:endpoint '{server_endpoint}' not found.")

    def stopAllBackends(self, exclude: list[str] = []):
        for server_endpoint, backend in self._backends.items():
            if server_endpoint not in exclude:
                backend.stopService()

_backend_manager = AIBackendManager()

def getBackendManager() -> AIBackendManager:
    global _backend_manager
    return _backend_manager


backends: Dict[str, Type[AIBackend]] = {}

def getBackendClass(name: str) -> Type[AIBackend]:
    import importlib
    import inspect

    global backends

    if name in backends:
        return backends[name]

    module = importlib.import_module(f".backends.{name}", package="src")
    classes = inspect.getmembers(module, inspect.isclass)
    for _, cls in classes:
        if issubclass(cls, AIBackend) and cls is not AIBackend:
            backends[name] = cls
            return cls

    raise ValueError(f"No Backend class found for '{name}'")
