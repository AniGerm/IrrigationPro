# Ollama -> OpenAI Adapter (minimal)

This small adapter exposes an OpenAI-compatible `/v1/chat/completions` endpoint
and forwards requests to a local Ollama instance (`/api/generate`).

Usage
1. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start the adapter:

```bash
# optional: set default model name if yours differs
export OLLAMA_DEFAULT_MODEL="llama3.2:1b"
python adapter.py
```

3. Configure your local VS Code extension (the one that supports an OpenAI-style endpoint) to use `http://localhost:11435` as API base.

Notes
- This is a minimal adapter for local testing. It concatenates messages into a plain prompt.
- For production or better parity, implement streaming/proper role handling and usage fields.