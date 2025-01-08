import os
import random
from flask import Flask, request, abort
from linebot import LineBotApi
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
import openai

# .env ファイルの読み込み
load_dotenv(override=True)

app = Flask(__name__)

line_bot_api = LineBotApi(channel_access_token=os.environ["ACCESS_TOKEN"])
handler = WebhookHandler(channel_secret=os.environ["CHANNEL_SECRET"])

# OpenAI API キーの設定
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("環境変数 'OPENAI_API_KEY' が設定されていません。")
openai.api_key = api_key

# システムメッセージの設定
system_content = os.getenv("CHATGPT_SYSTEM_CONTENT")
if not system_content:
    raise ValueError("環境変数 'CHATGPT_SYSTEM_CONTENT' が設定されていません。")


@app.route("/")
def index():
    return "You call index()"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


def adjust_response_length(response: str, user_message_length: int, adjustment_factor: float = 1.2) -> str:
    """
    ユーザーのメッセージの長さに応じて返信の文字数を調整
    """
    max_length = int(user_message_length * adjustment_factor)
    print(
        f"User Message Length: {user_message_length}, Max Length: {max_length}, Response Length: {len(response)}"
    )
    if len(response) > max_length:
        response = response[:max_length].rstrip() + "…"  # 長すぎる場合は省略
    return response


def add_grandma_tone(response: str) -> str:
    """
    応答におばあちゃんらしい語尾を追加
    """
    endings = ["じゃよ", "ねぇ", "かい？", "だねぇ"]
    if not response.endswith(tuple(endings)):
        response += " " + random.choice(endings)
    return response


def chat_completion(user_content: str) -> str:
    """
    OpenAI を利用して応答を生成し、文字数を調整
    """
    try:
        print("Calling OpenAI API with user content:", user_content)
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            max_tokens=50,
            temperature=0.5,
        )
        raw_response = completion["choices"][0]["message"]["content"]  # 正しいアクセス形式を使用
        print("Raw response from OpenAI API:", raw_response)

        # ユーザーのメッセージ文字数に応じて応答を調整
        user_message_length = len(user_content)
        adjustment_factor = float(os.getenv("ADJUSTMENT_FACTOR", 1.0))
        adjusted_response = adjust_response_length(raw_response, user_message_length, adjustment_factor)

        # 自然な語尾を追加
        final_response = add_grandma_tone(adjusted_response)
        print("Final response:", final_response)
        return final_response
    except Exception as e:
        print("Error in chat_completion:", e)
        return f"エラーが発生しました: {e}"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent):
    """
    ユーザーのメッセージを処理してLINEに応答
    """
    raw_response = chat_completion(event.message.text)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=raw_response))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
