import json

from dataclasses import dataclass
from pathlib import Path

from typing import Dict, List

@dataclass
class AIBackendConfig:
    type:   str
    binary: Path|None
    attached_instance: str|None

    default_parameters: List
    model_unloading: bool

    def __init__(self,
                 type: str,
                 binary: str|Path|None = None,
                 attach_to: str|None = None,
                 default_parameters: List|None = None,
                 model_unloading: bool = True):

        from .aibackendmanager import getBackendClass
        backend_class = getBackendClass(type)

        if not backend_class.supports_attaching_to_running_instance:
            if attach_to is not None:
                raise ValueError(f"Backend type {type} does not support attaching to a running instance.")
            if binary is None:
                raise ValueError(f"Backend type {type} requires a binary path.")

        if not backend_class.supports_executing_directly:
            if binary is not None:
                raise ValueError(f"Backend type {type} does not support executing directly.")
            if attach_to is None:
                raise ValueError(f"Backend type {type} requires a running instance to attach to.")

        if binary is None and attach_to is None:
            raise ValueError(f"Backend type {type} requires either a binary path or a running instance to attach to.")


        self.type = type
        self.binary = Path(binary) if binary is not None else None
        self.attached_instance = attach_to if backend_class.supports_attaching_to_running_instance else None
        self.default_parameters = default_parameters if default_parameters is not None else []
        self.model_unloading = backend_class.supports_model_unloading and model_unloading

@dataclass
class EndpointConfig:
    name: str
    backend: str
    parameters: List

    path_prefix: str = ""
    strip_prefix: bool = True

    kv_cache_saving: bool = True

    def __init__(self, name: str, backend: str, path_prefix: str, strip_prefix: bool = False, parameters: List|None = None, kv_cache_saving: bool = True):
        from .aibackendmanager import getBackendClass

        self.name = name
        self.backend = backend
        self.path_prefix = path_prefix
        self.strip_prefix = strip_prefix
        self.parameters = parameters if parameters is not None else []
        self.kv_cache_saving = kv_cache_saving if getBackendClass(backend).supports_kv_cache_restoring else False


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
                backend=endpoint_config['backend'],
                path_prefix=endpoint_config.get('path_prefix', ''),
                strip_prefix=endpoint_config.get('strip_prefix', False),
                parameters=endpoint_config.get('parameters', []),
                kv_cache_saving=endpoint_config.get('kv_cache_saving', True)
            )
            self.endpoints.append(endpoint)

@dataclass
class WarmupConfig:
    server: str
    endpoint: str

@dataclass
class Config:
    temp_dir: Path
    backends: Dict[str, AIBackendConfig]
    servers:  List[ServerConfig]
    warmup:   List[WarmupConfig]


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

        backends: Dict[str, AIBackendConfig] = {}
        for name, backend_conf in config_data.get('backends').items():
            if name in backends:
                raise ValueError(f"Duplicate backend configuration for {name}")

            backends[name] = AIBackendConfig(name, **backend_conf)

        servers_config = []
        server_ports = set()
        for server_config in config_data['servers']:
            server = ServerConfig(**server_config)

            if server.port in server_ports:
                raise ValueError(f"Duplicate server port: {server.port}")

            servers_config.append(server)
            server_ports.add(server.port)

        warmup = []
        for warmup_config in config_data.get('warmup', []):
            warmup.append(WarmupConfig(
                server=warmup_config['server'],
                endpoint=warmup_config['endpoint']
            ))

        temp_dir = config_data.get('temp_dir', None)
        if temp_dir is None:
            if Path('/tmp').exists():
                temp_dir = Path('/tmp/ai-model-juggler')
            else:
                temp_dir = Path('ai-model-juggler').absolute()
        else:
            temp_dir = Path(temp_dir).absolute()

        config = Config(
            temp_dir=temp_dir,
            backends=backends,
            servers=servers_config,
            warmup=warmup
        )

    return config
