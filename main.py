import http.server
import socketserver
import threading
from typing import Tuple

from aibackendmanager import AIBackendManager
from llmbackend import LLMBackend
from text2imgbackend import Text2ImgBackend
from config import getConfig, ServerConfig

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

        for server_config in config.servers.values():
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
                backend = ai_backend_manager.getBackend(f"{self.port}:{endpoint.model}")

                if endpoint.strip_prefix:
                    path = self.path[len(endpoint.path_prefix):]
                break

        assert backend is not None, f"No backend found for path: {self.path}"

        server_api_path = f"http://{backend.host}:{backend.backend_port}"

        self.send_response(307)
        self.send_header('Location', f"{server_api_path}{path}")
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



config = getConfig()
ai_backend_manager = AIBackendManager()

handler_threads = []

for server_name in config.servers:
    server_config = config.servers[server_name]

    for endpoint in server_config.endpoints:
        model = config.models[endpoint.model]

        backend_config = getattr(config.backends, model.type.name.lower())

        if model.type.isInferenceBackend():
            backend = LLMBackend(backend_config, model, server_config.host)
        elif model.type.isImageGenerationBackend():
            backend = Text2ImgBackend(backend_config, model, server_config.host)
        else:
            # again, this is here in case we add more backend types in the future
            raise ValueError(f"Unsupported model type: {model.type}")

        ai_backend_manager.addBackend(backend, server_config.port)

    handler_threads.append(threading.Thread(target=run_server, args=(AIAPIHandler, server_config)))


print(f"Starting {len(handler_threads)} server threads...")
for thread in handler_threads:
    thread.start()

if len(config.warmup) > 0:
    print(f"Warming up {len(config.warmup)} backends...")

    for warmup_config in config.warmup:
        server_config = config.servers[warmup_config.server]
        endpoint_path_prefix = None
        endpoint_config = None
        for endpoint in server_config.endpoints:
            if endpoint.name == warmup_config.endpoint:
                endpoint_config = endpoint
                endpoint_path_prefix = endpoint.path_prefix
                break

        assert endpoint_config is not None, f"Endpoint {warmup_config.endpoint} not found in server {server_config.name}"

        ai_backend_manager.getBackend(f"{server_config.port}:{endpoint_config.model}")
