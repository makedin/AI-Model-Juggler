import json

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from typing import Dict, List

class AIBackendType(Enum):
    LLAMACPP = "llamacpp"
    KOBOLDCPP = "koboldcpp"
    STABLE_DIFFUSION_UI = "stable_diffusion_ui"

    def isInferenceBackend(self) -> bool:
        return self in (AIBackendType.LLAMACPP, AIBackendType.KOBOLDCPP)

    def isImageGenerationBackend(self) -> bool:
        return self == AIBackendType.STABLE_DIFFUSION_UI

@dataclass
class AIBackendConfig:
    type:   AIBackendType
    binary: Path

    def __init__(self, type: AIBackendType, **kwargs):
        self.type = type

        for key, value in kwargs.items():
            if key == 'binary':
                self.binary = Path(value)
            else:
                setattr(self, key, value)

@dataclass
class InferenceBackendConfig(AIBackendConfig):
    kv_cache_save_path: Path|None = None

@dataclass
class ImageGeneratorConfig(AIBackendConfig):
    pass

@dataclass
class BackendsConfig:
    llamacpp: InferenceBackendConfig|None = None
    koboldcpp: InferenceBackendConfig|None = None
    stable_diffusion_ui: ImageGeneratorConfig|None = None


    def __init__(self, config: Dict[str, Dict]):
        self.llamacpp = None
        self.koboldcpp = None
        self.stable_diffusion_ui = None

        for key in config.keys():
            if key not in AIBackendType:
                raise ValueError(f"Unknown backend type: {key}")

            backend_type = AIBackendType(key)

            if getattr(self, key) is not None:
                raise ValueError(f"Duplicate backend configuration for {key}")

            if backend_type.isInferenceBackend():
                backend = InferenceBackendConfig(backend_type, **config[key])
            elif backend_type.isImageGenerationBackend():
                backend = ImageGeneratorConfig(backend_type, **config[key])
            else:
                # not needed for now, but better not leave any footguns lying around
                raise ValueError(f"Unsupported backend type: {backend_type}")

            setattr(self, key, backend)




@dataclass
class AIModelConfig:
    type: AIBackendType
    name: str
    parameters: List
    kv_cache_saving: bool = True
    checkpoint_unloading: bool = True

@dataclass
class EndpointConfig:
    name: str
    path_prefix: str
    model: str
    strip_prefix: bool = False

    def __init__(self, name: str, path_prefix: str, model: str, strip_prefix: bool = False):
        self.name = name
        self.path_prefix = path_prefix
        self.model = model
        self.strip_prefix = strip_prefix



@dataclass
class ServerConfig:
    name: str
    host: str
    port: int
    endpoints: List[EndpointConfig]

    def __init__(self, name: str, host: str, port: int, endpoints: List[Dict]):
        self.name = name
        self.host = host
        self.port = port

        self.endpoints = []

        for endpoint_config in endpoints:
            endpoint = EndpointConfig(
                name=endpoint_config['name'],
                path_prefix=endpoint_config.get('path_prefix', ''),
                model=endpoint_config['model'],
                strip_prefix=endpoint_config.get('strip_prefix', False)
            )
            self.endpoints.append(endpoint)

@dataclass
class WarmupConfig:
    server: str
    endpoint: str

@dataclass
class Config:
    backends: BackendsConfig
    models: Dict[str, AIModelConfig]
    servers: Dict[str, ServerConfig]
    warmup: List[WarmupConfig]


config = None

def getConfig() -> Config:
    global config
    if config is None:
        config = loadConfig(None)

    return config

def loadConfig(path: Path|None) -> Config:
    global config

    if path is None:
        config_path = Path('config.json')
    elif path.is_dir():
        config_path = path / 'config.json'
    else:
        config_path = path


    with open(config_path, 'r') as file:
        config_data = json.load(file)

        backends_config = BackendsConfig(config_data['backends'])

        models_config = {}
        for name in config_data['models']:
            if name in models_config:
                raise ValueError(f"Duplicate model name: {name}")

            model_config_data = config_data['models'][name]
            backend_type_name = model_config_data['type']

            if backend_type_name not in AIBackendType:
                raise ValueError(f"Unknown backend type: {backend_type_name}")

            model_config = AIModelConfig(
                type=AIBackendType(backend_type_name),
                name=name,
                parameters=model_config_data.get('parameters', []),
                kv_cache_saving=model_config_data.get('kv_cache_saving', True),
                checkpoint_unloading=model_config_data.get('checkpoint_unloading', True)
            )

            models_config[name] = model_config

        servers_config = {}
        server_ports = set()
        for server_name in config_data['servers']:
            server = ServerConfig(server_name, **config_data['servers'][server_name])

            if server.port in server_ports:
                raise ValueError(f"Duplicate server port: {server.port}")

            servers_config[server.name] = server
            server_ports.add(server.port)

        warmup = []
        for warmup_config in config_data.get('warmup', []):
            warmup.append(WarmupConfig(
                server=warmup_config['server'],
                endpoint=warmup_config['endpoint']
            ))

        config = Config(
            backends=backends_config,
            models=models_config,
            servers=servers_config,
            warmup=warmup
        )

    return config
