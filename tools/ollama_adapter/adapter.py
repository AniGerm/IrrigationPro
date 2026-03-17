from flask import Flask, request, jsonify
import requests
import time
import os

app = Flask(__name__)

OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')

def call_ollama(model, prompt, max_tokens=256):
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {"model": model, "prompt": prompt, "max_tokens": max_tokens}
    try:
        r = requests.post(url, json=payload, stream=True, timeout=60)
    except Exception as e:
        return None, str(e)

    if r.status_code != 200:
        try:
            return None, r.json()
        except Exception:
            return None, r.text

    # Ollama streams JSON objects per line with 'response' fragments
    pieces = []
    try:
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = None
                # Some lines may be concatenated; try parse
                import json
                obj = json.loads(line)
            except Exception:
                # skip unparsable
                continue
            text = obj.get('response')
            if text:
                pieces.append(text)
            if obj.get('done'):
                break
    except Exception as e:
        return None, str(e)

    return ''.join(pieces), None


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.get_json() or {}
    model = data.get('model') or os.environ.get('OLLAMA_DEFAULT_MODEL') or 'llama3.2:1b'
    messages = data.get('messages') or []
    max_tokens = data.get('max_tokens') or 512

    # Simple conversion of messages to prompt text
    prompt_parts = []
    for m in messages:
        role = m.get('role', 'user')
        content = m.get('content', '')
        if role == 'system':
            prompt_parts.append(f"System: {content}\n")
        elif role == 'assistant':
            prompt_parts.append(f"Assistant: {content}\n")
        else:
            prompt_parts.append(f"User: {content}\n")
    prompt = "\n".join(prompt_parts)

    text, err = call_ollama(model, prompt, max_tokens=max_tokens)
    if err:
        return jsonify({'error': str(err)}), 500

    resp = {
        'id': f'ollama-adapt-{int(time.time())}',
        'object': 'chat.completion',
        'created': int(time.time()),
        'model': model,
        'choices': [
            {
                'index': 0,
                'message': {'role': 'assistant', 'content': text},
                'finish_reason': 'stop'
            }
        ],
        'usage': {}
    }
    return jsonify(resp)


if __name__ == '__main__':
    port = int(os.environ.get('ADAPTER_PORT', 11435))
    app.run(host='127.0.0.1', port=port)
