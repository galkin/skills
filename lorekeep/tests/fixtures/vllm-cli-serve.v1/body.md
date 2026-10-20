### Frontend[¶](https://docs.vllm.ai/en/stable/cli/serve/#frontend)

Arguments for the OpenAI-compatible frontend server.

#### `--lora-modules`[¶](https://docs.vllm.ai/en/stable/cli/serve/#-lora-modules)

- LoRA modules configurations in either 'name=path' format or JSON format
or JSON list format. Example (old format): `'name=path'` Example (new
format): ```
{"name": "name", "path": "lora_path",
"base_model_name": "id"}
```

#### `--chat-template`[¶](https://docs.vllm.ai/en/stable/cli/serve/#-chat-template)

- The file path to the chat template, or the template in single-line form for the specified model.

#### `--chat-template-content-format`[¶](https://docs.vllm.ai/en/stable/cli/serve/#-chat-template-content-format)

- Possible choices: `auto`, `openai`, `string`
- The format to render message content within a chat template. 
  - "string" will render the content as a string. Example: `"Hello World"`
  - "openai" will render the content as a list of dictionaries, similar to
  OpenAI schema. Example: `[{"type": "text", "text": "Hello world!"}]`
- Default: `auto`

#### `--trust-request-chat-template`, `--no-trust-request-chat-template`[¶](https://docs.vllm.ai/en/stable/cli/serve/#-trust-request-chat-template-no-trust-request-chat-template)

- Whether to trust the chat template provided in the request. If False,
the server will always use the chat template specified by `--chat-template` or the ones from tokenizer.
- Default: `False`

#### `--trust-request-mm-kwargs`, `--no-trust-request-mm-kwargs`[¶](https://docs.vllm.ai/en/stable/cli/serve/#-trust-request-mm-kwargs-no-trust-request-mm-kwargs)

- Whether to trust per-request multimodal kwargs (`mm_processor_kwargs` and `media_io_kwargs`). If False, the server rejects non-empty values
because they can change multimodal preprocessing resource usage. Only
enable this when API clients are trusted.
- Default: `False`

#### `--default-chat-template-kwargs`[¶](https://docs.vllm.ai/en/stable/cli/serve/#-default-chat-template-kwargs)

- Default keyword arguments to pass to the chat template renderer. These will be merged with request-level chat\_template\_kwargs, with request values taking precedence. Useful for setting default behavior for reasoning models. Example: '{"enable\_thinking": false}' to disable thinking mode by default for Qwen3/DeepSeek models. Should either be a valid JSON string or JSON keys passed individually.



#### `--max-model-len`[¶](https://docs.vllm.ai/en/stable/cli/serve/#-max-model-len)

- Model context length (prompt and output). If unspecified, will be automatically derived from the model config. When passing via `--max-model-len`, supports k/m/g/K/M/G in human-readable
format. Examples:
  - 1k -> 1000
  - 1K -> 1024
  - 25.6k -> 25,600
  - -1 or 'auto' -> Automatically choose the maximum model length that fits in GPU memory. This will use the model's maximum context length if it fits, otherwise it will find the largest length that can be accommodated.
Parse human-readable integers like '1k', '2M', etc. Including decimal values with decimal multipliers. Also accepts -1 or 'auto' as a special value for auto-detection. ```
Examples:
- '1k' -> 1,000
- '1K' -> 1,024
- '25.6k' -> 25,600
- '-1' or 'auto' -> -1 (special value for auto-detection)
```

#### `--quantization`, `-q`[¶](https://docs.vllm.ai/en/stable/cli/serve/#-quantization-q)

- Method used to quantize the weights. If `None`, we first check the `quantization_config` attribute in the model config file. If that is `None`, we assume the model weights are not quantized and use `dtype` to
determine the data type of the weights.

#### `--quantization-config`[¶](https://docs.vllm.ai/en/stable/cli/serve/#-quantization-config)

- User-facing quantization configuration. Carries per-layer-kind specs
