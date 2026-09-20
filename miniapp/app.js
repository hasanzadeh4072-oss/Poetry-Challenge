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

const homeScreen = document.getElementById("homeScreen");
const gameScreen = document.getElementById("gameScreen");
const resultScreen = document.getElementById("resultScreen");

const levelName = document.getElementById("levelName");
const scoreElement = document.getElementById("score");
const questionNumber = document.getElementById("questionNumber");
const questionText = document.getElementById("questionText");
const optionsContainer = document.getElementById("options");
const timerElement = document.getElementById("timer");

const resultLevel = document.getElementById("resultLevel");
const finalScore = document.getElementById("finalScore");
const resultMessage = document.getElementById("resultMessage");

const stopButton = document.getElementById("stopButton");
const restartButton = document.getElementById("restartButton");

let confettiReady = false;
let perfectStyleAdded = false;


/* =========================================================
تبدیل اعداد به فارسی
========================================================= */

function toPersianNumber(value) {
    return String(value).replace(
        /\d/g,
        digit => "۰۱۲۳۴۵۶۷۸۹"[digit]
    );
}


/* =========================================================
نمایش صفحه
========================================================= */

function showScreen(screen) {
    [homeScreen, gameScreen, resultScreen].forEach(item => {
        item.classList.remove("active");
    });

    screen.classList.add("active");
}


/* =========================================================
درهم‌ریختن آرایه
========================================================= */

function shuffle(array) {
    const result = [...array];

    for (let i = result.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));

        [result[i], result[j]] =
            [result[j], result[i]];
    }

    return result;
}


/* =========================================================
دریافت کتابخانه کنفتی
========================================================= */

function loadConfettiLibrary() {

    if (window.confetti) {
        confettiReady = true;
        return Promise.resolve();
    }

    if (
        document.getElementById(
            "hcg-confetti-library"
        )
    ) {
        return new Promise(resolve => {

            const check =
                setInterval(() => {

                    if (window.confetti) {
                        clearInterval(check);
                        confettiReady = true;
                        resolve();
                    }

                }, 50);

            setTimeout(() => {
                clearInterval(check);
                resolve();
            }, 5000);

        });
    }

    return new Promise(resolve => {

        const script =
            document.createElement("script");

        script.id =
            "hcg-confetti-library";

        script.src =
            "https://cdn.jsdelivr.net/npm/hcg-confetti-cannons@1/hcg-confetti-cannons.min.js";

        script.onload = () => {
            confettiReady = true;
            resolve();
        };

        script.onerror = () => {
            console.warn(
                "Confetti library could not be loaded."
            );

            resolve();
        };

        document.head.appendChild(script);
    });
}


/* =========================================================
دریافت سؤال‌ها
========================================================= */

async function loadQuestions(level) {

    const url = DATA_URLS[level];

    if (!url) {
        throw new Error("سطح نامعتبر است");
    }

    const response =
        await fetch(
            `${url}?v=${Date.now()}`,
            {
                cache: "no-store"
            }
        );

    if (!response.ok) {
        throw new Error(
            `خطا در دریافت سؤال‌ها: ${response.status}`
        );
    }

    const data =
        await response.json();

    if (!Array.isArray(data)) {
        throw new Error(
            "ساختار فایل سؤال‌ها نامعتبر است"
        );
    }

    const selectedLevel =
        LEVEL_NAMES[level];

    return data.filter(question => {

        if (
            !question ||
            !question["سؤال"] ||
            !question["پاسخ صحیح"]
        ) {
            return false;
        }

        if (question["سطح"]) {
            return (
                question["سطح"] ===
                selectedLevel
            );
        }

        return true;
    });
}


/* =========================================================
ساخت گزینه‌ها
========================================================= */

function getOptions(question) {

    let options =
        question["گزینه‌ها"];

    if (Array.isArray(options)) {

        options =
            options.filter(option => {

                return (
                    option !== null &&
                    option !== undefined &&
                    String(option).trim() !== ""
                );
            });

        if (options.length >= 2) {
            return options;
        }
    }

    const correct =
        question["پاسخ صحیح"];

    if (
        question["نوع سؤال"] ===
        "صحیح/غلط"
    ) {
        return [
            "صحیح",
            "غلط"
        ];
    }

    let others =
        question["سایر گزینه‌های چالشی"];

    if (typeof others === "string") {

        others =
            others
                .split(/[،,]/)
                .map(option =>
                    option.trim()
                )
                .filter(option => {

                    return (
                        option !== "" &&
                        option !== "—" &&
                        option !== "-"
                    );
                });

    } else if (Array.isArray(others)) {

        others =
            others
                .map(option =>
                    String(option).trim()
                )
                .filter(option => {

                    return (
                        option !== "" &&
                        option !== "—" &&
                        option !== "-"
                    );
                });

    } else {

        others = [];
    }

    const allOptions = [
        correct,
        ...others
    ];

    const uniqueOptions = [
        ...new Set(
            allOptions.map(option =>
                String(option).trim()
            )
        )
    ];

    return shuffle(uniqueOptions);
}


/* =========================================================
شروع بازی
========================================================= */

async function startGame(level) {

    clearTimer();

    state.level = level;

    state.levelName =
        LEVEL_NAMES[level] || level;

    state.currentQuestion = 0;
    state.score = 0;
    state.wrongAnswers = 0;
    state.correctAnswers = 0;
    state.unanswered = 0;
    state.questions = [];
    state.gameActive = false;

    levelName.textContent =
        state.levelName;

    scoreElement.textContent =
        toPersianNumber(0);

    showScreen(gameScreen);

    questionText.textContent =
        "در حال آماده‌سازی چالش...";

    optionsContainer.innerHTML = "";

    try {

        const allQuestions =
            await loadQuestions(level);

        if (
            allQuestions.length <
            QUESTION_COUNT
        ) {
            throw new Error(
                `تعداد سؤال‌های سطح ${LEVEL_NAMES[level]} کافی نیست`
            );
        }

        state.questions =
            shuffle(allQuestions)
                .slice(
                    0,
                    QUESTION_COUNT
                )
                .map(question => ({
                    question,
                    options:
                        getOptions(question)
                }));

        for (
            const item
            of state.questions
        ) {

            if (
                item.options.length < 2
            ) {
                throw new Error(
                    "یکی از سؤال‌ها گزینه کافی ندارد"
                );
            }
        }

        state.gameActive = true;

        showQuestion();

    } catch (error) {

        console.error(
            "START GAME ERROR:",
            error
        );

        state.gameActive = false;

        questionText.textContent =
            "دریافت سؤال‌ها با مشکل مواجه شد.";

        optionsContainer.innerHTML = "";

        const retryButton =
            document.createElement(
                "button"
            );

        retryButton.className =
            "primary-btn";

        retryButton.textContent =
            "🔄 تلاش دوباره";

        retryButton.addEventListener(
            "click",
            () => startGame(level)
        );

        optionsContainer.appendChild(
            retryButton
        );
    }
}


/* =========================================================
نمایش سؤال
========================================================= */

function showQuestion() {

    clearTimer();

    if (!state.gameActive) {
        return;
    }

    if (
        state.currentQuestion >=
        state.questions.length
    ) {
        finishGame();
        return;
    }

    const item =
        state.questions[
            state.currentQuestion
        ];

    const question =
        item.question;

    state.answered = false;

    state.timeLeft =
        QUESTION_TIME;

    questionNumber.textContent =
        toPersianNumber(
            state.currentQuestion + 1
        );

    questionText.textContent =
        question["سؤال"];

    optionsContainer.innerHTML = "";

    const options =
        shuffle(item.options);

    options.forEach(option => {

        const button =
            document.createElement(
                "button"
            );

        button.className =
            "option-btn";

        button.type = "button";

        button.textContent =
            String(option);

        button.addEventListener(
            "click",
            () => {

                answerQuestion(
                    option,
                    button
                );
            }
        );

        optionsContainer.appendChild(
            button
        );
    });

    updateTimer();

    state.timer =
        setInterval(() => {

            if (!state.gameActive) {

                clearTimer();

                return;
            }

            state.timeLeft--;

            updateTimer();

            if (
                state.timeLeft <= 0
            ) {

                clearTimer();

                timeExpired();
            }

        }, 1000);
}


/* =========================================================
تایمر
========================================================= */

function updateTimer() {

    const minutes =
        Math.floor(
            state.timeLeft / 60
        );

    const seconds =
        state.timeLeft % 60;

    timerElement.textContent =
        `${toPersianNumber(minutes)}:${toPersianNumber(
            String(seconds).padStart(2, "0")
        )}`;

    timerElement.classList.remove(
        "warning",
        "danger"
    );

    if (
        state.timeLeft <= 10
    ) {

        timerElement.classList.add(
            "danger"
        );

    } else if (
        state.timeLeft <= 30
    ) {

        timerElement.classList.add(
            "warning"
        );
    }
}


/* =========================================================
نرمال‌سازی متن
========================================================= */

function normalizeText(value) {

    return String(value ?? "")
        .trim()
        .replace(/ي/g, "ی")
        .replace(/ك/g, "ک");
}


/* =========================================================
پاسخ صحیح
========================================================= */

function getCorrectAnswer(question) {

    return (
        question["پاسخ صحیح"] ||
        ""
    );
}


/* =========================================================
بررسی پاسخ
========================================================= */

function isCorrect(
    selectedAnswer,
    question
) {

    return (
        normalizeText(
            selectedAnswer
        ) ===
        normalizeText(
            getCorrectAnswer(question)
        )
    );
}


/* =========================================================
پاسخ به سؤال
========================================================= */

function answerQuestion(
    selectedAnswer,
    selectedButton
) {

    if (
        !state.gameActive ||
        state.answered
    ) {
        return;
    }

    state.answered = true;

    clearTimer();

    const item =
        state.questions[
            state.currentQuestion
        ];

    const question =
        item.question;

    const correct =
        isCorrect(
            selectedAnswer,
            question
        );

    const buttons =
        optionsContainer.querySelectorAll(
            ".option-btn"
        );

    buttons.forEach(button => {
        button.disabled = true;
    });

    if (correct) {

        state.score += 100;

        state.correctAnswers++;

        selectedButton.classList.add(
            "correct"
        );

    } else {

        state.wrongAnswers++;

        selectedButton.classList.add(
            "wrong"
        );

        if (
            state.wrongAnswers % 2 === 0
        ) {
            state.score -= 15;
        }

        const correctAnswer =
            getCorrectAnswer(question);

        buttons.forEach(button => {

            if (
                normalizeText(
                    button.textContent
                ) ===
                normalizeText(
                    correctAnswer
                )
            ) {

                button.classList.add(
                    "correct"
                );
            }
        });
    }

    scoreElement.textContent =
        toPersianNumber(
            state.score
        );

    setTimeout(() => {
        nextQuestion();
    }, 700);
}


/* =========================================================
پایان زمان سؤال
========================================================= */

function timeExpired() {

    if (
        !state.gameActive ||
        state.answered
    ) {
        return;
    }

    state.answered = true;

    state.unanswered++;

    const buttons =
        optionsContainer.querySelectorAll(
            ".option-btn"
        );

    buttons.forEach(button => {
        button.disabled = true;
    });

    setTimeout(() => {
        nextQuestion();
    }, 500);
}


/* =========================================================
سؤال بعدی
========================================================= */

function nextQuestion() {

    if (!state.gameActive) {
        return;
    }

    state.currentQuestion++;

    if (
        state.currentQuestion >=
        state.questions.length
    ) {

        finishGame();

    } else {

        showQuestion();
    }
}


/* =========================================================
پاک کردن تایمر
========================================================= */

function clearTimer() {

    if (state.timer !== null) {

        clearInterval(
            state.timer
        );

        state.timer = null;
    }
}


/* =========================================================
استایل انیمیشن امتیاز کامل
========================================================= */

function addPerfectAnimationStyles() {

    if (perfectStyleAdded) {
        return;
    }

    const style =
        document.createElement(
            "style"
        );

    style.id =
        "perfect-score-style";

    style.textContent = `

        .perfect-screen {
            position: fixed !important;
            inset: 0 !important;

            width: 100vw !important;
            height: 100vh !important;

            z-index: 2147483647 !important;

            display: flex !important;
            align-items: center !important;
            justify-content: center !important;

            overflow: hidden !important;

            background:
                linear-gradient(
                    180deg,
                    #111827 0%,
                    #0b1020 100%
                ) !important;

            box-sizing: border-box !important;
        }

        .perfect-box {
            position: relative !important;

            z-index: 20 !important;

            width: 100% !important;

            display: flex !important;
            flex-direction: column !important;

            align-items: center !important;
            justify-content: center !important;

            text-align: center !important;
        }

        .perfect-trophy {
            font-size: 100px !important;

            line-height: 1 !important;

            margin-bottom: 20px !important;

            opacity: 0 !important;

            transform:
                scale(.2)
                translateY(40px) !important;

            filter:
                drop-shadow(
                    0 0 12px
                    rgba(255,193,7,.9)
                )
                drop-shadow(
                    0 0 35px
                    rgba(255,193,7,.6)
                ) !important;

            animation:
                trophyAppear
                .9s
                cubic-bezier(.17,.89,.32,1.28)
                forwards !important;
        }

        .perfect-number {
            font-size: 86px !important;

            font-weight: 900 !important;

            line-height: 1 !important;

            color: #ffd54f !important;

            text-shadow:
                0 0 12px
                rgba(255,193,7,.9),
                0 0 30px
                rgba(255,193,7,.6) !important;

            opacity: 0 !important;

            animation:
                numberAppear
                .8s
                ease
                .5s
                forwards !important;
        }

        .perfect-title {
            margin-top: 22px !important;

            font-size: 27px !important;

            font-weight: 900 !important;

            color: #ffffff !important;

            opacity: 0 !important;

            animation:
                textAppear
                .7s
                ease
                1.1s
                forwards !important;
        }

        .perfect-subtitle {
            margin-top: 10px !important;

            padding: 0 20px !important;

            font-size: 16px !important;

            color:
                rgba(255,255,255,.75) !important;

            opacity: 0 !important;

            animation:
                textAppear
                .7s
                ease
                1.4s
                forwards !important;
        }

        @keyframes trophyAppear {

            0% {
                opacity: 0;
                transform:
                    scale(.2)
                    translateY(60px);
            }

            70% {
                opacity: 1;
                transform:
                    scale(1.12)
                    translateY(-5px);
            }

            100% {
                opacity: 1;
                transform:
                    scale(1)
                    translateY(0);
            }
        }

        @keyframes numberAppear {

            0% {
                opacity: 0;
                transform: scale(.2);
            }

            70% {
                opacity: 1;
                transform: scale(1.12);
            }

            100% {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes textAppear {

            from {
                opacity: 0;
                transform:
                    translateY(18px);
            }

            to {
                opacity: 1;
                transform:
                    translateY(0);
            }
        }

    `;

    document.head.appendChild(
        style
    );

    perfectStyleAdded = true;
}


/* =========================================================
اجرای انیمیشن امتیاز کامل
========================================================= */

async function showPerfectScoreAnimation() {

    addPerfectAnimationStyles();

    const old =
        document.querySelector(
            ".perfect-screen"
        );

    if (old) {
        old.remove();
    }


    /* -----------------------------------------
       ساخت صفحه جشن
    ----------------------------------------- */

    const overlay =
        document.createElement(
            "div"
        );

    overlay.className =
        "perfect-screen";


    const box =
        document.createElement(
            "div"
        );

    box.className =
        "perfect-box";


    const trophy =
        document.createElement(
            "div"
        );

    trophy.className =
        "perfect-trophy";

    trophy.textContent =
        "🏆";


    const number =
        document.createElement(
            "div"
        );

    number.className =
        "perfect-number";

    number.textContent =
        "۰";


    const title =
        document.createElement(
            "div"
        );

    title.className =
        "perfect-title";

    title.textContent =
        "✨ امتیاز کامل! ✨";


    const subtitle =
        document.createElement(
            "div"
        );

    subtitle.className =
        "perfect-subtitle";

    subtitle.textContent =
        "هر ۷ سؤال را درست پاسخ دادید";


    box.appendChild(
        trophy
    );

    box.appendChild(
        number
    );

    box.appendChild(
        title
    );

    box.appendChild(
        subtitle
    );

    overlay.appendChild(
        box
    );

    document.body.appendChild(
        overlay
    );


    /* -----------------------------------------
       بارگذاری کتابخانه
    ----------------------------------------- */

    await loadConfettiLibrary();


    /* -----------------------------------------
       کنفتی آماده
    ----------------------------------------- */

    if (
        confettiReady &&
        typeof window.confetti ===
        "function"
    ) {

        setTimeout(() => {

            try {

                window.confetti.celebrate({
                    particleCount: 180
                });

            } catch (error) {

                console.warn(
                    "Confetti error:",
                    error
                );

                try {
                    window.confetti({
                        particleCount: 180,
                        spread: 100,
                        origin: {
                            x: 0.5,
                            y: 0.65
                        }
                    });
                } catch (_) {}
            }

        }, 250);


        setTimeout(() => {

            try {

                window.confetti.fireworks({
                    duration: 1800,
                    interval: 300
                });

            } catch (_) {}

        }, 900);

    }


    /* -----------------------------------------
       شمارش ۰ تا ۷۰۰
    ----------------------------------------- */

    const duration =
        1500;

    const start =
        performance.now();

    function animateScore(now) {

        if (
            !overlay.parentNode
        ) {
            return;
        }

        const progress =
            Math.min(
                (now - start) /
                duration,
                1
            );

        const eased =
            1 -
            Math.pow(
                1 - progress,
                3
            );

        const value =
            Math.floor(
                700 * eased
            );

        number.textContent =
            toPersianNumber(
                value
            );

        if (
            progress < 1
        ) {

            requestAnimationFrame(
                animateScore
            );

        } else {

            number.textContent =
                "۷۰۰";
        }
    }

    requestAnimationFrame(
        animateScore
    );


    /* -----------------------------------------
       پایان
    ----------------------------------------- */

    setTimeout(() => {

        if (
            overlay &&
            overlay.parentNode
        ) {
            overlay.remove();
        }

        if (window.confetti) {

            try {
                window.confetti.reset();
            } catch (_) {}
        }

        showResultScreen();

    }, 5000);
}


/* =========================================================
نمایش نتیجه نهایی
========================================================= */

function showResultScreen() {

    resultLevel.textContent =
        state.levelName;

    finalScore.textContent =
        toPersianNumber(
            state.score
        );

    let message;

    if (
        state.score >= 600
    ) {

        message =
            "فوق‌العاده! 🌟";

    } else if (
        state.score >= 400
    ) {

        message =
            "عالی! 👏";

    } else if (
        state.score >= 200
    ) {

        message =
            "خوب بود! 🌿";

    } else {

        message =
            "این پایان راه نیست؛ دوباره تلاش کن. 💚";
    }

    resultMessage.textContent =
        message;

    showScreen(
        resultScreen
    );
}


/* =========================================================
پایان بازی
========================================================= */

function finishGame() {

    clearTimer();

    state.gameActive = false;

    if (
        state.score === 700
    ) {

        showPerfectScoreAnimation();

        return;
    }

    showResultScreen();
}


/* =========================================================
توقف بازی
========================================================= */

function stopGame() {

    clearTimer();

    state.gameActive = false;

    showScreen(
        homeScreen
    );
}


/* =========================================================
انتخاب سطح
========================================================= */

document
    .querySelectorAll(".level-btn")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                const level =
                    button.dataset.level;

                if (level) {
                    startGame(level);
                }
            }
        );
    });


/* =========================================================
دکمه توقف
========================================================= */

stopButton.addEventListener(
    "click",
    stopGame
);


/* =========================================================
دکمه شروع مجدد
========================================================= */

restartButton.addEventListener(
    "click",
    () => {
        showScreen(homeScreen);
    }
);


/* =========================================================
راه‌اندازی برنامک سروش
========================================================= */

function initializeSoroushWebApp() {

    try {

        if (
            window.Soroush &&
            window.Soroush.WebApp
        ) {

            const webApp =
                window.Soroush.WebApp;

            if (
                typeof webApp.ready ===
                "function"
            ) {
                webApp.ready();
            }

            if (
                typeof webApp.expand ===
                "function"
            ) {
                webApp.expand();
            }
        }

    } catch (error) {

        console.error(
            "Soroush WebApp initialization error:",
            error
        );
    }
}

initializeSoroushWebApp();
