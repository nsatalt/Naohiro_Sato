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


def add_emojis_based_on_content(response: str) -> str:
    """
    応答内容に応じて適切な絵文字を追加
    """
    emoji_map = {
        "お風呂": "🛁",
        "ご飯": "🍚",
        "天気": "🌤️",
        "猫": "🐱",
        "犬": "🐶",
        "散歩": "🚶‍♀️",
        "疲れた": "😴",
        "楽しい": "😊",
        "ありがとう": "🙏",
        "好き": "❤️",
    }

    added_emojis = []
    for keyword, emoji in emoji_map.items():
        if keyword in response:
            added_emojis.append(emoji)

    # 応答の最後に絵文字を追加（重複を避ける）
    if added_emojis:
        response += " " + " ".join(set(added_emojis))
    return response


def chat_completion(user_content: str) -> str:
    """
    OpenAI を利用して応答を生成し、絵文字を追加
    """
    try:
        print("Calling OpenAI API with user content:", user_content)
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            max_tokens=200,
            temperature=0.8,
        )
        raw_response = completion["choices"][0]["message"]["content"]
        print("Raw response from OpenAI API:", raw_response)

        # 内容に応じて絵文字を追加
        final_response = add_emojis_based_on_content(raw_response)
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
