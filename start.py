import argparse
from pathlib import Path

from src.main import serve

arg_parser = argparse.ArgumentParser(description="AI Model Juggler")
arg_parser.add_argument("--config", "-c", type=str, default="config.json", help="Path to the configuration file")
arguments = arg_parser.parse_args()


serve(Path(arguments.config))
