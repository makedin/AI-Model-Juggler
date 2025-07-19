import urllib.error, urllib.request

from aibackend import AIBackend
from config import AIBackendType, AIModelConfig, ImageGeneratorConfig

class Text2ImgBackend(AIBackend):
    def __init__(self, config: ImageGeneratorConfig, model: AIModelConfig, host: str):
        super().__init__(config, model, host)

        self.service_name = f"Image generator backend ({self.type.name.lower()}/{model.name})"

        self.checkpoint_potentially_loaded = True

        if self.type == AIBackendType.STABLE_DIFFUSION_UI:
            self.checkpoint_unloading = model.checkpoint_unloading

    def _extraPopenParameters(self) -> list:
        if self.type == AIBackendType.STABLE_DIFFUSION_UI:
            return ["--port", str(self.backend_port), '--nowebui']

        raise NotImplementedError(f"Service type {self.type} is not implemented.")

    def _stable_diffusion_ui_is_ready(self) -> bool:
        try:
            with urllib.request.urlopen(f'http://{self.host}:{self.backend_port}/sdapi/v1/memory') as response:
                if response.status == 200:
                    self.is_ready = True
                    self.checkpoint_potentially_loaded = True
                    return True
                return False

        except urllib.error.URLError as _:
            return False


    def isReady(self) -> bool:
        if super().isReady():
            return True

        if self.type == AIBackendType.STABLE_DIFFUSION_UI:
            return self._stable_diffusion_ui_is_ready()
            
        raise NotImplementedError(f"Service type {self.type} is not implemented.")

    def unloadModel(self) -> bool:
        if not self.isRunning():
            return False

        if not self.checkpoint_potentially_loaded:
            return True

        if self.type == AIBackendType.STABLE_DIFFUSION_UI:
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

        raise NotImplementedError(f"Service type {self.type} is not implemented.")

    def stopService(self, force: bool = False):
        if not self.isRunning():
            return

        if self.checkpoint_unloading and not force:
            self.unloadModel()
            return

        self.shutdown()
