import os
import json
import random
import time
import threading
import requests

from flask import Flask, request, jsonify


# =========================================================
# تنظیمات
# =========================================================

TOKEN = os.getenv("SOROUSH_TOKEN")

API_BASE = f"https://api.splus.ir/bot{TOKEN}" if TOKEN else ""

QUESTION_TIME = 90
QUESTIONS_PER_GAME = 7

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


# =========================================================
# Flask
# =========================================================

app = Flask(__name__)


# =========================================================
# وضعیت بازی کاربران
# =========================================================

games = {}
game_locks = {}


def get_lock(chat_id):
    if chat_id not in game_locks:
        game_locks[chat_id] = threading.Lock()
    return game_locks[chat_id]


# =========================================================
# بارگذاری سؤال‌ها
# =========================================================

QUESTIONS = {}


def load_questions():
    global QUESTIONS

    QUESTIONS = {}

    for level, filename in LEVEL_FILES.items():

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                print(f"[ERROR] {filename} باید آرایه JSON باشد.")
                QUESTIONS[level] = []
                continue

            valid_questions = []

            for q in data:
                if not isinstance(q, dict):
                    continue

                if not q.get("سؤال"):
                    continue

                if not q.get("پاسخ صحیح"):
                    continue

                valid_questions.append(q)

            QUESTIONS[level] = valid_questions

            print(
                f"[OK] {filename}: "
                f"{len(valid_questions)} سوال بارگذاری شد."
            )

        except Exception as e:
            QUESTIONS[level] = []
            print(f"[ERROR] خطا در بارگذاری {filename}: {e}")


load_questions()


# =========================================================
# API
# =========================================================

def api_call(method, data=None):
    if not TOKEN:
        print("[ERROR] SOROUSH_TOKEN تنظیم نشده است.")
        return None

    url = f"{API_BASE}/{method}"

    try:
        response = requests.post(
            url,
            json=data or {},
            timeout=20
        )

        try:
            result = response.json()
        except Exception:
            result = None

        if response.status_code != 200:
            print(
                f"[API ERROR] {method} "
                f"status={response.status_code} "
                f"body={response.text[:500]}"
            )

        return result

    except Exception as e:
        print(f"[API ERROR] {method}: {e}")
        return None


def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    return api_call("sendMessage", data)


def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    return api_call("editMessageText", data)


def delete_message(chat_id, message_id):
    return api_call(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id
        }
    )


def answer_callback(callback_id):
    if not callback_id:
        return

    api_call(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


# =========================================================
# کیبوردها
# =========================================================

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
                    "text": "🎯 آشنایی",
                    "callback_data": "level:ashenaei"
                }
            ],
            [
                {
                    "text": "🎯 دانایی",
                    "callback_data": "level:danaei"
                }
            ],
            [
                {
                    "text": "🎯 استادی",
                    "callback_data": "level:ostad"
                }
            ]
        ]
    }


# =========================================================
# شروع چالش
# =========================================================

def show_start(chat_id):

    text = (
        "🎯 <b>چالش شعرانه</b>\n\n"
        "به چالش ادبیات و شعر خوش آمدید.\n\n"
        "🎯 ۳ سطح: آشنایی، دانایی، استادی\n"
        "🎮 هر سطح مستقل و شامل ۷ سؤال\n"
        "🔀 سؤال‌ها تصادفی و بدون تکرار انتخاب می‌شوند.\n"
        "⏱️ زمان هر سؤال: ۱:۳۰ دقیقه\n"
        "✅ پاسخ صحیح: +۱۰۰ امتیاز\n"
        "❌ پاسخ غلط: −۱۵ امتیاز\n"
        "⏭️ بدون پاسخ: ۰ امتیاز\n"
        "🏁 پس از ۷ سؤال، بازی تمام و نتیجه نهایی نمایش داده می‌شود.\n\n"
        "برای شروع، سطح خود را انتخاب کنید:"
    )

    send_message(
        chat_id,
        text,
        level_keyboard()
    )


# =========================================================
# شمارش ۱، ۲، ۳
# =========================================================

def countdown(chat_id):

    result = send_message(
        chat_id,
        "۱"
    )

    if not result:
        return

    message_id = (
        result.get("result", {}).get("message_id")
        if isinstance(result, dict)
        else None
    )

    if not message_id:
        return

    time.sleep(0.8)

    edit_message(
        chat_id,
        message_id,
        "۲"
    )

    time.sleep(0.8)

    edit_message(
        chat_id,
        message_id,
        "۳"
    )

    time.sleep(0.8)

    delete_message(
        chat_id,
        message_id
    )


# =========================================================
# آماده‌سازی سؤال
# =========================================================

def prepare_question(question):

    options = question.get("گزینه‌ها")

    if not isinstance(options, list):
        options = []

    options = [
        str(option)
        for option in options
        if option is not None and str(option).strip()
    ]

    correct = str(question.get("پاسخ صحیح", "")).strip()

    # اگر گزینه‌ها ناقص باشند، سؤال نمایش داده نمی‌شود.
    if not options:
        return None

    # پاسخ صحیح حتماً باید در گزینه‌ها وجود داشته باشد.
    if correct not in options:
        return None

    random.shuffle(options)

    return {
        "question": question,
        "options": options,
        "correct": correct
    }


# =========================================================
# ارسال سؤال
# =========================================================

def send_question(chat_id):

    with get_lock(chat_id):

        game = games.get(chat_id)

        if not game:
            return

        if game["question_index"] >= QUESTIONS_PER_GAME:
            finish_game(chat_id)
            return

        questions = game["questions"]

        if not questions:
            finish_game(chat_id)
            return

        question = questions[game["question_index"]]

        prepared = prepare_question(question)

        if not prepared:
            game["question_index"] += 1
            send_question(chat_id)
            return

        game["current_question"] = prepared
        game["question_started"] = time.time()

        q_number = game["question_index"] + 1

        text = (
            f"🎮 <b>سؤال {q_number} از {QUESTIONS_PER_GAME}</b>\n\n"
            f"{prepared['question'].get('سؤال', '')}\n\n"
            "⏱️ زمان پاسخ‌گویی: ۱:۳۰"
        )

        buttons = []

        for index, option in enumerate(prepared["options"]):
            buttons.append([
                {
                    "text": option,
                    "callback_data": f"answer:{index}"
                }
            ])

        result = send_message(
            chat_id,
            text,
            {
                "inline_keyboard": buttons
            }
        )

        message_id = None

        if isinstance(result, dict):
            message_id = (
                result.get("result", {}).get("message_id")
            )

        game["message_id"] = message_id

        # تایمر سؤال
        thread = threading.Thread(
            target=question_timeout,
            args=(
                chat_id,
                game["question_index"],
                message_id
            ),
            daemon=True
        )

        thread.start()


# =========================================================
# تایمر سؤال
# =========================================================

def question_timeout(chat_id, question_index, message_id):

    time.sleep(QUESTION_TIME)

    with get_lock(chat_id):

        game = games.get(chat_id)

        if not game:
            return

        # اگر کاربر قبلاً پاسخ داده، این تایمر دیگر کاری ندارد.
        if game["question_index"] != question_index:
            return

        if game.get("current_question") is None:
            return

        # بدون پاسخ
        game["score"] += 0
        game["unanswered"] += 1

        if message_id:
            edit_message(
                chat_id,
                message_id,
                "⏰ <b>زمان پاسخ‌گویی تمام شد.</b>\n\n"
                "⏭️ بدون پاسخ: ۰ امتیاز"
            )

        game["current_question"] = None
        game["question_index"] += 1

    time.sleep(0.7)

    send_question(chat_id)


# =========================================================
# پردازش پاسخ
# =========================================================

def process_answer(chat_id, callback_id, option_index):

    answer_callback(callback_id)

    with get_lock(chat_id):

        game = games.get(chat_id)

        if not game:
            return

        current = game.get("current_question")

        if not current:
            return

        # بررسی زمان
        started = game.get("question_started", 0)

        if time.time() - started >= QUESTION_TIME:
            return

        options = current["options"]

        try:
            option_index = int(option_index)
        except Exception:
            return

        if option_index < 0 or option_index >= len(options):
            return

        selected = options[option_index]
        correct = current["correct"]

        q_number = game["question_index"] + 1

        if selected == correct:

            game["score"] += 100
            game["correct"] += 1

            result_text = (
                "✅ <b>پاسخ صحیح!</b>\n\n"
                "+۱۰۰ امتیاز"
            )

        else:

            game["score"] -= 15
            game["wrong"] += 1

            result_text = (
                "❌ <b>پاسخ غلط!</b>\n\n"
                "−۱۵ امتیاز\n\n"
                f"پاسخ صحیح: <b>{correct}</b>"
            )

        message_id = game.get("message_id")

        if message_id:
            edit_message(
                chat_id,
                message_id,
                result_text
            )

        game["current_question"] = None
        game["question_index"] += 1

        finished = (
            game["question_index"]
            >= QUESTIONS_PER_GAME
        )

    time.sleep(0.8)

    if finished:
        finish_game(chat_id)
    else:
        send_question(chat_id)


# =========================================================
# پایان بازی
# =========================================================

def finish_game(chat_id):

    with get_lock(chat_id):

        game = games.get(chat_id)

        if not game:
            return

        level_name = LEVEL_NAMES.get(
            game["level"],
            game["level"]
        )

        score = game["score"]
        correct = game["correct"]
        wrong = game["wrong"]
        unanswered = game["unanswered"]

        if score >= 700:
            message = "🏆 فوق‌العاده بود! شما یک قهرمان شعرانه هستید."
        elif score >= 500:
            message = "👏 عالی بود! دانش ادبی شما قابل توجه است."
        elif score >= 300:
            message = "🌿 خوب بود! کمی تمرین بیشتر و بهتر هم می‌شوید."
        elif score >= 0:
            message = "📚 چالش به پایان رسید؛ وقت آن است بیشتر با شعر و ادبیات همراه شوید."
        else:
            message = "😄 این بار سخت گذشت! یک بار دیگر شانس خودتان را امتحان کنید."

        text = (
            "🏁 <b>چالش به پایان رسید!</b>\n\n"
            f"🎯 سطح: <b>{level_name}</b>\n"
            f"⭐ امتیاز نهایی: <b>{score}</b>\n\n"
            f"✅ پاسخ صحیح: {correct}\n"
            f"❌ پاسخ غلط: {wrong}\n"
            f"⏭️ بدون پاسخ: {unanswered}\n\n"
            f"{message}\n\n"
            "🌿 دوباره بازی کنید و رکورد خودتان را بهتر کنید."
        )

        send_message(
            chat_id,
            text,
            main_keyboard()
        )

        del games[chat_id]


# =========================================================
# انتخاب سطح
# =========================================================

def start_level(chat_id, level):

    with get_lock(chat_id):

        if level not in QUESTIONS:
            send_message(
                chat_id,
                "❌ این سطح در حال حاضر در دسترس نیست.",
                main_keyboard()
            )
            return

        available = QUESTIONS[level]

        if len(available) < QUESTIONS_PER_GAME:
            send_message(
                chat_id,
                "❌ تعداد سؤال‌های این سطح برای شروع بازی کافی نیست.",
                main_keyboard()
            )
            return

        selected_questions = random.sample(
            available,
            QUESTIONS_PER_GAME
        )

        games[chat_id] = {
            "level": level,
            "questions": selected_questions,
            "question_index": 0,
            "score": 0,
            "correct": 0,
            "wrong": 0,
            "unanswered": 0,
            "current_question": None,
            "question_started": 0,
            "message_id": None,
        }

    # شمارش بیرون از lock
    countdown(chat_id)

    send_message(
        chat_id,
        (
            f"🎮 <b>بازی سطح {LEVEL_NAMES[level]} شروع شد!</b>\n\n"
            "۷ سؤال در پیش دارید.\n"
            "⏱️ برای هر سؤال ۱ دقیقه و ۳۰ ثانیه فرصت دارید."
        )
    )

    time.sleep(0.8)

    send_question(chat_id)


# =========================================================
# دریافت پیام‌ها
# =========================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    try:
        update = request.get_json(force=True)

    except Exception:
        return jsonify({"ok": True})


    # -----------------------------------------------------
    # پیام معمولی
    # -----------------------------------------------------

    message = update.get("message")

    if message:

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        text = message.get("text", "")

        if not chat_id:
            return jsonify({"ok": True})

        if text in [
            "/start",
            "شروع",
            "شروع چالش"
        ]:

            show_start(chat_id)

        return jsonify({"ok": True})


    # -----------------------------------------------------
    # Callback Query
    # -----------------------------------------------------

    callback = update.get("callback_query")

    if callback:

        callback_id = callback.get("id")
        data = callback.get("data", "")

        callback_message = callback.get("message", {})
        chat = callback_message.get("chat", {})

        chat_id = chat.get("id")

        if not chat_id:
            answer_callback(callback_id)
            return jsonify({"ok": True})


        # شروع چالش
        if data == "start_challenge":

            answer_callback(callback_id)

            show_start(chat_id)

            return jsonify({"ok": True})


        # انتخاب سطح
        if data.startswith("level:"):

            answer_callback(callback_id)

            level = data.split(":", 1)[1]

            # جلوگیری از شروع بازی دوم هم‌زمان
            if chat_id in games:

                send_message(
                    chat_id,
                    "⚠️ شما در حال حاضر یک چالش فعال دارید."
                )

                return jsonify({"ok": True})

            start_level(
                chat_id,
                level
            )

            return jsonify({"ok": True})


        # پاسخ سؤال
        if data.startswith("answer:"):

            option_index = data.split(":", 1)[1]

            process_answer(
                chat_id,
                callback_id,
                option_index
            )

            return jsonify({"ok": True})


        answer_callback(callback_id)

    return jsonify({"ok": True})


# =========================================================
# تنظیم Webhook
# =========================================================

def set_webhook():

    if not TOKEN:
        print("[WARNING] SOROUSH_TOKEN وجود ندارد؛ webhook تنظیم نشد.")
        return

    external_url = os.getenv("RENDER_EXTERNAL_URL")

    if not external_url:
        external_url = os.getenv("WEBHOOK_URL")

    if not external_url:
        print(
            "[WARNING] RENDER_EXTERNAL_URL یا WEBHOOK_URL "
            "وجود ندارد؛ webhook تنظیم نشد."
        )
        return

    if external_url.endswith("/webhook"):
        webhook_url = external_url
    else:
        webhook_url = external_url.rstrip("/") + "/webhook"

    result = api_call(
        "setWebhook",
        {
            "url": webhook_url
        }
    )

    print(
        f"[WEBHOOK] {webhook_url}"
    )

    print(
        f"[WEBHOOK RESULT] {result}"
    )


# =========================================================
# اجرا
# =========================================================

if __name__ == "__main__":

    set_webhook()

    port = int(
        os.getenv("PORT", "5000")
    )

    app.run(
        host="0.0.0.0",
        port=port
            )
