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


# ==================================================
# وضعیت بازی کاربران
# ==================================================

games = {}

game_locks = {}
game_locks_guard = threading.Lock()


def get_game_lock(chat_id):
    """دریافت قفل اختصاصی هر کاربر."""

    with game_locks_guard:
        if chat_id not in game_locks:
            game_locks[chat_id] = threading.Lock()

        return game_locks[chat_id]


# ==================================================
# API
# ==================================================

def api_request(method, data=None, context=""):

    start_time = time.monotonic()

    try:

        url = f"{API_BASE}/{method}"

        if context:
            print(
                f"API START: {method} | {context}"
            )
        else:
            print(
                f"API START: {method}"
            )

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
            + (
                f" | {context}"
                if context
                else ""
            )
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
            + (
                f" | {context}"
                if context
                else ""
            )
        )

        return None


def send_message(
    chat_id,
    text,
    reply_markup=None,
    context=""
):

    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if reply_markup is not None:
        data["reply_markup"] = reply_markup

    return api_request(
        "sendMessage",
        data,
        context
    )


def edit_message(
    chat_id,
    message_id,
    text,
    reply_markup=None,
    context=""
):

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if reply_markup is not None:
        data["reply_markup"] = reply_markup

    return api_request(
        "editMessageText",
        data,
        context
    )


def delete_message(
    chat_id,
    message_id,
    context=""
):

    return api_request(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id,
        },
        context
    )


def answer_callback(callback_id):

    if not callback_id:
        return

    return api_request(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        },
        "callback"
    )


def answer_callback_async(callback_id):

    if not callback_id:
        return

    threading.Thread(
        target=answer_callback,
        args=(callback_id,),
        daemon=True
    ).start()


# ==================================================
# ساخت گزینه‌های سؤال
# ==================================================

def build_options(question):

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

        return [
            "صحیح",
            "غلط"
        ]

    options = question.get("گزینه‌ها")

    if isinstance(options, list):

        clean_options = []

        for option in options:

            if option is None:
                continue

            option = str(option).strip()

            if not option:
                continue

            if option in [
                "-",
                "—",
                "–"
            ]:
                continue

            if option not in clean_options:
                clean_options.append(option)

        if len(clean_options) >= 2:
            return clean_options

    correct_answer = question.get(
        "پاسخ صحیح"
    )

    if not correct_answer:
        return None

    correct_answer = str(
        correct_answer
    ).strip()

    if not correct_answer:
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

    options = [
        correct_answer
    ] + others

    unique_options = []

    for option in options:

        if option is None:
            continue

        option = str(option).strip()

        if not option:
            continue

        if option in [
            "-",
            "—",
            "–"
        ]:
            continue

        if option not in unique_options:
            unique_options.append(option)

    if len(unique_options) < 2:
        return None

    return unique_options


# ==================================================
# بارگذاری سؤال‌ها
# ==================================================

def load_questions():

    questions = {}

    for level, filename in LEVEL_FILES.items():

        try:

            with open(
                filename,
                "r",
                encoding="utf-8"
            ) as f:

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


# ==================================================
# Reply Keyboard
# ==================================================

def main_keyboard():

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
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
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
        "one_time_keyboard": False
    }


# ==================================================
# Inline Keyboard پاسخ سؤال
# ==================================================

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


# ==================================================
# پیام خوش‌آمدگویی
# ==================================================

def start_message():

    return (
        "📚 <b>چالش شعرانه</b>\n\n"
        "در این بازی ۷ سؤال از سطح انتخابی شما نمایش داده می‌شود.\n"
        "برای هر سؤال ۱ دقیقه و ۳۰ ثانیه فرصت دارید.\n\n"
        "✅ پاسخ صحیح: +۱۰۰ امتیاز\n"
        "❌ هر دو پاسخ غلط: −۱۵ امتیاز\n"
        "⏱ بدون پاسخ: ۰ امتیاز\n\n"
        "برای شروع، دکمه «شروع چالش» را بزنید."
    )


# ==================================================
# آماده‌سازی سؤال
# ==================================================

def prepare_question(question):

    options = list(
        question["گزینه‌ها"]
    )

    random.shuffle(options)

    return {
        "question": question,
        "options": options,
    }


# ==================================================
# ارسال سؤال
# ==================================================

def send_question(chat_id):

    lock = get_game_lock(chat_id)

    with lock:

        game = games.get(chat_id)

        if not game:
            return

        index = game["current"]

        if index >= QUESTION_COUNT:

            should_finish = True

        else:

            should_finish = False

            prepared = game["questions"][index]

            question = prepared["question"]
            options = prepared["options"]

            text = (
                f"❓ <b>سؤال {index + 1} از "
                f"{QUESTION_COUNT}</b>\n\n"
                f"{question['سؤال']}"
            )

    if should_finish:

        finish_game(chat_id)

        return

    result = send_message(
        chat_id,
        text,
        answer_keyboard(options),
        context=f"question_{index + 1}"
    )

    if not result:
        return

    message = result.get(
        "result",
        {}
    )

    message_id = message.get(
        "message_id"
    )

    if not message_id:
        return

    lock = get_game_lock(chat_id)

    with lock:

        game = games.get(chat_id)

        if not game:
            return

        if game["current"] != index:
            return

        game["message_id"] = message_id

        game["question_started"] = (
            time.monotonic()
        )

        game["question_deadline"] = (
            game["question_started"]
            + QUESTION_TIME
        )

        timer_id = object()

        game["timer_id"] = timer_id

    threading.Thread(
        target=question_timeout,
        args=(
            chat_id,
            index,
            timer_id
        ),
        daemon=True
    ).start()


# ==================================================
# ادامه بازی
# ==================================================

def continue_game(
    chat_id,
    expected_current
):

    lock = get_game_lock(chat_id)

    with lock:

        game = games.get(chat_id)

        if not game:
            return

        if game["current"] != expected_current:
            return

        if expected_current >= QUESTION_COUNT:

            should_finish = True

        else:

            should_finish = False

    if should_finish:

        finish_game(chat_id)

    else:

        send_question(chat_id)


def schedule_next_question(
    chat_id,
    expected_current
):

    timer = threading.Timer(
        1.0,
        continue_game,
        args=(
            chat_id,
            expected_current
        )
    )

    timer.daemon = True
    timer.start()


# ==================================================
# تایمر سؤال
# ==================================================

def question_timeout(
    chat_id,
    question_index,
    timer_id
):

    lock = get_game_lock(chat_id)

    with lock:

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

    remaining = (
        deadline
        - time.monotonic()
    )

    if remaining > 0:
        time.sleep(remaining)

    lock = get_game_lock(chat_id)

    with lock:

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

        message_id = game.get(
            "message_id"
        )

        game["current"] += 1

        expected_current = game["current"]

    if message_id:

        edit_message(
            chat_id,
            message_id,
            (
                f"⏱ <b>زمان سؤال "
                f"{question_index + 1} تمام شد.</b>\n\n"
                "امتیاز این سؤال: ۰"
            ),
            context=f"timeout_question_{question_index + 1}"
        )

    lock = get_game_lock(chat_id)

    with lock:

        game = games.get(chat_id)

        if not game:
            return

        game["answered"] = False

    schedule_next_question(
        chat_id,
        expected_current
    )


# ==================================================
# پردازش پاسخ
# ==================================================

def process_answer(
    chat_id,
    callback_id,
    option_index
):

    lock = get_game_lock(chat_id)

    with lock:

        game = games.get(chat_id)

        if not game:

            answer_callback_async(
                callback_id
            )

            return

        if game.get("answered"):

            answer_callback_async(
                callback_id
            )

            return

        current = game["current"]

        if current >= QUESTION_COUNT:

            answer_callback_async(
                callback_id
            )

            return

        deadline = game.get(
            "question_deadline"
        )

        # ------------------------------------------
        # پاسخ بعد از پایان زمان
        # ------------------------------------------

        if (
            deadline is not None
            and time.monotonic() >= deadline
        ):

            game["answered"] = True
            game["timer_id"] = None

            message_id = game.get(
                "message_id"
            )

            game["current"] += 1

            expected_current = game["current"]

            timeout_case = True

        else:

            timeout_case = False

            prepared = game["questions"][current]

            question = prepared["question"]
            options = prepared["options"]

            try:

                option_index = int(
                    option_index
                )

            except (
                ValueError,
                TypeError
            ):

                answer_callback_async(
                    callback_id
                )

                return

            if (
                option_index < 0
                or option_index >= len(options)
            ):

                answer_callback_async(
                    callback_id
                )

                return

            selected_answer = options[
                option_index
            ]

            correct_answer = question[
                "پاسخ صحیح"
            ]

            game["answered"] = True
            game["timer_id"] = None

            message_id = game.get(
                "message_id"
            )

            # --------------------------------------
            # پاسخ صحیح
            # --------------------------------------

            if selected_answer == correct_answer:

                game["score"] += 100

                result_text = (
                    "✅ <b>پاسخ صحیح</b>\n\n"
                    "امتیاز این سؤال: +۱۰۰\n"
                    f"امتیاز فعلی: {game['score']}"
                )

            # --------------------------------------
            # پاسخ غلط
            # --------------------------------------

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

            game["current"] += 1

            expected_current = game["current"]

    # ----------------------------------------------
    # پاسخ Callback بدون معطل کردن منطق بازی
    # ----------------------------------------------

    answer_callback_async(
        callback_id
    )

    # ----------------------------------------------
    # پاسخ دیرهنگام
    # ----------------------------------------------

    if timeout_case:

        if message_id:

            edit_message(
                chat_id,
                message_id,
                (
                    f"⏱ <b>زمان سؤال "
                    f"{current + 1} تمام شد.</b>\n\n"
                    "امتیاز این سؤال: ۰"
                ),
                context=f"late_answer_question_{current + 1}"
            )

    # ----------------------------------------------
    # پاسخ عادی
    # ----------------------------------------------

    else:

        if message_id:

            edit_message(
                chat_id,
                message_id,
                result_text,
                context=f"answer_question_{current + 1}"
            )

    # ----------------------------------------------
    # سؤال بعدی
    # ----------------------------------------------

    lock = get_game_lock(chat_id)

    with lock:

        game = games.get(chat_id)

        if not game:
            return

        game["answered"] = False

    schedule_next_question(
        chat_id,
        expected_current
    )


# ==================================================
# پایان بازی
# ==================================================

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
        main_keyboard(),
        context="finish_game"
    )


# ==================================================
# توقف چالش
# ==================================================

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
            main_keyboard(),
            context="stop_no_game"
        )

        return

    send_message(
        chat_id,
        (
            "⛔ <b>چالش متوقف شد.</b>\n\n"
            "برای شروع یک چالش جدید، "
            "دکمه «شروع چالش» را بزنید."
        ),
        main_keyboard(),
        context="stop_game"
    )


# ==================================================
# شروع واقعی بازی
# ==================================================

def start_game(chat_id, level):

    lock = get_game_lock(chat_id)

    with lock:

        if chat_id in games:

            send_message(
                chat_id,
                (
                    "⚠️ <b>یک چالش در حال اجراست.</b>\n\n"
                    "ابتدا چالش فعلی را تمام کنید "
                    "یا آن را متوقف کنید."
                ),
                stop_keyboard(),
                context="start_existing_game"
            )

            return

        if level not in QUESTIONS:

            send_message(
                chat_id,
                "متأسفانه سؤال‌های این سطح در دسترس نیست.",
                main_keyboard(),
                context="level_unavailable"
            )

            return

        available = QUESTIONS[level]

        if len(available) < QUESTION_COUNT:

            send_message(
                chat_id,
                (
                    "تعداد سؤال‌های این سطح "
                    "برای شروع چالش کافی نیست."
                ),
                main_keyboard(),
                context="not_enough_questions"
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

    countdown_message = send_message(
        chat_id,
        "۳",
        context="countdown_3"
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
                    countdown_id,
                    context="delete_countdown"
                )

                return

            edit_message(
                chat_id,
                countdown_id,
                "۲",
                context="countdown_2"
            )

            time.sleep(0.7)

            if chat_id not in games:

                delete_message(
                    chat_id,
                    countdown_id,
                    context="delete_countdown"
                )

                return

            edit_message(
                chat_id,
                countdown_id,
                "۱",
                context="countdown_1"
            )

            time.sleep(0.7)

            if chat_id not in games:

                delete_message(
                    chat_id,
                    countdown_id,
                    context="delete_countdown"
                )

                return

            delete_message(
                chat_id,
                countdown_id,
                context="delete_countdown"
            )

    if chat_id not in games:
        return

    send_message(
        chat_id,
        (
            f"🎮 <b>چالش {LEVEL_NAMES[level]}</b>\n\n"
            "شروع شد!"
        ),
        stop_keyboard(),
        context="challenge_started"
    )

    time.sleep(0.5)

    if chat_id not in games:
        return

    send_question(chat_id)


# ==================================================
# پردازش Update
# ==================================================

def handle_update(update):

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

        # ------------------------------------------
        # توقف
        # ------------------------------------------

        if text == "⛔ توقف چالش":

            if chat_id in games:

                stop_game(chat_id)

            else:

                send_message(
                    chat_id,
                    (
                        "ℹ️ در حال حاضر "
                        "چالش فعالی ندارید."
                    ),
                    main_keyboard(),
                    context="stop_no_game"
                )

            return

        # ------------------------------------------
        # شروع /start
        # ------------------------------------------

        if text in [
            "/start",
            "شروع"
        ]:

            if chat_id in games:

                send_message(
                    chat_id,
                    (
                        "⚠️ <b>یک چالش در حال اجراست.</b>\n\n"
                        "برای شروع چالش جدید، "
                        "ابتدا چالش فعلی را تمام کنید "
                        "یا آن را متوقف کنید."
                    ),
                    stop_keyboard(),
                    context="start_during_game"
                )

                return

            send_message(
                chat_id,
                start_message(),
                main_keyboard(),
                context="start_message"
            )

            return

        # ------------------------------------------
        # شروع چالش
        # ------------------------------------------

        if text == "شروع چالش":

            if chat_id in games:

                send_message(
                    chat_id,
                    (
                        "⚠️ <b>یک چالش در حال اجراست.</b>\n\n"
                        "برای شروع چالش جدید، "
                        "ابتدا چالش فعلی را تمام کنید "
                        "یا آن را متوقف کنید."
                    ),
                    stop_keyboard(),
                    context="start_button_during_game"
                )

                return

            send_message(
                chat_id,
                (
                    "🎓 <b>سطح چالش را انتخاب کنید:</b>\n\n"
                    "یکی از سه سطح زیر را انتخاب کنید."
                ),
                level_keyboard(),
                context="level_selection"
            )

            return

        # ------------------------------------------
        # انتخاب سطح
        # ------------------------------------------

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
                    stop_keyboard(),
                    context="level_during_game"
                )

                return

            start_game(
                chat_id,
                level_map[text]
            )

            return

        return

    # ----------------------------------------------
    # Callback Query
    # ----------------------------------------------

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

    callback_message = callback.get(
        "message",
        {}
    )

    chat = callback_message.get(
        "chat",
        {}
    )

    chat_id = chat.get("id")

    if not chat_id:

        answer_callback_async(
            callback_id
        )

        return

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


# ==================================================
# Webhook
# ==================================================

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


# ==================================================
# اجرای برنامه
# ==================================================

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
