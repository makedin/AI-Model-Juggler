# AI Model Juggler

Ai Model Juggler exposes HTTP endpoints associated with different AI backends and spins those backends up and down transparently. This way multiple models can be run "simultaneously" even if they don't fit in the available VRAM.

## Supported backends

The following backends are currently supported:
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
  - Support KV cache saving and restoring
- [Stable Diffusion web UI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) / [Stable Diffusion WebUI Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)
  - Supports model unloading (without killing the backend server)
  - Supports attaching to a running server (the server must be started with ```--nowebgui``` or ```--api```)
- [koboldcpp](https://github.com/LostRuins/koboldcpp)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
  - Supports model unloading
  - Supports attaching to a running server
  - ! Cannot be started by AI Model Juggler (yet), must be attached to an already running instance

AI Model Juggler is AGI agnostic and does not impose limitations on using the backends through their HTTP APIs.

## Performance

AI Model Juggler performs a couple of tricks to speed things up to make things more transparent. With compatible backends, it supports model unloading, which allows an inactive backend to remain running while still releasing all most of the VRAM. In some cases, this speeds up the start of generation considerably. It also supports llama.cpp's KV cache saving and restoring to save on prompt processing time. Both features are optional, and can be disabled if desired.

It is recommended to store the model files on fast storage. RAM disk is preferred, but a fast NVMe SSD should be perfectly satisfactory. Anything much slower might cause backend start up times to grow to a point where the process is no longer completely transparent to the user.

## Installation and platform support

AI Model Juggler is a Python program with no dependencies outside the standard library. There is no need to set up a virtual environment or to install any extra packages.

The code is supposed to be OS agnostic and compatible with any currently maintained Python version, but has only been tested with Python 3.13 on Linux.

## Usage

The program requires a configuration file called ```config.json``` to be present. Editing the configuration is the only way to affect the behavior of the program. Once the configuration file has been set up, simply run ```python main.py```. Alternatively, the program may be run with a command line argument ```--config <file>``` to make it use a different configuration.

Example config.json:
```json
{
    "temp_dir": "/tmp/ai-model-juggler/",
    "backends": {
        "llamacpp": {
            "binary": "/path/to/llama.cpp/build/bin/llama-server",
            "default_parameters": [
                "-ngl", "99",
                "--no-mmap",
                "-fa"
            ],
            "host": "localhost"
        },
        "sdwebui": {
            "attach_to": "http://localhost:7860",
            "binary": "/path/to/stable-diffusion-webui-forge/webui.sh",
            "model_unloading": true
        },
        "koboldcpp": {
            "binary": "/path/to/koboldcpp-linux-x64"
        },
        "comfyui": {
            "attach_to": "http://localhost:8188",
            "model_unloading": true
        },
        "ollama": {
            "attach_to": "http://localhost:11434",
            "binary": "/path/to/ollama",
        }
    },
    "servers": [
        {
            "name": "LLM",
            "host": "localhost",
            "port": 8021,
            "endpoints": [
                {
                    "name": "Vision LLM",
                    "path_prefix": "/vision",
                    "strip_prefix": true,

                    "backend": "llamacpp",
                    "parameters": [
                        "-m", "/path/to/Mistral-Small-3.2-24B-Instruct-2506-Q5_K_M.gguf",
                        "--mmproj", "/path/to/mistral-small-3.2-mmproj-f16.gguf",
                        "--ctx-size", "16384"
                    ],
                    "kv_cache_saving": false
                },
                {
                    "name": "Qwen 3 MoE",
                    "path_prefix": "/qwen3",
                    "strip_prefix": true,

                    "backend": "koboldcpp",
                    "parameters": [
                        "--config", "/path/to/Qwen3-30B-A3B-Q4_K_M.kcpps"
                    ]
                },
                {
                    "name": "Ollama",
                    "path_prefix": "/ollama",
                    "strip_prefix": true,
                    "backend": "ollama"
                },
                {
                    "name": "Default LLM",
                    "backend": "llamacpp",
                    "parameters": [
                        "-m", "/path/to/google_gemma-3-27b-it-Q5_K_M.gguf",
                        "--ctx-size", "32768"
                    ]
                }
            ]
        },
        {
            "name": "Image generation",
            "host": "localhost",
            "port": 8022,
            "endpoints": [
            {
                "name": "Stable Diffusion",
                "path_prefix": "/sdapi",
                "backend": "sdwebui",
                "strip_prefix": false,
            },
            {
                "name": "ComfyUI",
                "path_prefix": "",
                "backend": "comfyui"
            }
            ]
        }
    ],
    "warmup": [
        {
            "server": "Image generation",
            "endpoint": "Stable Diffusion"
        },
        {
            "server": "LLM",
            "endpoint": "Vision LLM"
        }
    ]
}
```

The example configuration defines two servers, one listening on ```locahost:8081``` and the other on ```localhost:8082```.

Calls to ```localhost:8081``` with the path starting with ```/vision``` (like ```http://localhost:8081/vision/health```) will go to llama.cpp running a vision capable Mistral Small 3.2, with the path prefix removed (so ```/vision/health``` becomes ```/health```). Calls with the path prefix ```/qwen3``` will be handled by a koboldcpp server running the Qwen3-30B-A3B, again with the prefix stripped. Finally, calls with neither prefix will be handled by a llama.cpp server running Gemma 3 27B.

Calls to ```http://localhost:8082/sdapi``` will be routed to a Stable Diffusion WebUI Forge server. Not that the ```/sdapi``` prefix is not stripped, as it belongs to the actual calls to the API. Calls to ```http://localhost:8082``` without the path prefix will go to a ComfyUI server.

The ```warmup``` section specifies that first, Stable Diffusion WebUI Forge is started, and then the vision capable LLM inference backend. As the image generation backend supports model unloading and the feature is enabled (by default, in fact), the backend will not shut down when the LLM backend is spun up, considerably speeding up the first image generation.

The Stable Diffusion WebUI Forge backend will first try to attach to a running instance of the service, available at ```http://localhost:7860```. If the service is not running, a new instance will be started.

## Limitations

The project is in a barely working shape. It has very limited support for backends, though adding new ones should be rather simple. There is also very little graceful error handling. Sending multiple requests too rapidly (before the previous one has finished processing) could cause weird issues. There is no user interface of any sort, unless you count the configuration file, and some logging which you shouldn't.

AI Model Juggler is not a real proxy (not yet, anyway). It simply starts up the requested backend and responds with a 307 redirect to the newly running server. This makes it ill suited for using the llama.cpp's built in web UI.

## Comparison to other projects

The closest alternative is probably [llama-swap](https://github.com/mostlygeek/llama-swap), which promises to do much the same thing as AI Model Juggler, and more besides. However, it seems to be limited to working with backends that support the OpenAI API, meaning that it probably does not work with Stable Diffusion web UI, at least not without some trickery. Other than that, it is probably superior in every regard.
