# Setup

Install dependencies:

```bash
pip install flask requests openai
```

Run the proxy:

```bash
python openai_proxy.py
```

The server will start on:

```text
http://127.0.0.1:8080
```

# Example Usage

Example using the official OpenAI Python SDK: 

```python
from openai import OpenAI

client = OpenAI(
    api_key="aaddpp",
    base_url="http://127.0.0.1:8080/v1"
)

r = client.chat.completions.create(
    model="claude_opus_4_7",
    messages=[
        {
            "role": "user",
            "content": "write me a hello world py app"
        }
    ]
)

print(r.choices[0].message.content)
```

# Supported Endpoints

* `/v1/chat/completions`
* `/v1/models`
* `/v1/files`
