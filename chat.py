import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

OpenAI.api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI()

system_content = os.getenv("CHATGPT_SYSTEM_CONTENT")


def chat_completion(user_content):
    # client = OpenAI()
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": system_content}, {"role": "user", "content": user_content}],
    )
    reply_message = completion.choices[0].message.content
    return reply_message


def main():
    user_content = "Hello!"
    reply_message = chat_completion(user_content)
    print(reply_message)


if __name__ == "__main__":
    main()