"use strict";

const QUESTION_COUNT = 7;
const QUESTION_TIME = 90;

const BASE_URL =
    "https://hasanzadeh4072-oss.github.io/Poetry-Challenge";

const DATA_URLS = {
    ashenaei: `${BASE_URL}/ashenaei.json`,
    danaei: `${BASE_URL}/danaei.json`,
    ostad: `${BASE_URL}/Ostad.json`
};

const LEVEL_NAMES = {
    ashenaei: "آشنایی",
    danaei: "دانایی",
    ostad: "استادی"
};

const state = {
    level: null,
    levelName: "",
    questions: [],
    currentQuestion: 0,
    score: 0,
    wrongAnswers: 0,
    correctAnswers: 0,
    unanswered: 0,
    timer: null,
    timeLeft: QUESTION_TIME,
    answered: false,
    gameActive: false
};

const app = document.getElementById("app");

function toPersianNumber(value) {
    return String(value).replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]);
}

function showScreen(html) {
    app.innerHTML = html;
}

function shuffle(array) {
    const result = [...array];

    for (let i = result.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [result[i], result[j]] = [result[j], result[i]];
    }

    return result;
}

async function loadQuestions(level) {
    const response = await fetch(
        `${DATA_URLS[level]}?v=${Date.now()}`,
        {
            cache: "no-store"
        }
    );

    if (!response.ok) {
        throw new Error("خطا در دریافت بانک سؤال");
    }

    const data = await response.json();

    if (!Array.isArray(data)) {
        throw new Error("ساختار بانک سؤال صحیح نیست");
    }

    const levelName = LEVEL_NAMES[level];

    return data.filter(question => {
        if (
            !question ||
            !question["سؤال"] ||
            !question["پاسخ صحیح"]
        ) {
            return false;
        }

        if (question["سطح"]) {
            return question["سطح"] === levelName;
        }

        return true;
    });
}

function getOptions(question) {
    let options = [];

    if (
        Array.isArray(question["گزینه‌ها"]) &&
        question["گزینه‌ها"].length >= 2
    ) {
        options = [...question["گزینه‌ها"]];
    } else if (question["نوع سؤال"] === "صحیح/غلط") {
        options = ["صحیح", "غلط"];
    } else {
        let others = question["سایر گزینه‌های چالشی"];

        if (typeof others === "string") {
            try {
                others = JSON.parse(others);
            } catch {
                others = others
                    .split(/[,،\n]/)
                    .map(item => item.trim())
                    .filter(Boolean);
            }
        }

        if (Array.isArray(others)) {
            options = [
                question["پاسخ صحیح"],
                ...others
            ];
        }
    }

    options = options
        .map(item => String(item).trim())
        .filter(Boolean);

    options = [...new Set(options)];

    return shuffle(options);
}

function startGame(level) {
    clearTimer();

    state.level = level;
    state.levelName = LEVEL_NAMES[level];
    state.questions = [];
    state.currentQuestion = 0;
    state.score = 0;
    state.wrongAnswers = 0;
    state.correctAnswers = 0;
    state.unanswered = 0;
    state.timeLeft = QUESTION_TIME;
    state.answered = false;
    state.gameActive = false;

    showScreen(`
        <div class="loading-screen">
            <div class="loading-spinner"></div>
            <div>در حال آماده‌سازی چالش...</div>
        </div>
    `);

    loadQuestions(level)
        .then(questions => {
            if (questions.length < QUESTION_COUNT) {
                throw new Error(
                    `برای این سطح حداقل ${QUESTION_COUNT} سؤال لازم است.`
                );
            }

            const selectedQuestions = shuffle(questions)
                .slice(0, QUESTION_COUNT)
                .map(question => ({
                    ...question,
                    _options: getOptions(question)
                }));

            for (const question of selectedQuestions) {
                if (question._options.length < 2) {
                    throw new Error(
                        "برخی از سؤال‌ها گزینه‌های کافی ندارند."
                    );
                }
            }

            state.questions = selectedQuestions;
            state.gameActive = true;

            showQuestion();
        })
        .catch(error => {
            showScreen(`
                <div class="error-screen">
                    <div class="error-icon">⚠️</div>
                    <div class="error-title">خطا</div>
                    <div class="error-message">
                        ${error.message}
                    </div>
                    <button class="primary-btn" id="back-home">
                        بازگشت
                    </button>
                </div>
            `);

            document
                .getElementById("back-home")
                ?.addEventListener("click", showHomeScreen);
        });
}

function showQuestion() {
    clearTimer();

    const question =
        state.questions[state.currentQuestion];

    if (!question) {
        finishGame();
        return;
    }

    state.answered = false;
    state.timeLeft = QUESTION_TIME;

    const options = shuffle(question._options);

    showScreen(`
        <div class="game-screen">

            <div class="game-header">
                <div class="level-badge">
                    ${state.levelName}
                </div>

                <div class="question-counter">
                    سؤال ${toPersianNumber(state.currentQuestion + 1)}
                    از
                    ${toPersianNumber(QUESTION_COUNT)}
                </div>
            </div>

            <div class="score-row">
                <div>
                    امتیاز:
                    <strong id="score-value">
                        ${toPersianNumber(state.score)}
                    </strong>
                </div>

                <div class="timer" id="timer">
                    ${toPersianNumber(state.timeLeft)}
                </div>
            </div>

            <div class="question-card">
                <div class="question-text">
                    ${question["سؤال"]}
                </div>
            </div>

            <div class="options-container">
                ${options.map((option, index) => `
                    <button
                        class="option-btn"
                        data-option="${encodeURIComponent(option)}"
                    >
                        <span class="option-letter">
                            ${"الفبپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی"[index] || ""}
                        </span>

                        <span class="option-text">
                            ${option}
                        </span>
                    </button>
                `).join("")}
            </div>

            <button class="stop-btn" id="stop-game">
                ⛔ توقف چالش
            </button>

        </div>
    `);

    document
        .querySelectorAll(".option-btn")
        .forEach(button => {
            button.addEventListener("click", () => {
                const option = decodeURIComponent(
                    button.dataset.option
                );

                answerQuestion(option, button);
            });
        });

    document
        .getElementById("stop-game")
        ?.addEventListener("click", stopGame);

    startTimer();
}

function startTimer() {
    clearTimer();

    state.timeLeft = QUESTION_TIME;

    updateTimer();

    state.timer = setInterval(() => {
        if (!state.gameActive || state.answered) {
            return;
        }

        state.timeLeft--;

        updateTimer();

        if (state.timeLeft <= 0) {
            timeExpired();
        }
    }, 1000);
}

function updateTimer() {
    const timer =
        document.getElementById("timer");

    if (!timer) {
        return;
    }

    timer.textContent = toPersianNumber(
        Math.max(0, state.timeLeft)
    );

    timer.classList.toggle(
        "danger",
        state.timeLeft <= 10
    );
}

function normalizeText(text) {
    return String(text ?? "")
        .trim()
        .replace(/ي/g, "ی")
        .replace(/ى/g, "ی")
        .replace(/ك/g, "ک")
        .replace(/ۀ/g, "ه")
        .replace(/ة/g, "ه")
        .replace(/\u200c/g, " ")
        .replace(/\s+/g, " ");
}

function getCorrectAnswer(question) {
    return normalizeText(
        question["پاسخ صحیح"]
    );
}

function isCorrect(option, question) {
    return (
        normalizeText(option) ===
        getCorrectAnswer(question)
    );
}

function answerQuestion(option, clickedButton) {
    if (!state.gameActive || state.answered) {
        return;
    }

    state.answered = true;
    clearTimer();

    const question =
        state.questions[state.currentQuestion];

    document
        .querySelectorAll(".option-btn")
        .forEach(button => {
            button.disabled = true;
        });

    if (isCorrect(option, question)) {
        state.correctAnswers++;
        state.score += 100;

        clickedButton.classList.add("correct");
    } else {
        state.wrongAnswers++;

        if (state.wrongAnswers % 2 === 0) {
            state.score -= 15;
        }

        clickedButton.classList.add("wrong");

        document
            .querySelectorAll(".option-btn")
            .forEach(button => {
                const value = decodeURIComponent(
                    button.dataset.option
                );

                if (isCorrect(value, question)) {
                    button.classList.add("correct");
                }
            });
    }

    const scoreValue =
        document.getElementById("score-value");

    if (scoreValue) {
        scoreValue.textContent =
            toPersianNumber(state.score);
    }

    setTimeout(() => {
        nextQuestion();
    }, 700);
}

function timeExpired() {
    if (!state.gameActive || state.answered) {
        return;
    }

    state.answered = true;
    state.unanswered++;

    clearTimer();

    document
        .querySelectorAll(".option-btn")
        .forEach(button => {
            button.disabled = true;
        });

    setTimeout(() => {
        nextQuestion();
    }, 500);
}

function nextQuestion() {
    if (!state.gameActive) {
        return;
    }

    state.currentQuestion++;

    if (
        state.currentQuestion >=
        QUESTION_COUNT
    ) {
        finishGame();
        return;
    }

    showQuestion();
}

function clearTimer() {
    if (state.timer) {
        clearInterval(state.timer);
        state.timer = null;
    }
}

/* =========================================================
   READY-MADE EXTERNAL ANIMATION
   ========================================================= */

const PERFECT_ANIMATION_URL =
    "https://assets-v2.lottiefiles.com/a/9c0c9d5c-7c2d-11ee-8c99-4f1c0c7d2d0f/animation.json";

function loadLottieScript() {
    return new Promise(resolve => {
        if (
            window.lottie &&
            typeof window.lottie.loadAnimation === "function"
        ) {
            resolve(true);
            return;
        }

        const oldScript =
            document.querySelector(
                'script[data-lottie="true"]'
            );

        if (oldScript) {
            oldScript.addEventListener(
                "load",
                () => resolve(
                    !!window.lottie
                ),
                { once: true }
            );

            oldScript.addEventListener(
                "error",
                () => resolve(false),
                { once: true }
            );

            return;
        }

        const script =
            document.createElement("script");

        script.src =
            "https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js";

        script.dataset.lottie = "true";

        script.onload = () => {
            resolve(
                !!window.lottie
            );
        };

        script.onerror = () => {
            resolve(false);
        };

        document.head.appendChild(script);
    });
}

async function showPerfectScoreAnimation() {
    clearTimer();

    const overlay =
        document.createElement("div");

    overlay.id = "perfect-score-overlay";

    overlay.innerHTML = `
        <div
            id="perfect-animation"
            class="perfect-animation"
        ></div>
    `;

    document.body.appendChild(overlay);

    const loaded =
        await loadLottieScript();

    if (!loaded) {
        overlay.remove();
        showResultScreen();
        return;
    }

    try {
        window.lottie.loadAnimation({
            container:
                document.getElementById(
                    "perfect-animation"
                ),

            renderer: "svg",

            loop: false,

            autoplay: true,

            path: PERFECT_ANIMATION_URL,

            rendererSettings: {
                preserveAspectRatio:
                    "xMidYMid meet"
            }
        });
    } catch (error) {
        console.error(
            "Lottie animation error:",
            error
        );

        overlay.remove();
        showResultScreen();
        return;
    }

    setTimeout(() => {
        overlay.classList.add("hide");

        setTimeout(() => {
            overlay.remove();
            showResultScreen();
        }, 400);
    }, 5000);
}

function showResultScreen() {
    let resultMessage = "";

    if (state.score >= 600) {
        resultMessage = "فوق‌العاده! 🌟";
    } else if (state.score >= 400) {
        resultMessage = "عالی! 👏";
    } else if (state.score >= 200) {
        resultMessage = "خوب بود! 🌿";
    } else {
        resultMessage =
            "این پایان راه نیست؛ دوباره تلاش کن. 💚";
    }

    showScreen(`
        <div class="result-screen">

            <div class="result-icon">
                🏆
            </div>

            <div class="result-title">
                پایان چالش
            </div>

            <div class="result-level">
                سطح ${state.levelName}
            </div>

            <div class="result-score">
                ${toPersianNumber(state.score)}
            </div>

            <div class="result-message">
                ${resultMessage}
            </div>

            <div class="result-stats">

                <div class="result-stat">
                    <span>پاسخ صحیح</span>
                    <strong>
                        ${toPersianNumber(
                            state.correctAnswers
                        )}
                    </strong>
                </div>

                <div class="result-stat">
                    <span>پاسخ غلط</span>
                    <strong>
                        ${toPersianNumber(
                            state.wrongAnswers
                        )}
                    </strong>
                </div>

                <div class="result-stat">
                    <span>بدون پاسخ</span>
                    <strong>
                        ${toPersianNumber(
                            state.unanswered
                        )}
                    </strong>
                </div>

            </div>

            <button
                class="primary-btn"
                id="play-again"
            >
                🔄 دوباره بازی کن
            </button>

            <button
                class="secondary-btn"
                id="result-home"
            >
                🏠 بازگشت
            </button>

        </div>
    `);

    document
        .getElementById("play-again")
        ?.addEventListener(
            "click",
            () => startGame(state.level)
        );

    document
        .getElementById("result-home")
        ?.addEventListener(
            "click",
            showHomeScreen
        );
}

function finishGame() {
    clearTimer();

    state.gameActive = false;

    if (state.score === 700) {
        showPerfectScoreAnimation();
        return;
    }

    showResultScreen();
}

function stopGame() {
    clearTimer();

    state.gameActive = false;
    state.answered = true;

    showHomeScreen();
}

function showHomeScreen() {
    clearTimer();

    state.gameActive = false;

    showScreen(`
        <div class="home-screen">

            <div class="home-logo">
                📚
            </div>

            <div class="home-title">
                چالش شعرانه
            </div>

            <div class="home-description">
                دانسته‌های ادبی و شعری خودت را در
                سه سطح بیازما!
            </div>

            <button
                class="primary-btn"
                id="start-challenge"
            >
                شروع چالش
            </button>

            <div class="home-menu">

                <button class="menu-btn">
                    💬 ارتباط با مدیر
                </button>

                <button class="menu-btn">
                    🌿 درباره ما
                </button>

                <button class="menu-btn">
                    🤖 سایر بات‌ها
                </button>

            </div>

        </div>
    `);

    document
        .getElementById("start-challenge")
        ?.addEventListener(
            "click",
            showLevelScreen
        );
}

function showLevelScreen() {
    showScreen(`
        <div class="level-screen">

            <div class="level-title">
                انتخاب سطح
            </div>

            <div class="level-description">
                سطح موردنظر خود را انتخاب کنید
            </div>

            <div class="levels">

                <button
                    class="level-btn"
                    data-level="ashenaei"
                >
                    <span>🌱</span>
                    <strong>آشنایی</strong>
                    <small>سطح مقدماتی</small>
                </button>

                <button
                    class="level-btn"
                    data-level="danaei"
                >
                    <span>📖</span>
                    <strong>دانایی</strong>
                    <small>سطح متوسط</small>
                </button>

                <button
                    class="level-btn"
                    data-level="ostad"
                >
                    <span>🎓</span>
                    <strong>استادی</strong>
                    <small>سطح پیشرفته</small>
                </button>

            </div>

            <button
                class="secondary-btn"
                id="level-back"
            >
                بازگشت
            </button>

        </div>
    `);

    document
        .querySelectorAll(".level-btn")
        .forEach(button => {
            button.addEventListener(
                "click",
                () => {
                    startGame(
                        button.dataset.level
                    );
                }
            );
        });

    document
        .getElementById("level-back")
        ?.addEventListener(
            "click",
            showHomeScreen
        );
}

function injectStyles() {
    const style =
        document.createElement("style");

    style.textContent = `
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 0;
            font-family:
                Vazirmatn,
                Tahoma,
                Arial,
                sans-serif;
            direction: rtl;
            background: #f7f7f7;
            color: #222;
        }

        button {
            font-family: inherit;
        }

        .home-screen,
        .level-screen,
        .game-screen,
        .result-screen,
        .error-screen,
        .loading-screen {
            min-height: 100vh;
            padding: 24px 18px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .home-logo {
            font-size: 64px;
            margin-bottom: 12px;
        }

        .home-title {
            font-size: 30px;
            font-weight: 900;
            margin-bottom: 12px;
        }

        .home-description {
            max-width: 420px;
            text-align: center;
            line-height: 2;
            color: #666;
            margin-bottom: 28px;
        }

        .primary-btn,
        .secondary-btn,
        .menu-btn,
        .stop-btn,
        .level-btn {
            border: 0;
            cursor: pointer;
            transition: .2s ease;
        }

        .primary-btn {
            width: min(100%, 360px);
            padding: 15px 22px;
            border-radius: 16px;
            background: #222;
            color: #fff;
            font-size: 17px;
            font-weight: 800;
        }

        .secondary-btn {
            width: min(100%, 360px);
            margin-top: 12px;
            padding: 13px 20px;
            border-radius: 15px;
            background: #e9e9e9;
            color: #333;
            font-size: 16px;
        }

        .home-menu {
            width: min(100%, 360px);
            margin-top: 25px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .menu-btn {
            padding: 13px;
            border-radius: 14px;
            background: #fff;
            color: #555;
            font-size: 14px;
        }

        .level-title {
            font-size: 28px;
            font-weight: 900;
            margin-bottom: 8px;
        }

        .level-description {
            color: #777;
            margin-bottom: 25px;
        }

        .levels {
            width: min(100%, 420px);
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .level-btn {
            width: 100%;
            padding: 18px;
            border-radius: 18px;
            background: #fff;
            display: grid;
            grid-template-columns: 45px 1fr;
            grid-template-rows: auto auto;
            text-align: right;
            box-shadow:
                0 3px 14px rgba(0,0,0,.06);
        }

        .level-btn span {
            grid-row: 1 / 3;
            font-size: 30px;
            align-self: center;
        }

        .level-btn strong {
            font-size: 18px;
        }

        .level-btn small {
            margin-top: 5px;
            color: #888;
        }

        .game-screen {
            justify-content: flex-start;
            padding-top: 20px;
        }

        .game-header,
        .score-row {
            width: min(100%, 600px);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .game-header {
            margin-bottom: 15px;
        }

        .level-badge {
            background: #222;
            color: #fff;
            padding: 7px 13px;
            border-radius: 12px;
            font-size: 13px;
            font-weight: 700;
        }

        .question-counter {
            color: #777;
            font-size: 14px;
        }

        .score-row {
            margin-bottom: 18px;
            color: #555;
        }

        .score-row strong {
            color: #111;
        }

        .timer {
            min-width: 48px;
            text-align: center;
            padding: 7px 10px;
            border-radius: 10px;
            background: #fff;
            font-weight: 900;
        }

        .timer.danger {
            background: #ffe7e7;
            color: #c00;
        }

        .question-card {
            width: min(100%, 600px);
            padding: 24px 20px;
            border-radius: 20px;
            background: #fff;
            box-shadow:
                0 4px 18px rgba(0,0,0,.06);
            margin-bottom: 18px;
        }

        .question-text {
            font-size: 19px;
            line-height: 2;
            font-weight: 800;
            text-align: center;
        }

        .options-container {
            width: min(100%, 600px);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .option-btn {
            width: 100%;
            border: 2px solid #e7e7e7;
            background: #fff;
            border-radius: 16px;
            padding: 14px;
            display: flex;
            align-items: center;
            gap: 12px;
            text-align: right;
            cursor: pointer;
            font-size: 15px;
            line-height: 1.8;
        }

        .option-btn:disabled {
            cursor: default;
        }

        .option-letter {
            width: 32px;
            height: 32px;
            flex: 0 0 32px;
            border-radius: 50%;
            background: #f0f0f0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
        }

        .option-btn.correct {
            border-color: #39a95c;
            background: #eaf8ee;
        }

        .option-btn.wrong {
            border-color: #dc4c4c;
            background: #fff0f0;
        }

        .stop-btn {
            margin-top: 18px;
            padding: 10px 18px;
            border-radius: 12px;
            background: transparent;
            color: #888;
            font-size: 13px;
        }

        .result-icon {
            font-size: 64px;
            margin-bottom: 10px;
        }

        .result-title {
            font-size: 28px;
            font-weight: 900;
        }

        .result-level {
            color: #777;
            margin-top: 8px;
        }

        .result-score {
            font-size: 58px;
            font-weight: 1000;
            margin: 18px 0 5px;
        }

        .result-message {
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 25px;
        }

        .result-stats {
            width: min(100%, 420px);
            display: grid;
            grid-template-columns:
                repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 25px;
        }

        .result-stat {
            background: #fff;
            border-radius: 14px;
            padding: 12px 5px;
            text-align: center;
        }

        .result-stat span {
            display: block;
            font-size: 11px;
            color: #888;
            margin-bottom: 5px;
        }

        .result-stat strong {
            font-size: 18px;
        }

        .error-icon {
            font-size: 50px;
        }

        .error-title {
            font-size: 25px;
            font-weight: 900;
            margin: 12px 0;
        }

        .error-message {
            text-align: center;
            color: #777;
            margin-bottom: 20px;
        }

        .loading-spinner {
            width: 42px;
            height: 42px;
            border: 4px solid #ddd;
            border-top-color: #222;
            border-radius: 50%;
            animation: spin .8s linear infinite;
            margin-bottom: 15px;
        }

        @keyframes spin {
            to {
                transform: rotate(360deg);
            }
        }

        /* فقط لایه نمایش انیمیشن آماده خارجی */
        #perfect-score-overlay {
            position: fixed;
            inset: 0;
            z-index: 999999;
            background: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 1;
            transition: opacity .4s ease;
        }

        #perfect-score-overlay.hide {
            opacity: 0;
        }

        .perfect-animation {
            width: min(90vw, 500px);
            height: min(90vw, 500px);
        }

        @media (max-width: 420px) {
            .question-text {
                font-size: 17px;
            }

            .result-score {
                font-size: 50px;
            }
        }
    `;

    document.head.appendChild(style);
}

function initializeSoroushWebApp() {
    injectStyles();
    showHomeScreen();

    try {
        if (
            window.SoroushWebApp &&
            typeof window.SoroushWebApp.ready ===
                "function"
        ) {
            window.SoroushWebApp.ready();
        }
    } catch (error) {
        console.warn(
            "Soroush WebApp initialization warning:",
            error
        );
    }
}

if (
    document.readyState === "loading"
) {
    document.addEventListener(
        "DOMContentLoaded",
        initializeSoroushWebApp
    );
} else {
    initializeSoroushWebApp();
}
```0
