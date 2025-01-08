import os
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


def adjust_response_length(response, user_message_length, adjustment_factor=1.2):
    """
    ユーザーのメッセージの長さに応じて返信の文字数を調整
    """
    max_length = int(user_message_length * adjustment_factor)
    print(
        f"User Message Length: {user_message_length}, Max Length: {max_length}, Response Length: {len(response)}"
    )
    if len(response) > max_length:
        response = response[:max_length] + "…"  # 長すぎる場合は省略
    return response


def chat_completion(user_content):
    """
    OpenAI を利用して応答を生成し、文字数を調整
    """
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            max_tokens=50,  # 応答を50トークンに制限
            temperature=0.5,  # 簡潔な応答を生成しやすくする
        )
        raw_response = completion["choices"][0]["message"]["content"]

        # ユーザーのメッセージ文字数に応じて応答を調整
        user_message_length = len(user_content)
        adjustment_factor = float(
            os.getenv("ADJUSTMENT_FACTOR", 1.0)
        )  # デフォルトは1倍（入力とほぼ同じ長さ）
        adjusted_response = adjust_response_length(raw_response, user_message_length, adjustment_factor)

        return adjusted_response
    except Exception as e:
        return f"エラーが発生しました: {e}"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # ユーザーのメッセージに基づいて応答を生成
    raw_response = chat_completion(event.message.text)
    # LINEに応答を送信
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=raw_response))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
