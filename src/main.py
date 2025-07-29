import threading

from pathlib import Path

from .aibackendmanager import getBackendClass, getBackendManager
from .config import loadConfig
from .server import AIAPIHandler, run_server


def serve(configuration_file: Path):
    config = loadConfig(configuration_file)

    ai_backend_manager = getBackendManager()

    handler_threads = []

    for server_config in config.servers:
        for endpoint in server_config.endpoints:
            backend_config = config.backends[endpoint.backend]

            backend_class = getBackendClass(endpoint.backend)
            backend = backend_class(backend_config, server_config, endpoint)

            ai_backend_manager.addBackend(backend, server_config.name, endpoint.name)

        handler_threads.append(threading.Thread(target=run_server, args=(AIAPIHandler, server_config)))


    print(f"Starting {len(handler_threads)} server threads...")
    for thread in handler_threads:
        thread.start()

    if len(config.warmup) > 0:
        print(f"Warming up {len(config.warmup)} backends...")

        for warmup_config in config.warmup:
            server_config = None
            for server in config.servers:
                if server.name == warmup_config.server:
                    server_config = server
                    break

            assert server_config is not None, f"Server {warmup_config.server} not found in configuration"

            endpoint_config = None
            for endpoint in server_config.endpoints:
                if endpoint.name == warmup_config.endpoint:
                    endpoint_config = endpoint
                    break

            assert endpoint_config is not None, f"Endpoint {warmup_config.endpoint} not found in server {server_config.name}"

            ai_backend_manager.getBackend(f"{server_config.name}:{endpoint_config.name}")
