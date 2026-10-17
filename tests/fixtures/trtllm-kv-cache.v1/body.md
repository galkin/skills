The LLM API reference for the runtime's KV cache.

## KvCacheConfig[#](https://nvidia.github.io/TensorRT-LLM/llm-api/reference.html#kvcacheconfig)

Configuration for the KV cache manager of the runtime.

### Fields[#](https://nvidia.github.io/TensorRT-LLM/llm-api/reference.html#fields)

The fields below are read once, when the executor starts.

- enable\_block\_reuse: true

  Reuse the blocks of a shared prefix across requests.

- max\_tokens: null

  The maximum number of tokens the cache may hold.

- free\_gpu\_memory\_fraction: 0.7

  The share of free GPU memory the cache may take after the model is loaded.

## Enable Tool Calling[#](https://nvidia.github.io/TensorRT-LLM/llm-api/reference.html#enable-tool-calling)

Tool calls are parsed by the server, not by the cache.
