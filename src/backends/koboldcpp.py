import argparse
import json
import urllib.request, urllib.error

from pathlib import Path
from time import time
from typing import List

from ..aibackend import AIBackend
from ..config import getConfig

class Koboldcpp(AIBackend):
    supports_executing_directly = True

    def _modifyParameters(self, parameters: List) -> List:

        parser = argparse.ArgumentParser()
        parser.add_argument("--config", type=str)
        parser.add_argument("--port", type=int)
        parser.add_argument("--launch", action='store_true')
        parser.add_argument("--showgui", action='store_true')

        arguments, rest = parser.parse_known_args(parameters)

        # --config overrides all other parameters
        if arguments.config is not None:
            config_path = Path(arguments.config)

            if not config_path.is_file():
                raise FileNotFoundError(f"koboldcpp config file '{arguments.config}' does not exist.")

            with open(config_path, 'r') as file:
                config_data = json.load(file)

                config_data['port'] = self.backend_port
                config_data['port_param'] = self.backend_port
                config_data['showgui'] = False
                config_data['launch'] = False

            temp_config_path = getConfig().temp_dir / f'{config_path.name}_{int(time())}.{config_path.suffix}'
            with open(temp_config_path, 'w') as file:
                json.dump(config_data, file)

            return ["--config", str(temp_config_path)]

        modified_parameters = rest + ["--port", str(self.backend_port)]

        return modified_parameters

    def isReady(self) -> bool:
        if super().isReady():
            return True

        try:
            with urllib.request.urlopen(f'http://localhost:{self.backend_port}/api/v1/info/version') as response:
                if response.status == 200:
                    self.is_ready = True
                    return True
                return False

        # we'll assume that the server is not ready if we can't connect to it
        except urllib.error.URLError as _:
            return False
