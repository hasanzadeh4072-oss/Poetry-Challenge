import os
import json
import random
import threading
import time

import requests
from flask import Flask, request


app = Flask(__name__)

TOKEN = os.getenv("SOROUSH_TOKEN")
API_BASE = f"https://api.splus.ir/bot{TOKEN}"

QUESTION_COUNT = 7
QUESTION_TIME = 90

LEVEL_FILES = {
    "ashenaei": "ashenaei.json",
    "danaei": "danaei.json",
    "ostad": "Ostad.json",
}

LEVEL_NAMES = {
    "ashenaei": "آشنایی",
    "danaei": "دانایی",
    "ostad": "استادی",
}

# وضعیت بازی کاربران
games = {}

# قفل برای جلوگیری از اجرای هم‌زمان چند بازی برای یک کاربر
game_locks = {}


def api_request(method, data=None):
    """ارسال درخواست به API سروش‌پلاس."""
    try:
        response = requests.post(
            f"{API_BASE}/{method}",
            json=data or {},
            timeout=20
        )

        if response.status_code != 200:
            print(f"API Error {method}: {response.status_code}")
            return None

        return response.json()

    except Exception as e:
        print(f"API Exception {method}: {e}")
        return None


def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    return api_request("sendMessage", data)


def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    return api_request("editMessageText", data)


def delete_message(chat_id, message_id):
    return api_request(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id,
        }
    )


def answer_callback(callback_id):
    if callback_id:
        return api_request(
            "answerCallbackQuery",
            {
                "callback_query_id": callback_id
            }
        )


def load_questions():
    """بارگذاری سؤال‌های سه سطح."""
    questions = {}

    for level, filename in LEVEL_FILES.items():
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                print(f"{filename}: JSON باید یک لیست باشد.")
                questions[level] = []
                continue

            valid_questions = []

            for q in data:
                if not isinstance(q, dict):
                    continue

                if not q.get("سؤال"):
                    continue

                if not q.get("پاسخ صحیح"):
                    continue

                options = q.get("گزینه‌ها")

                if not isinstance(options, list):
                    continue

                if len(options) < 2:
                    continue

                if q["پاسخ صحیح"] not in options:
                    continue

                valid_questions.append(q)

            questions[level] = valid_questions

            print(
                f"{filename}: "
                f"{len(valid_questions)} سؤال معتبر بارگذاری شد."
            )

        except FileNotFoundError:
            print(f"فایل پیدا نشد: {filename}")
            questions[level] = []

        except Exception as e:
            print(f"خطا در خواندن {filename}: {e}")
            questions[level] = []

    return questions


QUESTIONS = load_questions()


def main_keyboard():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "شروع چالش",
                    "callback_data": "start_challenge"
                }
            ]
        ]
    }


def level_keyboard():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "آشنایی",
                    "callback_data": "level_ashenaei"
                }
            ],
            [
                {
                    "text": "دانایی",
                    "callback_data": "level_danaei"
                }
            ],
            [
                {
                    "text": "استادی",
                    "callback_data": "level_ostad"
                }
            ]
        ]
    }


def answer_keyboard(options):
    rows = []

    for index, option in enumerate(options):
        rows.append([
            {
                "text": str(option),
                "callback_data": f"answer_{index}"
            }
        ])

    return {
        "inline_keyboard": rows
    }


def start_message():
    return (
        "📚 <b>چالش شعرانه</b>\n\n"
        "در این بازی ۷ سؤال از سطح انتخابی شما نمایش داده می‌شود.\n"
        "برای هر سؤال ۱ دقیقه و ۳۰ ثانیه فرصت دارید.\n\n"
        "✅ پاسخ صحیح: +۱۰۰ امتیاز\n"
        "❌ پاسخ غلط: −۱۵ امتیاز\n"
        "⏱ بدون پاسخ: ۰ امتیاز\n\n"
        "برای شروع، سطح خود را انتخاب کنید:"
    )


def prepare_question(question):
    """آماده‌سازی سؤال و تصادفی‌کردن گزینه‌ها."""
    options = list(question["گزینه‌ها"])
    random.shuffle(options)

    return {
        "question": question,
        "options": options,
    }


def send_question(chat_id):
    """ارسال سؤال فعلی بازی."""
    game = games.get(chat_id)

    if not game:
        return

    index = game["current"]

    if index >= QUESTION_COUNT:
        finish_game(chat_id)
        return

    prepared = game["questions"][index]

    question = prepared["question"]
    options = prepared["options"]

    text = (
        f"❓ <b>سؤال {index + 1} از {QUESTION_COUNT}</b>\n\n"
        f"{question['سؤال']}"
    )

    result = send_message(
        chat_id,
        text,
        answer_keyboard(options)
    )

    if not result:
        return

    message = result.get("result", {})

    game["message_id"] = message.get("message_id")
    game["question_started"] = time.time()

    # برای کنترل زمان سؤال
    timer = threading.Thread(
        target=question_timeout,
        args=(chat_id, index),
        daemon=True
    )

    timer.start()


def question_timeout(chat_id, question_index):
    """بررسی پایان زمان پاسخ."""
    time.sleep(QUESTION_TIME)

    game = games.get(chat_id)

    if not game:
        return

    # اگر کاربر به سؤال بعدی رفته، این تایمر مربوط به سؤال قبلی است.
    if game["current"] != question_index:
        return

    if game.get("answered"):
        return

    game["answered"] = True
    game["score"] += 0

    if game.get("message_id"):
        edit_message(
            chat_id,
            game["message_id"],
            (
                f"⏱ <b>زمان سؤال {question_index + 1} تمام شد.</b>\n\n"
                "امتیاز این سؤال: ۰"
            )
        )

    game["current"] += 1
    game["answered"] = False

    time.sleep(1)

    if game["current"] >= QUESTION_COUNT:
        finish_game(chat_id)
    else:
        send_question(chat_id)


def process_answer(chat_id, callback_id, option_index):
    game = games.get(chat_id)

    if not game:
        answer_callback(callback_id)
        return

    if game.get("answered"):
        answer_callback(callback_id)
        return

    current = game["current"]

    if current >= QUESTION_COUNT:
        answer_callback(callback_id)
        return

    prepared = game["questions"][current]

    question = prepared["question"]
    options = prepared["options"]

    try:
        option_index = int(option_index)
    except (ValueError, TypeError):
        answer_callback(callback_id)
        return

    if option_index < 0 or option_index >= len(options):
        answer_callback(callback_id)
        return

    selected_answer = options[option_index]
    correct_answer = question["پاسخ صحیح"]

    game["answered"] = True

    if selected_answer == correct_answer:
        game["score"] += 100

        result_text = (
            f"✅ <b>پاسخ صحیح</b>\n\n"
            f"امتیاز این سؤال: +۱۰۰\n"
            f"امتیاز فعلی: {game['score']}"
        )

    else:
        game["score"] -= 15

        result_text = (
            f"❌ <b>پاسخ غلط</b>\n\n"
            f"پاسخ صحیح: {correct_answer}\n"
            f"امتیاز این سؤال: −۱۵\n"
            f"امتیاز فعلی: {game['score']}"
        )

    answer_callback(callback_id)

    if game.get("message_id"):
        edit_message(
            chat_id,
            game["message_id"],
            result_text
        )

    game["current"] += 1
    game["answered"] = False

    time.sleep(1)

    if game["current"] >= QUESTION_COUNT:
        finish_game(chat_id)
    else:
        send_question(chat_id)


def finish_game(chat_id):
    game = games.get(chat_id)

    if not game:
        return

    score = game["score"]
    level = LEVEL_NAMES.get(game["level"], game["level"])

    if score >= 600:
        message = "🏆 فوق‌العاده بود! شما واقعاً در این سطح درخشیدید."
    elif score >= 400:
        message = "👏 عالی بود! عملکرد بسیار خوبی داشتید."
    elif score >= 200:
        message = "🌿 خوب بود! با کمی تمرین بهتر هم می‌شوید."
    else:
        message = "📚 این پایان راه نیست؛ یک بار دیگر امتحان کنید."

    text = (
        "🎉 <b>چالش به پایان رسید!</b>\n\n"
        f"سطح: <b>{level}</b>\n"
        f"تعداد سؤال: <b>{QUESTION_COUNT}</b>\n"
        f"امتیاز نهایی: <b>{score}</b>\n\n"
        f"{message}"
    )

    send_message(
        chat_id,
        text,
        main_keyboard()
    )

    games.pop(chat_id, None)


def start_game(chat_id, level):
    if chat_id in games:
        return

    if level not in QUESTIONS:
        send_message(
            chat_id,
            "متأسفانه سؤال‌های این سطح در دسترس نیست."
        )
        return

    available = QUESTIONS[level]

    if len(available) < QUESTION_COUNT:
        send_message(
            chat_id,
            "تعداد سؤال‌های این سطح برای شروع چالش کافی نیست."
        )
        return

    selected = random.sample(available, QUESTION_COUNT)

    prepared_questions = [
        prepare_question(q)
        for q in selected
    ]

    games[chat_id] = {
        "level": level,
        "questions": prepared_questions,
        "current": 0,
        "score": 0,
        "message_id": None,
        "question_started": None,
        "answered": False,
    }

    countdown_message = send_message(
        chat_id,
        "۱"
    )

    if countdown_message:
        countdown_id = (
            countdown_message
            .get("result", {})
            .get("message_id")
        )

        if countdown_id:
            time.sleep(0.7)
            edit_message(chat_id, countdown_id, "۲")

            time.sleep(0.7)
            edit_message(chat_id, countdown_id, "۳")

            time.sleep(0.7)
            delete_message(chat_id, countdown_id)

    send_message(
        chat_id,
        (
            f"🎮 <b>چالش {LEVEL_NAMES[level]}</b>\n\n"
            "شروع شد!"
        )
    )

    time.sleep(0.5)

    send_question(chat_id)


def handle_update(update):
    """پردازش Update دریافتی از سروش‌پلاس."""

    # پیام معمولی
    message = update.get("message")

    if message:
        chat = message.get("chat", {})
        chat_id = chat.get("id")

        text = message.get("text", "")

        if not chat_id:
            return

        if text in ["/start", "شروع", "شروع چالش"]:
            send_message(
                chat_id,
                start_message(),
                main_keyboard()
            )

        return

    # Callback Query
    callback = update.get("callback_query")

    if not callback:
        return

    callback_id = callback.get("id")
    data = callback.get("data", "")

    callback_message = callback.get("message", {})
    chat = callback_message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        answer_callback(callback_id)
        return

    if data == "start_challenge":
        answer_callback(callback_id)

        edit_message(
            chat_id,
            callback_message.get("message_id"),
            "🎓 <b>سطح چالش را انتخاب کنید:</b>",
            level_keyboard()
        )

        return

    if data.startswith("level_"):
        level = data.replace("level_", "", 1)

        answer_callback(callback_id)

        if level not in LEVEL_NAMES:
            return

        start_game(chat_id, level)
        return

    if data.startswith("answer_"):
        option_index = data.replace("answer_", "", 1)

        process_answer(
            chat_id,
            callback_id,
            option_index
        )


@app.route("/webhook", methods=["POST"])
def webhook():
    """دریافت Update از سروش‌پلاس."""
    try:
        update = request.get_json(silent=True)

        if not update:
            return "OK"

        threading.Thread(
            target=handle_update,
            args=(update,),
            daemon=True
        ).start()

        return "OK"

    except Exception as e:
        print(f"Webhook Error: {e}")
        return "OK"


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000))
    )
