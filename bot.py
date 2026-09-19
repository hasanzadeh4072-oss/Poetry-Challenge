import os
import json
import random
import threading
import time

import requests
from flask import Flask, request, jsonify


TOKEN = os.getenv("SOROUSH_TOKEN")

if not TOKEN:
    raise RuntimeError("SOROUSH_TOKEN is not set")

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

games = {}
games_lock = threading.Lock()
chat_locks = {}


def get_chat_lock(chat_id):
    with games_lock:
        if chat_id not in chat_locks:
            chat_locks[chat_id] = threading.Lock()
        return chat_locks[chat_id]


def api_request(method, data=None, context=""):
    url = f"{API_BASE}/{method}"
    start_time = time.time()

    print(f"API START: {method} | {context}")

    try:
        response = requests.post(
            url,
            json=data or {},
            timeout=20
        )

        elapsed = time.time() - start_time

        print(
            f"API END: {method} "
            f"status={response.status_code} "
            f"time={elapsed:.2f}s | {context}"
        )

        if response.status_code != 200:
            print(
                f"API Error {method}: "
                f"{response.status_code} - {response.text}"
            )
            return None

        try:
            return response.json()
        except Exception:
            return None

    except Exception as e:
        elapsed = time.time() - start_time
        print(
            f"API Exception {method}: "
            f"{e} time={elapsed:.2f}s | {context}"
        )
        return None


def send_message(chat_id, text, reply_markup=None, context=""):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    return api_request(
        "sendMessage",
        data,
        context=context
    )


def edit_message(chat_id, message_id, text, reply_markup=None, context=""):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    return api_request(
        "editMessageText",
        data,
        context=context
    )


def delete_message(chat_id, message_id, context=""):
    return api_request(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id,
        },
        context=context
    )


def answer_callback(callback_id, text=None, show_alert=False):
    data = {
        "callback_query_id": callback_id,
        "show_alert": show_alert,
    }

    if text:
        data["text"] = text

    return api_request(
        "answerCallbackQuery",
        data,
        context="callback"
    )


def build_options(record):
    options = record.get("گزینه‌ها")

    if isinstance(options, list) and len(options) >= 2:
        return options[:]

    correct = record.get("پاسخ صحیح", "")

    others = record.get("سایر گزینه‌های چالشی", [])

    if not isinstance(others, list):
        others = []

    options = [correct] + others

    if record.get("نوع سؤال") == "صحیح/غلط":
        options = ["صحیح", "غلط"]

    return options


def load_questions(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"{filename}: ساختار JSON معتبر نیست.")
            return []

        valid = []

        for record in data:
            if not isinstance(record, dict):
                continue

            question = str(record.get("سؤال", "")).strip()
            correct = str(record.get("پاسخ صحیح", "")).strip()

            if not question or not correct:
                continue

            options = build_options(record)

            if len(options) < 2:
                continue

            options = [
                str(option).strip()
                for option in options
                if str(option).strip()
            ]

            if correct not in options:
                options.insert(0, correct)

            if len(options) < 2:
                continue

            record["_options"] = options
            valid.append(record)

        print(
            f"{filename}: "
            f"{len(valid)} سؤال معتبر بارگذاری شد."
        )

        return valid

    except Exception as e:
        print(f"خطا در بارگذاری {filename}: {e}")
        return []


QUESTION_BANKS = {}

for level, filename in LEVEL_FILES.items():
    QUESTION_BANKS[level] = load_questions(filename)


def main_keyboard():
    return {
        "keyboard": [
            [
                {
                    "text": "شروع چالش"
                }
            ],
            [
                {
                    "text": "💬 ارتباط با مدیر"
                },
                {
                    "text": "🌿 درباره ما"
                }
            ],
            [
                {
                    "text": "🤖 سایر بات‌ها"
                }
            ],
        ],
        "resize_keyboard": True,
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
            ],
        ]
    }


def stop_keyboard():
    return {
        "keyboard": [
            [
                {
                    "text": "⛔ توقف چالش"
                }
            ]
        ],
        "resize_keyboard": True,
    }


def answer_keyboard(options):
    keyboard = []

    for i in range(0, len(options), 2):
        row = []

        for j in range(i, min(i + 2, len(options))):
            row.append(
                {
                    "text": options[j],
                    "callback_data": f"answer_{j}"
                }
            )

        keyboard.append(row)

    return {
        "inline_keyboard": keyboard
    }


ABOUT_TEXT = """🌿 <b>درباره ما</b>

از سال ۱۳۹۵ با کانال «شعرکده» در پیام‌رسان سروش پلاس فعالیت خود را آغاز کرده‌ایم.

هدف ما معرفی و انتشار شعر و ادبیات فارسی و ایجاد فضایی برای علاقه‌مندان این حوزه است.

✨ «چالش شعرانه» یکی از تجربه‌های تازهٔ شعرکده است؛
یک بازی ادبی برای سنجش دانسته‌های شما در سه سطح آشنایی، دانایی و استادی.

از همراهی شما سپاسگزاریم. 🌱"""


MANAGER_TEXT = """💬 <b>ارتباط با مدیر</b>

اگر پیشنهادی دارید، مشکلی در بات مشاهده کردید یا موضوعی نیاز به پیگیری داشت، می‌توانید از طریق بات پیام ناشناس با مدیر در ارتباط باشید."""


OTHER_BOTS_TEXT = """🤖 <b>سایر بات‌های شعرکده</b>

📝 بات پیام ناشناس
🎴 کارت شعر
🔮 فال حافظ

برای استفاده از هرکدام، از لینک مربوط به همان بات در کانال شعرکده استفاده کنید."""


def prepare_question(game):
    level = game["level"]
    questions = game["questions"]
    index = game["current_index"]

    if index >= len(questions):
        return None

    question = questions[index]

    options = list(question["_options"])
    random.shuffle(options)

    game["current_question"] = question
    game["current_options"] = options
    game["answered"] = False
    game["question_started"] = time.time()
    game["deadline"] = time.time() + QUESTION_TIME

    return question


def send_question(chat_id):
    with get_chat_lock(chat_id):
        with games_lock:
            game = games.get(chat_id)

            if not game or game.get("finished"):
                return

            question = prepare_question(game)

            if question is None:
                pass
            else:
                question_number = game["current_index"] + 1
                total = len(game["questions"])
                level_name = LEVEL_NAMES[game["level"]]

                text = (
                    f"🎯 <b>چالش شعرانه</b>\n\n"
                    f"سطح: <b>{level_name}</b>\n"
                    f"سؤال <b>{question_number}</b> از <b>{total}</b>\n\n"
                    f"{question['سؤال']}\n\n"
                    f"⏱ زمان پاسخ‌گویی: <b>۹۰ ثانیه</b>"
                )

                options = game["current_options"]

        result = send_message(
            chat_id,
            text,
            answer_keyboard(options),
            context="question"
        )

        if result and isinstance(result, dict):
            message = result.get("result")

            if isinstance(message, dict):
                with games_lock:
                    game = games.get(chat_id)

                    if game and not game.get("finished"):
                        game["question_message_id"] = message.get(
                            "message_id"
                        )

        schedule_question_timeout(chat_id)


def schedule_question_timeout(chat_id):
    timer = threading.Timer(
        QUESTION_TIME,
        question_timeout,
        args=(chat_id,)
    )

    timer.daemon = True
    timer.start()


def question_timeout(chat_id):
    with get_chat_lock(chat_id):
        with games_lock:
            game = games.get(chat_id)

            if not game or game.get("finished"):
                return

            if game.get("answered"):
                return

            deadline = game.get("deadline", 0)

            if time.time() < deadline:
                return

            game["answered"] = True
            game["current_index"] += 1

            next_question = game["current_index"] < len(
                game["questions"]
            )

        send_message(
            chat_id,
            "⏰ زمان این سؤال به پایان رسید.\n"
            "برای این سؤال امتیازی ثبت نشد.",
            context="timeout"
        )

    if next_question:
        continue_game(chat_id)
    else:
        finish_game(chat_id)


def process_answer(chat_id, callback_id, option_index):
    answer_callback(callback_id)

    with get_chat_lock(chat_id):
        with games_lock:
            game = games.get(chat_id)

            if not game or game.get("finished"):
                return

            if game.get("answered"):
                return

            options = game.get("current_options", [])

            if option_index < 0 or option_index >= len(options):
                return

            game["answered"] = True

            question = game["current_question"]
            selected = options[option_index]
            correct = str(question.get("پاسخ صحیح", "")).strip()

            is_correct = selected == correct

            if is_correct:
                game["score"] += 100
                result_text = "✅ پاسخ درست بود! <b>+۱۰۰ امتیاز</b>"
            else:
                game["wrong_answers"] += 1

                if game["wrong_answers"] % 2 == 0:
                    game["score"] -= 15
                    result_text = (
                        "❌ پاسخ نادرست بود.\n"
                        "⚠️ هر دو پاسخ غلط، <b>۱۵ امتیاز</b> کسر شد."
                    )
                else:
                    result_text = (
                        "❌ پاسخ نادرست بود.\n"
                        "این پاسخ به‌تنهایی امتیازی کسر نکرد."
                    )

            explanation = str(
                question.get("توضیح کوتاه", "")
            ).strip()

            game["current_index"] += 1

            next_question = game["current_index"] < len(
                game["questions"]
            )

        message = result_text

        if explanation:
            message += f"\n\n💡 <b>توضیح:</b>\n{explanation}"

        send_message(
            chat_id,
            message,
            context="answer"
        )

    if next_question:
        continue_game(chat_id)
    else:
        finish_game(chat_id)


def continue_game(chat_id):
    time.sleep(1)

    with games_lock:
        game = games.get(chat_id)

        if not game or game.get("finished"):
            return

    send_question(chat_id)


def perfect_score_animation(chat_id):
    messages = [
        "🎉",
        "✨",
        "🏆",
    ]

    for emoji in messages:
        send_message(
            chat_id,
            emoji,
            context="perfect_animation"
        )
        time.sleep(0.6)


def finish_game(chat_id):
    with get_chat_lock(chat_id):
        with games_lock:
            game = games.get(chat_id)

            if not game or game.get("finished"):
                return

            game["finished"] = True

            score = game["score"]
            level = LEVEL_NAMES.get(
                game["level"],
                game["level"]
            )

        if score >= 700:
            evaluation = "🏆 <b>فوق‌العاده!</b>"
        elif score >= 400:
            evaluation = "🌟 <b>عالی!</b>"
        elif score >= 200:
            evaluation = "👏 <b>خوب!</b>"
        else:
            evaluation = "🌱 <b>این پایان راه نیست.</b>"

        text = (
            "🎊 <b>چالش به پایان رسید!</b>\n\n"
            f"🎯 سطح: <b>{level}</b>\n"
            f"🏅 امتیاز نهایی: <b>{score}</b>\n\n"
            f"{evaluation}\n\n"
            "برای شروع یک چالش جدید، روی «شروع چالش» بزنید."
        )

        send_message(
            chat_id,
            text,
            main_keyboard(),
            context="finish"
        )

        if score >= 700:
            threading.Thread(
                target=perfect_score_animation,
                args=(chat_id,),
                daemon=True
            ).start()


def stop_game(chat_id):
    with get_chat_lock(chat_id):
        with games_lock:
            game = games.get(chat_id)

            if game:
                game["finished"] = True

        send_message(
            chat_id,
            "⛔ <b>چالش متوقف شد.</b>\n\n"
            "هر زمان خواستید می‌توانید دوباره «شروع چالش» را انتخاب کنید.",
            main_keyboard(),
            context="stop"
        )


def start_game(chat_id, level):
    with get_chat_lock(chat_id):
        questions = QUESTION_BANKS.get(level, [])

        if len(questions) < QUESTION_COUNT:
            send_message(
                chat_id,
                "⚠️ تعداد سؤال‌های این سطح برای شروع چالش کافی نیست.",
                main_keyboard(),
                context="start_error"
            )
            return

        selected_questions = random.sample(
            questions,
            QUESTION_COUNT
        )

        with games_lock:
            games[chat_id] = {
                "level": level,
                "questions": selected_questions,
                "current_index": 0,
                "score": 0,
                "wrong_answers": 0,
                "answered": False,
                "finished": False,
                "current_question": None,
                "current_options": [],
                "question_message_id": None,
                "question_started": None,
                "deadline": None,
            }

        send_message(
            chat_id,
            (
                f"🎯 <b>سطح {LEVEL_NAMES[level]}</b> انتخاب شد.\n\n"
                "چالش تا چند لحظه دیگر شروع می‌شود..."
            ),
            stop_keyboard(),
            context="start_game"
        )

    def countdown():
        for number in ["۳", "۲", "۱"]:
            with games_lock:
                game = games.get(chat_id)

                if not game or game.get("finished"):
                    return

            send_message(
                chat_id,
                number,
                context="countdown"
            )

            time.sleep(1)

        with games_lock:
            game = games.get(chat_id)

            if not game or game.get("finished"):
                return

        send_question(chat_id)

    threading.Thread(
        target=countdown,
        daemon=True
    ).start()


def handle_update(update):
    if not isinstance(update, dict):
        return

    callback = update.get("callback_query")

    if callback:
        callback_id = callback.get("id")

        message = callback.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")

        data = callback.get("data", "")

        if chat_id is None:
            if callback_id:
                answer_callback(callback_id)
            return

        if data.startswith("level_"):
            level = data.replace("level_", "", 1)

            if level in LEVEL_FILES:
                answer_callback(callback_id)

                start_game(
                    chat_id,
                    level
                )

            return

        if data.startswith("answer_"):
            try:
                option_index = int(
                    data.replace("answer_", "", 1)
                )
            except ValueError:
                answer_callback(callback_id)
                return

            process_answer(
                chat_id,
                callback_id,
                option_index
            )

        return

    message = update.get("message")

    if not isinstance(message, dict):
        return

    chat = message.get("chat") or {}
    chat_id = chat.get("id")

    if chat_id is None:
        return

    text = str(
        message.get("text", "")
    ).strip()

    if text in ["/start", "شروع", "شروع چالش"]:
        with games_lock:
            existing = games.get(chat_id)

            if existing and not existing.get("finished"):
                send_message(
                    chat_id,
                    "⚠️ یک چالش در حال اجراست.\n"
                    "برای پایان آن، «⛔ توقف چالش» را بزنید.",
                    stop_keyboard(),
                    context="start_existing"
                )
                return

        send_message(
            chat_id,
            (
                "🌿 <b>به چالش شعرانه خوش آمدید!</b>\n\n"
                "دانسته‌های خود را در ادبیات فارسی "
                "در سه سطح آشنایی، دانایی و استادی محک بزنید.\n\n"
                "هر چالش شامل ۷ سؤال است."
            ),
            main_keyboard(),
            context="start"
        )
        return

    if text == "⛔ توقف چالش":
        stop_game(chat_id)
        return

    if text in ["💬 ارتباط با مدیر", "ارتباط با مدیر"]:
        send_message(
            chat_id,
            MANAGER_TEXT,
            main_keyboard(),
            context="manager"
        )
        return

    if text in ["🌿 درباره ما", "درباره ما"]:
        send_message(
            chat_id,
            ABOUT_TEXT,
            main_keyboard(),
            context="about"
        )
        return

    if text in ["🤖 سایر بات‌ها", "سایر بات‌ها"]:
        send_message(
            chat_id,
            OTHER_BOTS_TEXT,
            main_keyboard(),
            context="other_bots"
        )
        return


app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json(
            silent=True
        )

        if update:
            threading.Thread(
                target=handle_update,
                args=(update,),
                daemon=True
            ).start()

        return jsonify({
            "ok": True
        })

    except Exception as e:
        print(f"Webhook error: {e}")

        return jsonify({
            "ok": False
        }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "10000"
            )
        )
        )
