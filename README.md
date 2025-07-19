# AI Model Juggler

Ai Model Juggler exposes HTTP endpoints associated with different AI backends ([llama.cpp](https://github.com/ggml-org/llama.cpp) and [Stable Diffusion web UI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) / [Stable Diffusion WebUI Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge) are currently supported) and spins those backends up and down transparently. This way multiple models can be run "simultaneously" even if they don't fit in the available VRAM.

## Performance

AI Model Juggler performs a couple of tricks to speed things up to make things more transparent. It allows you to keep the image generation backend running while only unloading the checkpoint. This consumes a little VRAM (200 – 300 MB) but allows the generation to start up a lot faster. It also supports llama.cpp's KV cache saving and restoring to save on prompt processing time. Both features are optional, and can be disabled if desired.

It is recommended to store the model files on fast storage. RAM disk is preferred, but a fast NVMe SSD should be perfectly satisfactory. Anything much slower might cause backend start up times to grow to a point where the process is no longer completely transparent to the user.

## Installation and platform support

AI Model Juggler is a Python program with no dependencies outside the standard library. There is no need to set up a virtual environment or to install any extra packages.

The code is supposed to be OS agnostic and compatible with any currently maintained Python version, but has only been tested with Python 3.13 on Linux.

## Usage

The program requires a configuration file called ```config.json``` to be present. Editing the configuration is the only way to affect the behavior of the program. Once the configuration file has been set up, simply run ```python main.py```.

Example config.json:
```json
{
    "backends": {
        "llamacpp": {
            "binary": "/path/to/llama.cpp/build/bin/llama-server",
            "kv_cache_save_path": "/tmp/llama_kv_cache"
        },
        "stable_diffusion_ui": {
            "binary": "/path/to/stable-diffusion-webui-forge/webui.sh"
        }
    },
    "models": {
        "gemma": {
            "type": "llamacpp",
            "parameters": [
                "-m", "/path/to/google_gemma-3-27b-it-Q5_K_M.gguf",
                "--no-mmap",
                "--ctx-size", "16384",
                "-ngl", "99",
                "-fa"
            ],
            "kv_cache_saving": true
        },
        "vision": {
            "type": "llamacpp",
            "parameters": [
                "-m", "/path/to/Mistral-Small-3.2-24B-Instruct-2506-Q5_K_M.gguf",
                "--mmproj", "/path/to/mistral-small-3.2-mmproj-f16.gguf",
                "--no-mmap",
                "--ctx-size", "16384",
                "-ngl", "99",
                "-fa"
            ]
        },
        "sdxl": {
            "type": "stable_diffusion_ui",
            "checkpoint_unloading": true
        }
    },
    "servers": {
        "LLM": {
            "host": "localhost",
            "port": 8021,
            "endpoints": [
                {
                    "name": "Vision LLM",
                    "path_prefix": "/vision",
                    "model": "vision",
                    "strip_prefix": true
                },
                {
                    "name": "Primary LLM",
                    "path_prefix": "",
                    "model": "gemma"
                }
            ]
        },
        "Image generation": {
            "host": "localhost",
            "port": 8022,
            "endpoints": [
                {
                    "name": "Stable Diffusion",
                    "path_prefix": "",
                    "model": "sdxl"
                }
            ]
        }
    },
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

The example configuration defines two servers, one listening on locahost:8081 and the other on localhost:8082. Calls to the former will be forwarded to a llama.cpp instance doing inference on Google's Gemma 3 27B, unless the path starts with ```/vision``` (like ```localhost:8081/vision/health```) in which case the a vision capable Mistral Small 3.2 will be used instead. All calls to localhost:8082 will go to a Stable Diffusion webUI Forge server.

The ```warmup``` section specifies that first, the image generation backend is started, and then the vision capable LLM inference backend. As the feature allowing the image generation backend to keep running with model unloaded is enabled, the backend will not shut down when the LLM backend is spun up, considerably speeding up the first image generation.


## Limitations

The project is in a barely working shape. It has very limited support for backends, though adding new ones should be rather simple. There is also very little graceful error handling. Sending multiple requests too rapidly (before the previous one has finished processing) could cause weird issues. There is no user interface of any sort, unless you count the configuration file, and some logging which you shouldn't.

AI Model Juggler is not a real proxy (not yet, anyway). It simply starts up the requested backend and responds with a 307 redirect to the newly running server. This makes it ill suited for using the llama.cpp's built in web UI.

## Comparison to other projects

The closest alternative is probably [llama-swap](https://github.com/mostlygeek/llama-swap), which promises to do much the same thing as AI Model Juggler, and more besides. However, it seems to be limited to working with backends that support the OpenAI API, meaning that it probably does not work with Stable Diffusion web UI, at least not without some trickery. Other than that, it is probably superior in every regard.
