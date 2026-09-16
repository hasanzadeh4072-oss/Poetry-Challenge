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

# قفل اختصاصی هر کاربر
game_locks = {}

# قفل ایجاد قفل‌های کاربران
game_locks_guard = threading.Lock()


def get_game_lock(chat_id):
    """دریافت قفل اختصاصی هر کاربر."""

    with game_locks_guard:
        if chat_id not in game_locks:
            game_locks[chat_id] = threading.Lock()

        return game_locks[chat_id]


def api_request(method, data=None):
    """ارسال درخواست به API سروش‌پلاس بدون چاپ توکن."""

    start_time = time.monotonic()

    try:
        url = f"{API_BASE}/{method}"

        print(f"API START: {method}")

        response = requests.post(
            url,
            json=data or {},
            timeout=20
        )

        elapsed = time.monotonic() - start_time

        print(
            f"API END: {method} "
            f"status={response.status_code} "
            f"time={elapsed:.2f}s"
        )

        if response.status_code != 200:
            print(
                f"API Error {method}: "
                f"{response.status_code} - {response.text}"
            )
            return None

        return response.json()

    except Exception as e:
        elapsed = time.monotonic() - start_time

        print(
            f"API Exception {method}: "
            f"time={elapsed:.2f}s - {e}"
        )

        return None


def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if reply_markup is not None:
        data["reply_markup"] = reply_markup

    return api_request("sendMessage", data)


def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if reply_markup is not None:
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


def answer_callback_async(callback_id):
    """پاسخ به Callback بدون متوقف کردن روند بازی."""

    if not callback_id:
        return

    threading.Thread(
        target=answer_callback,
        args=(callback_id,),
        daemon=True
    ).start()


def build_options(question):
    """
    ساخت گزینه‌ها برای سؤال.

    صحیح/غلط:
    دقیقاً دو گزینه ساخته می‌شود.

    چندگزینه‌ای:
    ابتدا از «گزینه‌ها» استفاده می‌شود.
    در غیر این صورت از «پاسخ صحیح» و
    «سایر گزینه‌های چالشی» ساخته می‌شود.
    """

    question_type = str(
        question.get("نوع سؤال", "")
    ).strip()

    if question_type in [
        "صحیح/غلط",
        "صحیح یا غلط",
        "درست/غلط",
        "درست یا غلط",
        "صحیح-غلط",
    ]:
        return ["صحیح", "غلط"]

    options = question.get("گزینه‌ها")

    if isinstance(options, list):
        clean_options = []

        for option in options:
            if option is None:
                continue

            option = str(option).strip()

            if not option:
                continue

            if option in ["-", "—", "–"]:
                continue

            if option not in clean_options:
                clean_options.append(option)

        if len(clean_options) >= 2:
            return clean_options

    correct_answer = question.get("پاسخ صحیح")

    if not correct_answer:
        return None

    correct_answer = str(correct_answer).strip()

    if not correct_answer or correct_answer in ["-", "—", "–"]:
        return None

    other_options = question.get(
        "سایر گزینه‌های چالشی",
        []
    )

    if isinstance(other_options, list):
        others = other_options[:]

    elif isinstance(other_options, str):
        others = [
            item.strip()
            for item in other_options.split(",")
            if item.strip()
        ]

    else:
        others = []

    options = [correct_answer] + others

    unique_options = []

    for option in options:
        if option is None:
            continue

        option = str(option).strip()

        if not option:
            continue

        if option in ["-", "—", "–"]:
            continue

        if option not in unique_options:
            unique_options.append(option)

    if len(unique_options) < 2:
        return None

    return unique_options


def load_questions():
    """بارگذاری سؤال‌های سه سطح."""

    questions = {}

    for level, filename in LEVEL_FILES.items():
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                print(
                    f"{filename}: "
                    "JSON باید یک لیست باشد."
                )
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

                options = build_options(q)

                if not options:
                    continue

                if q["پاسخ صحیح"] not in options:
                    continue

                q["گزینه‌ها"] = options

                valid_questions.append(q)

            questions[level] = valid_questions

            print(
                f"{filename}: "
                f"{len(valid_questions)} سؤال معتبر بارگذاری شد."
            )

        except FileNotFoundError:
            print(
                f"فایل پیدا نشد: {filename}"
            )
            questions[level] = []

        except Exception as e:
            print(
                f"خطا در خواندن {filename}: {e}"
            )
            questions[level] = []

    return questions


QUESTIONS = load_questions()


# --------------------------------------------------
# Reply Keyboard
# --------------------------------------------------

def main_keyboard():
    """صفحه‌کلید اصلی خارج از کادر پیام."""

    return {
        "keyboard": [
            [
                {
                    "text": "شروع چالش"
                }
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }


def level_keyboard():
    """انتخاب سطح خارج از کادر پیام."""

    return {
        "keyboard": [
            [
                {
                    "text": "آشنایی"
                },
                {
                    "text": "دانایی"
                },
                {
                    "text": "استادی"
                }
            ],
            [
                {
                    "text": "⛔ توقف چالش"
                }
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }


def stop_keyboard():
    """صفحه‌کلید توقف چالش خارج از کادر پیام."""

    return {
        "keyboard": [
            [
                {
                    "text": "⛔ توقف چالش"
                }
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }


# --------------------------------------------------
# Inline Keyboard فقط برای پاسخ سؤال
# --------------------------------------------------

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


# --------------------------------------------------
# پیام‌ها
# --------------------------------------------------

def start_message():
    return (
        "📚 <b>چالش شعرانه</b>\n\n"
        "در این بازی ۷ سؤال از سطح انتخابی شما نمایش داده می‌شود.\n"
        "برای هر سؤال ۱ دقیقه و ۳۰ ثانیه فرصت دارید.\n\n"
        "✅ پاسخ صحیح: +۱۰۰ امتیاز\n"
        "❌ هر دو پاسخ غلط: −۱۵ امتیاز\n"
        "⏱ بدون پاسخ: ۰ امتیاز\n\n"
        "برای شروع، سطح چالش خود را انتخاب کنید:"
    )


# --------------------------------------------------
# آماده‌سازی سؤال
# --------------------------------------------------

def prepare_question(question):
    """آماده‌سازی سؤال و تصادفی‌کردن گزینه‌ها."""

    options = list(question["گزینه‌ها"])
    random.shuffle(options)

    return {
        "question": question,
        "options": options,
    }


# --------------------------------------------------
# ارسال سؤال
# --------------------------------------------------

def send_question(chat_id):

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

    message = result.get(
        "result",
        {}
    )

    game["message_id"] = message.get(
        "message_id"
    )

    game["question_started"] = time.monotonic()

    game["question_deadline"] = (
        game["question_started"]
        + QUESTION_TIME
    )

    timer_id = object()

    game["timer_id"] = timer_id

    timer = threading.Thread(
        target=question_timeout,
        args=(
            chat_id,
            index,
            timer_id
        ),
        daemon=True
    )

    timer.start()


# --------------------------------------------------
# پایان زمان سؤال
# --------------------------------------------------

def question_timeout(
    chat_id,
    question_index,
    timer_id
):
    """بررسی پایان دقیق زمان پاسخ."""

    game = games.get(chat_id)

    if not game:
        return

    start_time = game.get(
        "question_started"
    )

    if start_time is None:
        return

    deadline = game.get(
        "question_deadline",
        start_time + QUESTION_TIME
    )

    remaining = deadline - time.monotonic()

    if remaining > 0:
        time.sleep(remaining)

    game = games.get(chat_id)

    if not game:
        return

    if game.get("current") != question_index:
        return

    if game.get("timer_id") is not timer_id:
        return

    if game.get("answered"):
        return

    game["answered"] = True
    game["timer_id"] = None

    if game.get("message_id"):
        edit_message(
            chat_id,
            game["message_id"],
            (
                f"⏱ <b>زمان سؤال "
                f"{question_index + 1} تمام شد.</b>\n\n"
                "امتیاز این سؤال: ۰"
            )
        )

    game["current"] += 1
    game["answered"] = False

    time.sleep(1)

    if chat_id not in games:
        return

    if game["current"] >= QUESTION_COUNT:
        finish_game(chat_id)
    else:
        send_question(chat_id)


# --------------------------------------------------
# پردازش پاسخ
# --------------------------------------------------

def process_answer(
    chat_id,
    callback_id,
    option_index
):

    game = games.get(chat_id)

    if not game:
        answer_callback_async(callback_id)
        return

    if game.get("answered"):
        answer_callback_async(callback_id)
        return

    current = game["current"]

    if current >= QUESTION_COUNT:
        answer_callback_async(callback_id)
        return

    deadline = game.get(
        "question_deadline"
    )

    if (
        deadline is not None
        and time.monotonic() >= deadline
    ):

        game["answered"] = True
        game["timer_id"] = None

        answer_callback_async(callback_id)

        if game.get("message_id"):
            edit_message(
                chat_id,
                game["message_id"],
                (
                    f"⏱ <b>زمان سؤال "
                    f"{current + 1} تمام شد.</b>\n\n"
                    "امتیاز این سؤال: ۰"
                )
            )

        game["current"] += 1
        game["answered"] = False

        time.sleep(1)

        if chat_id not in games:
            return

        if game["current"] >= QUESTION_COUNT:
            finish_game(chat_id)
        else:
            send_question(chat_id)

        return

    prepared = game["questions"][current]

    question = prepared["question"]
    options = prepared["options"]

    try:
        option_index = int(option_index)

    except (
        ValueError,
        TypeError
    ):
        answer_callback_async(callback_id)
        return

    if (
        option_index < 0
        or option_index >= len(options)
    ):
        answer_callback_async(callback_id)
        return

    selected_answer = options[option_index]

    correct_answer = question["پاسخ صحیح"]

    game["answered"] = True
    game["timer_id"] = None

    if selected_answer == correct_answer:

        game["score"] += 100

        result_text = (
            "✅ <b>پاسخ صحیح</b>\n\n"
            "امتیاز این سؤال: +۱۰۰\n"
            f"امتیاز فعلی: {game['score']}"
        )

    else:

        game["wrong_answers"] += 1

        if game["wrong_answers"] % 2 == 0:

            game["score"] -= 15

            penalty_text = (
                "امتیاز این سؤال: −۱۵"
            )

        else:

            penalty_text = (
                "امتیاز این سؤال: ۰"
            )

        result_text = (
            "❌ <b>پاسخ غلط</b>\n\n"
            f"پاسخ صحیح: {correct_answer}\n"
            f"{penalty_text}\n"
            f"امتیاز فعلی: {game['score']}"
        )

    answer_callback_async(callback_id)

    if game.get("message_id"):
        edit_message(
            chat_id,
            game["message_id"],
            result_text
        )

    game["current"] += 1
    game["answered"] = False

    time.sleep(1)

    if chat_id not in games:
        return

    if game["current"] >= QUESTION_COUNT:
        finish_game(chat_id)
    else:
        send_question(chat_id)


# --------------------------------------------------
# پایان بازی
# --------------------------------------------------

def finish_game(chat_id):

    lock = get_game_lock(chat_id)

    with lock:
        game = games.pop(
            chat_id,
            None
        )

    if not game:
        return

    score = game["score"]

    level = LEVEL_NAMES.get(
        game["level"],
        game["level"]
    )

    if score >= 600:

        message = (
            "🏆 فوق‌العاده بود! "
            "شما واقعاً در این سطح درخشیدید."
        )

    elif score >= 400:

        message = (
            "👏 عالی بود! "
            "عملکرد بسیار خوبی داشتید."
        )

    elif score >= 200:

        message = (
            "🌿 خوب بود! "
            "با کمی تمرین بهتر هم می‌شوید."
        )

    else:

        message = (
            "📚 این پایان راه نیست؛ "
            "یک بار دیگر امتحان کنید."
        )

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


# --------------------------------------------------
# توقف چالش
# --------------------------------------------------

def stop_game(chat_id):

    lock = get_game_lock(chat_id)

    with lock:
        game = games.pop(
            chat_id,
            None
        )

    if not game:

        send_message(
            chat_id,
            "ℹ️ در حال حاضر چالش فعالی ندارید.",
            main_keyboard()
        )

        return

    send_message(
        chat_id,
        (
            "⛔ <b>چالش متوقف شد.</b>\n\n"
            "شما اکنون آماده شروع یک چالش جدید هستید."
        ),
        main_keyboard()
    )


# --------------------------------------------------
# شروع بازی
# --------------------------------------------------

def start_game(chat_id, level):

    lock = get_game_lock(chat_id)

    with lock:

        if chat_id in games:

            send_message(
                chat_id,
                (
                    "⚠️ <b>یک چالش در حال اجراست.</b>\n\n"
                    "ابتدا چالش فعلی را به پایان برسانید "
                    "یا با دکمه «⛔ توقف چالش» آن را متوقف کنید."
                ),
                stop_keyboard()
            )

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

        selected = random.sample(
            available,
            QUESTION_COUNT
        )

        prepared_questions = [
            prepare_question(q)
            for q in selected
        ]

        games[chat_id] = {
            "level": level,
            "questions": prepared_questions,
            "current": 0,
            "score": 0,
            "wrong_answers": 0,
            "message_id": None,
            "question_started": None,
            "question_deadline": None,
            "timer_id": None,
            "answered": False,
        }

    # صفحه‌کلید توقف در زمان بازی
    send_message(
        chat_id,
        "⛔ برای توقف چالش در هر لحظه، دکمه زیر را بزنید.",
        stop_keyboard()
    )

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

            if chat_id not in games:

                delete_message(
                    chat_id,
                    countdown_id
                )

                return

            edit_message(
                chat_id,
                countdown_id,
                "۲"
            )

            time.sleep(0.7)

            if chat_id not in games:

                delete_message(
                    chat_id,
                    countdown_id
                )

                return

            edit_message(
                chat_id,
                countdown_id,
                "۳"
            )

            time.sleep(0.7)

            if chat_id not in games:

                delete_message(
                    chat_id,
                    countdown_id
                )

                return

            delete_message(
                chat_id,
                countdown_id
            )

    if chat_id not in games:
        return

    send_message(
        chat_id,
        (
            f"🎮 <b>چالش {LEVEL_NAMES[level]}</b>\n\n"
            "شروع شد!"
        )
    )

    time.sleep(0.5)

    if chat_id not in games:
        return

    send_question(chat_id)


# --------------------------------------------------
# پردازش پیام‌ها
# --------------------------------------------------

def handle_update(update):

    # پیام معمولی
    message = update.get("message")

    if message:

        chat = message.get(
            "chat",
            {}
        )

        chat_id = chat.get("id")

        text = message.get(
            "text",
            ""
        )

        if not chat_id:
            return

        # توقف
        if text == "⛔ توقف چالش":

            stop_game(chat_id)

            return

        # شروع
        if text in [
            "/start",
            "شروع",
            "شروع چالش"
        ]:

            if chat_id in games:

                send_message(
                    chat_id,
                    (
                        "⚠️ <b>یک چالش در حال اجراست.</b>\n\n"
                        "برای شروع چالش جدید، ابتدا چالش فعلی را "
                        "به پایان برسانید یا آن را متوقف کنید."
                    ),
                    stop_keyboard()
                )

                return

            # نمایش پیام و هم‌زمان نمایش گزینه‌های سطح
            send_message(
                chat_id,
                start_message(),
                level_keyboard()
            )

            return

        # انتخاب سطح از Reply Keyboard
        level_map = {
            "آشنایی": "ashenaei",
            "دانایی": "danaei",
            "استادی": "ostad",
        }

        if text in level_map:

            if chat_id in games:

                send_message(
                    chat_id,
                    (
                        "⚠️ <b>یک چالش در حال اجراست.</b>\n\n"
                        "ابتدا چالش فعلی را تمام کنید "
                        "یا آن را متوقف کنید."
                    ),
                    stop_keyboard()
                )

                return

            start_game(
                chat_id,
                level_map[text]
            )

            return

        return

    # Callback Query
    callback = update.get(
        "callback_query"
    )

    if not callback:
        return

    callback_id = callback.get(
        "id"
    )

    data = callback.get(
        "data",
        ""
    )

    chat = (
        callback
        .get("message", {})
        .get("chat", {})
    )

    chat_id = chat.get("id")

    if not chat_id:

        answer_callback_async(
            callback_id
        )

        return

    # پاسخ سؤال
    if data.startswith("answer_"):

        option_index = data.replace(
            "answer_",
            "",
            1
        )

        process_answer(
            chat_id,
            callback_id,
            option_index
        )

        return

    answer_callback_async(
        callback_id
    )


# --------------------------------------------------
# Webhook
# --------------------------------------------------

@app.route(
    "/webhook",
    methods=["POST"]
)
def webhook():

    try:

        update = request.get_json(
            silent=True
        )

        if not update:
            return "OK"

        threading.Thread(
            target=handle_update,
            args=(update,),
            daemon=True
        ).start()

        return "OK"

    except Exception as e:

        print(
            f"Webhook Error: {e}"
        )

        return "OK"


# --------------------------------------------------
# اجرای برنامه
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                5000
            )
        )
    )
