import os
import json
import random
import threading
import time

import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("SOROUSH_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "SOROUSH_TOKEN environment variable is not set."
    )

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
game_locks = {}
game_locks_guard = threading.Lock()


def get_game_lock(chat_id):
    with game_locks_guard:
        if chat_id not in game_locks:
            game_locks[chat_id] = threading.Lock()
        return game_locks[chat_id]


def api_request(method, data=None, context=""):
    start_time = time.monotonic()

    try:
        url = f"{API_BASE}/{method}"

        if context:
            print(f"API START: {method} | {context}")
        else:
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
            + (f" | {context}" if context else "")
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
            + (f" | {context}" if context else "")
        )

        return None


def send_message(chat_id, text, reply_markup=None, context=""):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
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
        "parse_mode": "HTML"
    }

    if reply_markup is not None:
        data["reply_markup"] = reply_markup

    return api_request(
        "editMessageText",
        data,
        context
    )


def delete_message(chat_id, message_id, context=""):
    return api_request(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id
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
                    f"{filename}: JSON باید یک لیست باشد."
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
                },
                {
                    "text": "🤖 سایر بات‌ها"
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


def answer_keyboard(options, question_token):
    rows = []

    for index, option in enumerate(options):
        rows.append(
            [
                {
                    "text": str(option),
                    "callback_data": (
                        f"answer_{question_token}_{index}"
                    )
                }
            ]
        )

    return {
        "inline_keyboard": rows
    }


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


def about_message():
    return (
        "🌿 <b>درباره ما</b>\n\n"
        "از سال ۱۳۹۵ با کانال «شعرکده» در پیام‌رسان سروش پلاس "
        "همراه شما هستیم.\n\n"
        "در «شعرکده» بخش‌های متنوعی از جمله:\n"
        "📜 شعر\n"
        "📖 برگی از کتاب\n"
        "🎬 دیالوگ ماندگار\n"
        "💬 بگو مگو\n"
        "🪶 ضرب‌المثل\n"
        "🎵 موزیک‌گردی\n"
        "🇮🇷 ایران زیبا\n"
        "را با شما به اشتراک می‌گذاریم.\n\n"
        "خوشحال می‌شویم پذیرای شما در کانال شعرکده باشیم. 🌱\n\n"
        '🔗 <a href="https://splus.ir/life_m23">لینک کانال شعرکده</a>'
    )


def manager_message():
    return (
        "💬 <b>ارتباط با مدیر</b>\n\n"
        "اگر پیشنهاد، انتقاد یا پیامی برای مدیر بات دارید، "
        "می‌توانید از طریق پیام ناشناس شعرکده با ما در ارتباط باشید.\n\n"
        '🔗 <a href="http://splus.ir/PayamNashenasBot">'
        "پیام ناشناس شعرکده"
        "</a>"
    )


def other_bots_message():
    return (
        "🤖 <b>سایر بات‌ها</b>\n\n"
        "📅 تاریخ ایجاد کانال: ۱۳۹۵\n\n"
        '🎨 <a href="http://splus.ir/PoetryCardBot">'
        "بات کارت شعر"
        "</a>\n"
        '💬 <a href="http://splus.ir/PayamNashenasBot">'
        "بات پیام ناشناس"
        "</a>\n"
        '🌿 <a href="http://splus.ir/HafezFalBot">'
        "بات فال حافظ"
        "</a>"
    )


def prepare_question(question):
    options = list(question["گزینه‌ها"])
    random.shuffle(options)

    return {
        "question": question,
        "options": options
    }


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
            question_token = game["question_token"]

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
        answer_keyboard(
            options,
            question_token
        ),
        context=f"question_{index + 1}"
    )

    if not result:
        print(
            f"QUESTION SEND FAILED: "
            f"chat={chat_id} "
            f"question={index + 1}"
        )
        return

    message = result.get(
        "result",
        {}
    )

    message_id = message.get(
        "message_id"
    )

    if not message_id:
        print(
            f"QUESTION MESSAGE ID MISSING: "
            f"chat={chat_id} "
            f"question={index + 1}"
        )
        return

    lock = get_game_lock(chat_id)

    with lock:
        game = games.get(chat_id)

        if not game:
            return

        if game["current"] != index:
            return

        if game["question_token"] != question_token:
            return

        game["message_id"] = message_id
        game["question_started"] = time.monotonic()
        game["question_deadline"] = (
            game["question_started"]
            + QUESTION_TIME
        )

        game["answered"] = False

        timer_id = object()
        game["timer_id"] = timer_id

    print(
        f"QUESTION ACTIVE: "
        f"chat={chat_id} "
        f"question={index + 1} "
        f"token={question_token}"
    )

    threading.Thread(
        target=question_timeout,
        args=(
            chat_id,
            index,
            question_token,
            timer_id
        ),
        daemon=True
    ).start()


def continue_game(chat_id, expected_current):
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


def schedule_next_question(chat_id, expected_current):
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


def question_timeout(
    chat_id,
    question_index,
    question_token,
    timer_id
):
    lock = get_game_lock(chat_id)

    with lock:
        game = games.get(chat_id)

        if not game:
            return

        if game.get("current") != question_index:
            return

        if game.get("question_token") != question_token:
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

    lock = get_game_lock(chat_id)

    with lock:
        game = games.get(chat_id)

        if not game:
            return

        if game.get("current") != question_index:
            return

        if game.get("question_token") != question_token:
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
        game["question_token"] += 1

        expected_current = game["current"]

    print(
        f"QUESTION TIMEOUT: "
        f"chat={chat_id} "
        f"question={question_index + 1} "
        f"token={question_token}"
    )

    schedule_next_question(
        chat_id,
        expected_current
    )

    if message_id:
        edit_message(
            chat_id,
            message_id,
            (
                f"⏱ <b>زمان سؤال "
                f"{question_index + 1} تمام شد.</b>\n\n"
                "امتیاز این سؤال: ۰"
            ),
            context=(
                f"timeout_question_"
                f"{question_index + 1}"
            )
        )


def process_answer(
    chat_id,
    callback_id,
    question_token,
    option_index
):
    answer_callback_async(callback_id)

    lock = get_game_lock(chat_id)

    with lock:
        game = games.get(chat_id)

        if not game:
            print(
                f"ANSWER IGNORED: "
                f"chat={chat_id} "
                f"reason=no_game"
            )
            return

        current = game["current"]

        if game.get("question_token") != question_token:
            print(
                f"ANSWER IGNORED: "
                f"chat={chat_id} "
                f"reason=stale_question "
                f"received_token={question_token} "
                f"current_token="
                f"{game.get('question_token')}"
            )
            return

        if game.get("answered"):
            print(
                f"ANSWER IGNORED: "
                f"chat={chat_id} "
                f"reason=already_answered "
                f"question={current + 1}"
            )
            return

        if current >= QUESTION_COUNT:
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

            message_id = game.get(
                "message_id"
            )

            game["current"] += 1
            game["question_token"] += 1

            expected_current = game["current"]

            timeout_case = True

            print(
                f"LATE ANSWER: "
                f"chat={chat_id} "
                f"question={current + 1} "
                f"token={question_token}"
            )

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
                return

            if (
                option_index < 0
                or option_index >= len(options)
            ):
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

            if selected_answer == correct_answer:
                game["score"] += 100

                result_text = (
                    "✅ <b>پاسخ صحیح</b>\n\n"
                    "امتیاز این سؤال: +۱۰۰\n"
                    f"امتیاز فعلی: "
                    f"{game['score']}"
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
                    f"❓ <b>سؤال:</b>\n"
                    f"{question['سؤال']}\n\n"
                    f"✅ <b>پاسخ صحیح:</b> "
                    f"{correct_answer}\n\n"
                    f"{penalty_text}\n"
                    f"امتیاز فعلی: "
                    f"{game['score']}"
                )

            game["current"] += 1
            game["question_token"] += 1

            expected_current = game["current"]

            print(
                f"ANSWER ACCEPTED: "
                f"chat={chat_id} "
                f"question={current + 1} "
                f"token={question_token} "
                f"selected={selected_answer}"
            )

    schedule_next_question(
        chat_id,
        expected_current
    )

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
                context=(
                    f"late_answer_question_"
                    f"{current + 1}"
                )
            )

        return

    if message_id:
        edit_message(
            chat_id,
            message_id,
            result_text,
            context=(
                f"answer_question_"
                f"{current + 1}"
            )
        )


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

    if score >= 700:
        message = (
            "🏆 فوق‌العاده بود ! "
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
            "یک بار دیگر امتحان کنی"
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
            "question_token": 1,
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
            f"🎮 <b>چالش "
            f"{LEVEL_NAMES[level]}</b>\n\n"
            "شروع شد!"
        ),
        stop_keyboard(),
        context="challenge_started"
    )

    time.sleep(0.5)

    if chat_id not in games:
        return

    send_question(chat_id)


def handle_update(update):
    message = update.get("message")

    if message:
        chat = message.get(
            "chat",
            {}
        )

        chat_id = chat.get(
            "id"
        )

        text = message.get(
            "text",
            ""
        )

        if not chat_id:
            return

        if text == "⛔ توقف چالش":
            if chat_id in games:
                stop_game(chat_id)

            else:
                send_message(
                    chat_id,
                    (
                        "ℹ️ در حال حاضر چالش فعالی ندارید.\n\n"
                        "🎮 برای شروع، یک چالش جدید را آغاز کنید."
                    ),
                    main_keyboard(),
                    context="stop_no_game"
                )

            return

        if text in [
            "💬 ارتباط با مدیر",
            "ارتباط با مدیر"
        ]:
            send_message(
                chat_id,
                manager_message(),
                main_keyboard(),
                context="manager"
            )
            return

        if text in [
            "🌿 درباره ما",
            "درباره ما"
        ]:
            send_message(
                chat_id,
                about_message(),
                main_keyboard(),
                context="about"
            )
            return

        if text in [
            "🤖 سایر بات‌ها",
            "سایر بات‌ها"
        ]:
            send_message(
                chat_id,
                other_bots_message(),
                main_keyboard(),
                context="other_bots"
            )
            return

        if text in ["/start", "شروع"]:
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
                    "🎓 <b>انتخاب سطح چالش :</b>\n"
                    "یکی از سه سطح زیر را انتخاب کنید."
                ),
                level_keyboard(),
                context="level_selection"
            )

            return

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

    chat_id = chat.get(
        "id"
    )

    if not chat_id:
        answer_callback_async(
            callback_id
        )
        return

    if data.startswith("answer_"):
        parts = data.split("_")

        if len(parts) != 3:
            print(
                f"INVALID CALLBACK DATA: {data}"
            )

            answer_callback_async(
                callback_id
            )
            return

        try:
            question_token = int(
                parts[1]
            )

            option_index = int(
                parts[2]
            )

        except (
            ValueError,
            TypeError
        ):
            print(
                f"INVALID CALLBACK VALUES: {data}"
            )

            answer_callback_async(
                callback_id
            )
            return

        process_answer(
            chat_id,
            callback_id,
            question_token,
            option_index
        )

        return

    answer_callback_async(
        callback_id
    )


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
