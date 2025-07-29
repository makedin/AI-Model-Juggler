# Configuration

AI Model Juggler requires a configuration file named to define its behavior. By default, it loads `config.json` from the current directory, but a different file can be specified using the `--config <file>` (or ```-c <file>``` for short) command line argument.

## Configuration File Structure

The configuration file is a JSON object that contains four sections:
- `temp_dir`: A string specifying the directory where temporary files will be stored. (Optional)
- `backends`: An object defining the backends available for use, each with its own configuration. (Required)
- `servers`: An array of server configurations, each containing a name, host, port, and a list of endpoints. (Required)
- `warmup`: An array of objects specifying which servers and endpoints to warm up at startup. (Optional)


### temp_dir
The `temp_dir` field specifies the directory where temporary files will be stored. The temporary files include KV cache files and modified koboldcpp configuration files.

If not specified, the program will attempt to use `/tmp/ai-model-juggler/` if the `/tmp` directory exists; otherwise, it will create a directory named `ai-model-juggler/` in the current working directory.

### backends
The `backends` section defines the available backends that the program can use. It is an object where each key is the name of a backend, and the value is an object containing the configuration for that backend. The configuration for each backend can include the following fields:

- `binary`: The path to the backend's executable file. (Optional)
- `attach_to`: The URL of a running backend instance to connect to instead of starting a new one. (Optional)
- `default_parameters`: An array of strings representing the command line parameters to be used for every instance of this backend. (Optional)
- `host`: The hostname or IP address the host is to listen on. (Optional, defaults to `localhost`)
- `model_unloading`: A boolean indicating whether to use the model unloading feature of the backend (Optional, defaults to `true` for supported backends)

Either `binary` or `attach_to` must be specified for each backend. If both are specified, the program will first try to connect to the backend at `attach_to`, and if that fails, it will start a new instance using the `binary` path.

Neither `binary` nor `attach_to` may be supplied to a backend that does not support it. For such backends, the other one will be required.

### servers

The `servers` section is an array of server configurations. Each server configuration is an object that contains the following fields:

- `name`: A string representing the name of the server. (Required)
- `host`: The hostname or IP address the server is to listen on. (Required)
- `port`: An integer representing the port number the server will listen on. (Required)
- `endpoints`: An array of endpoint configurations for the server. (Required)


#### endpoint
Each endpoint configuration is an object that contains the following fields:
- `name`: A string representing the name of the endpoint. (Required)
- `path_prefix`: A string representing the path prefix for the endpoint. (Optional, defaults to an empty string, which matches everything)
- `strip_prefix`: A boolean indicating whether to strip the path prefix from the request path before forwarding it to the backend. (Optional, defaults to `false`)
- `backend`: A string representing the name of the backend to use for this endpoint. (Required)
- `parameters`: An array of strings representing the command line parameters to be passed to the backend when starting it, in addition to the backend's default_parameters. (Optional)
- `kv_cache_saving`: A boolean indicating whether to save the KV cache for this endpoint. (Optional, defaults to `true` for backends that support KV cache saving)

The endpoint is defined by the `path_prefix`. `path_prefix` matching is done from top to bottom, so the first endpoint that matches the request path will be used. Order endpoints from most specific to least specific to ensure the correct endpoint is used.

### warmup
The `warmup` section is an array of objects that specify which backend instance to warm up at startup. Each object in the array contains the following fields:
- `server`: A string representing the name of the server with the relevant endpoint. (Required)
- `endpoint`: A string representing the name of the endpoint corresponding to the backend instance. (Required)

Warming up a backend will be started up. Note that warming up multiple backends will result in the previously warmed up backends to be stopped, so it only makes sense to warm up one backend that does not support model unloading, and that one should come last in the list. This feature is most useful with backend backends that are slow to start up but reload the model quickly, such as `Stable Diffusion WebUI`. Warming up is not needed for backend instances that were started beforehand and are only attached to.

# Example Configuration File
```json
{
    "temp_dir": "string",
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

Calls to ```localhost:8081``` with the path starting with ```/vision``` (like ```http://localhost:8081/vision/health```) will go to llama.cpp running a vision capable Mistral Small 3.2, with the path prefix removed (so ```/vision/health``` becomes ```/health```). Calls with the path prefix ```/qwen3``` will be handled by a koboldcpp server running the Qwen3-30B-A3B, again with the prefix stripped. Calls with the prefix ```/ollama``` go to ollama, which does the model selection based on the POST data. Finally, calls with neither prefix will be handled by a llama.cpp server running Gemma 3 27B.

Calls to ```http://localhost:8082/sdapi``` will be routed to a Stable Diffusion WebUI Forge server. Not that the ```/sdapi``` prefix is not stripped, as it belongs to the actual calls to the API. Calls to ```http://localhost:8082``` without the path prefix will go to a ComfyUI server.

The ```warmup``` section specifies that first, Stable Diffusion WebUI Forge is started, and then the vision capable LLM inference backend. As the image generation backend supports model unloading and the feature is enabled (by default, in fact), the backend will not shut down when the LLM backend is spun up, considerably speeding up the first image generation.

The Stable Diffusion WebUI Forge backend will first try to attach to a running instance of the service, available at ```http://localhost:7860```. If the service is not running, a new instance will be started.

ComfyUI only has the `attach_to` defined, and the related endpoint will return an error if the service is not running. The backend will not be started automatically.
