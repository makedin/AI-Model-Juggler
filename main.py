import argparse
import http.server
import socketserver
import threading

from pathlib import Path
from typing import Tuple

from aibackendmanager import AIBackendManager
from config import loadConfig, getConfig, ServerConfig, AIBackendType

from backends.llamacpp import LLamaCPPBackend
from backends.sdwebui import SDWebUIBackend

class AIAPIHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.prepared = False
        super().__init__(*args, **kwargs)

    def prepare(self):
        if self.prepared:
            return

        server_address: Tuple[str, int] = self.server.server_address
        self.host = server_address[0]
        self.port = server_address[1]

        config = getConfig()

        for server_config in config.servers:
            if server_config.port == self.port:
                self.server_name = server_config.name
                self.endpoints = server_config.endpoints
                break

    def handle_request(self):
        global ai_backend_manager
        self.prepare()

        backend = None
        path = self.path
        for endpoint in self.endpoints:
            if endpoint.path_prefix == '' or self.path.startswith(endpoint.path_prefix):
                backend = ai_backend_manager.getBackend(f"{self.server_name}:{endpoint.name}")

                if endpoint.strip_prefix:
                    path = self.path[len(endpoint.path_prefix):]
                break

        assert backend is not None, f"No backend found for path: {self.path}"

        backend_url = backend.backendURL()

        self.send_response(307)
        self.send_header('Location', f"{backend_url}{path}")
        self.end_headers()

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_HEAD(self):
        self.handle_request()

    def do_OPTIONS(self):
        self.handle_request()

def run_server(handler_class, config: ServerConfig):
    with socketserver.ThreadingTCPServer((config.host, config.port), handler_class) as httpd:
        print(f"Server \"{config.name}\" running on {config.host}:{config.port}")
        httpd.serve_forever()


arg_parser = argparse.ArgumentParser(description="AI Model Juggler")
arg_parser.add_argument("--config", "-c", type=str, default="config.json", help="Path to the configuration file")
arguments = arg_parser.parse_args()

config = loadConfig(Path(arguments.config))

ai_backend_manager = AIBackendManager()

backend_classes = {
    AIBackendType.LLAMACPP: "LLamaCPPBackend",
    AIBackendType.SDWEBUI: "SDWebUIBackend",
}

handler_threads = []

for server_config in config.servers:
    for endpoint in server_config.endpoints:
        backend_config = getattr(config.backends, endpoint.backend.name.lower())

        class_name = backend_classes.get(endpoint.backend)
        assert class_name is not None, f"Unsupported backend type: {endpoint.backend}"

        backend = globals()[class_name](backend_config, server_config.host, endpoint)

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

        endpoint_path_prefix = None
        endpoint_config = None
        for endpoint in server_config.endpoints:
            if endpoint.name == warmup_config.endpoint:
                endpoint_config = endpoint
                endpoint_path_prefix = endpoint.path_prefix
                break

        assert endpoint_config is not None, f"Endpoint {warmup_config.endpoint} not found in server {server_config.name}"

        ai_backend_manager.getBackend(f"{server_config.name}:{endpoint_config.name}")
