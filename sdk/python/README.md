# OpenAI InkStack Python SDK

Build Python applications that start InkStack threads, run turns, stream progress,
and control workspace access.

## Install

Install the SDK:

```bash
pip install inkstack
```

## Quickstart

The SDK reuses your existing InkStack authentication when one is already
available:

```python
from inkstack import InkStack

with InkStack() as inkstack:
    thread = inkstack.thread_start()
    result = thread.run("Explain this repository in three bullets.")
    print(result.final_response)
```

`thread.run(...)` returns a `TurnResult` containing the final response,
collected items, and token usage.

## Authentication

Existing InkStack authentication is reused automatically. To start ChatGPT
browser login explicitly:

```python
from inkstack import InkStack

with InkStack() as inkstack:
    login = inkstack.login_chatgpt()
    print(login.auth_url)
    print(login.wait().success)
```

For device-code login:

```python
with InkStack() as inkstack:
    login = inkstack.login_chatgpt_device_code()
    print(login.verification_url, login.user_code)
    login.wait()
```

For API-key login:

```python
with InkStack() as inkstack:
    inkstack.login_api_key("sk-...")
```

## Built-In Help

Use Python's standard `help(inkstack)`, `help(InkStack)`, or
`python -m pydoc inkstack` documentation tools.

## Documentation

- [Getting started](https://github.com/Grim-Saga/InkStack/blob/main/sdk/python/docs/getting-started.md)
- [API reference](https://github.com/Grim-Saga/InkStack/blob/main/sdk/python/docs/api-reference.md)
- [Untrusted external messages](https://github.com/Grim-Saga/InkStack/blob/main/sdk/python/docs/api-reference.md#externalmessage)
- [FAQ](https://github.com/Grim-Saga/InkStack/blob/main/sdk/python/docs/faq.md)
- [Examples](https://github.com/Grim-Saga/InkStack/blob/main/sdk/python/examples/README.md)

The package is licensed under the
[repository Apache License 2.0](https://github.com/Grim-Saga/InkStack/blob/main/LICENSE).
