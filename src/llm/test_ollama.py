
import ollama

response = ollama.chat(
    model="qwen2.5:3b",
    messages=[
        {
            "role": "user",
            "content": "Write a SQL query to display all students."
        }
    ]
)

print(response["message"]["content"])
