from aibackend import AIBackend

class AIBackendManager:
    def __init__(self):
        self._backends = {}

    def addBackend(self, backend: AIBackend, port: int):
        self._backends[f"{port}:{backend.model_name}"] = backend


    def stopBackend(self, model_name: str):
        if model_name in self._backends:
            backend = self._backends[model_name]
            backend.stopService()

    def getBackend(self, model_name: str) -> AIBackend:
        if model_name in self._backends:
            self.stopAllBackends(exclude=[model_name])
            model = self._backends[model_name]
            model.startService()
            return model

        raise ValueError(f"Backend for model '{model_name}' not found.")


    def stopAllBackends(self, exclude: list[str] = []):
        for model_name, backend in self._backends.items():
            if model_name not in exclude:
                backend.stopService()
