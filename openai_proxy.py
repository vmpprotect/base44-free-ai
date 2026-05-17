# openai_compat_proxy.py
from flask import Flask, request, jsonify
import requests
import time
import uuid
import os

app = Flask(__name__)

APP_ID = "69cc56480f78649c97f34d04" # app id found inside either a request to their api, or inside the JS

LOCAL_API_KEY = "aaddpp"

BASE = f"https://punchmadeuniversity.com/api/apps/{APP_ID}/integration-endpoints/Core"

MODELS = [
    "gpt_5_mini",
    "gemini_3_flash",
    "gpt_5",
    "gpt_5_4",
    "gpt_5_5",
    "gemini_3_1_pro",
    "claude_sonnet_4_6",
    "claude_opus_4_6",
    "claude_opus_4_7",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://punchmadeuniversity.com/",
    "X-App-Id": APP_ID,
    "X-Origin-URL": "https://punchmadeuniversity.com/",
    "Origin": "https://punchmadeuniversity.com",
}

uploaded_files = {}  # file_id -> file_url

def check_api_key():
    auth = request.headers.get("Authorization", "")

    if not auth.startswith("Bearer "):
        return False

    token = auth.split(" ", 1)[1].strip()

    return token == LOCAL_API_KEY


@app.before_request
def authenticate():
    # allow health checks
    if request.path == "/":
        return

    if not check_api_key():
        return jsonify({
            "error": {
                "message": "Invalid API key",
                "type": "invalid_request_error",
                "code": "invalid_api_key"
            }
        }), 401

def messages_to_prompt(messages):
    lines = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, list):
            parts = []

            for item in content:
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))

            content = "\n".join(parts)

        lines.append(f"{role}: {content}")

    return "\n".join(lines)


def extract_text(data):
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        for key in [
            "response",
            "text",
            "content",
            "message",
            "answer"
        ]:
            if key in data:
                return data[key]

        return str(data)

    return str(data)

@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "base44-wrapper"
    })


@app.route("/v1/models", methods=["GET"])
def list_models():
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": m,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "base44-wrapper"
            }
            for m in MODELS
        ]
    })


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    body = request.get_json(force=True)

    model = body.get("model", "gpt_5_mini")
    messages = body.get("messages", [])
    internet = body.get("add_context_from_internet", False)
    response_json_schema = body.get("response_json_schema")
    file_ids = body.get("file_ids", [])

    file_urls = []

    for fid in file_ids:
        if fid in uploaded_files:
            file_urls.append(uploaded_files[fid])

    payload = {
        "prompt": messages_to_prompt(messages),
        "model": model,
    }

    if file_urls:
        payload["file_urls"] = file_urls
    else:
        payload["add_context_from_internet"] = internet

    if response_json_schema:
        payload["response_json_schema"] = response_json_schema

    r = requests.post(
        f"{BASE}/InvokeLLM",
        headers={
            **HEADERS,
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=120
    )

    try:
        data = r.json()
    except Exception:
        data = r.text

    text = extract_text(data)

    return jsonify({
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    })


@app.route("/v1/files", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({
            "error": {
                "message": "Missing file field"
            }
        }), 400

    f = request.files["file"]

    files = {
        "file": (
            f.filename,
            f.stream,
            f.mimetype or "application/octet-stream"
        )
    }

    r = requests.post(
        f"{BASE}/UploadFile",
        headers=HEADERS,
        files=files,
        timeout=120
    )

    try:
        data = r.json()
    except Exception:
        return jsonify({
            "error": {
                "message": r.text,
                "type": "upload_error"
            }
        }), r.status_code

    file_url = data.get("file_url") or data.get("url")

    if not file_url:
        return jsonify({
            "error": {
                "message": f"No file_url returned: {data}",
                "type": "upload_error"
            }
        }), 500

    file_id = f"file-{uuid.uuid4().hex}"

    uploaded_files[file_id] = file_url

    return jsonify({
        "id": file_id,
        "object": "file",
        "bytes": 0,
        "created_at": int(time.time()),
        "filename": f.filename,
        "purpose": request.form.get(
            "purpose",
            "assistants"
        ),
        "url": file_url
    })


@app.route("/v1/files/<file_id>", methods=["GET"])
def get_file(file_id):
    if file_id not in uploaded_files:
        return jsonify({
            "error": {
                "message": "File not found"
            }
        }), 404

    return jsonify({
        "id": file_id,
        "object": "file",
        "url": uploaded_files[file_id]
    })


if __name__ == "__main__":
    print("[+] Running on http://127.0.0.1:8080")

    app.run(
        host="127.0.0.1",
        port=8080
    )