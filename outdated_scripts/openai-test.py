from openai import OpenAI
client = OpenAI(api_key="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")

completion = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ]
)

print(completion.choices[0].message)
