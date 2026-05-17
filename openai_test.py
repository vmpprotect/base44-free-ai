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