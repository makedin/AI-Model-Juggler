import http.server
import socketserver

from typing import Tuple

from .aibackendmanager import getBackendManager
from .config import getConfig, ServerConfig


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
                backend = getBackendManager().getBackend(f"{self.server_name}:{endpoint.name}")

                if endpoint.strip_prefix:
                    path = self.path[len(endpoint.path_prefix):]
                break

        if backend is None:
            self.send_error(404, "Endpoint not found")
            print (f'{self.host}:{self.port}: endpoint not found for path "{self.path}"')
            return

        if backend is False:
            print (f'{self.host}:{self.port}: backend for "{endpoint.name}" could not be started.')
            self.send_error(503, "Backend not available", "Backend could not be started")
            return

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

