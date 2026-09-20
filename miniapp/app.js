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

let perfectAnimationStyleAdded = false;


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
دریافت سؤال‌ها
========================================================= */

async function loadQuestions(level) {
    const url = DATA_URLS[level];

    if (!url) {
        throw new Error("سطح نامعتبر است");
    }

    const response = await fetch(
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

    const data = await response.json();

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
            return question["سطح"] === selectedLevel;
        }

        return true;
    });
}


/* =========================================================
ساخت گزینه‌ها
========================================================= */

function getOptions(question) {
    let options = question["گزینه‌ها"];

    if (Array.isArray(options)) {
        options = options.filter(option => {
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
        question["نوع سؤال"] === "صحیح/غلط"
    ) {
        return [
            "صحیح",
            "غلط"
        ];
    }

    let others =
        question["سایر گزینه‌های چالشی"];

    if (typeof others === "string") {
        others = others
            .split(/[،,]/)
            .map(option => option.trim())
            .filter(option => {
                return (
                    option !== "" &&
                    option !== "—" &&
                    option !== "-"
                );
            });
    } else if (Array.isArray(others)) {
        others = others
            .map(option => String(option).trim())
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
                .slice(0, QUESTION_COUNT)
                .map(question => ({
                    question,
                    options: getOptions(question)
                }));

        for (const item of state.questions) {
            if (item.options.length < 2) {
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
            document.createElement("button");

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
            document.createElement("button");

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

    if (state.timeLeft <= 10) {
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
    return question["پاسخ صحیح"] || "";
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
        clearInterval(state.timer);
        state.timer = null;
    }
}


/* =========================================================
CSS انیمیشن امتیاز کامل
========================================================= */

function addPerfectAnimationStyles() {

    if (perfectAnimationStyleAdded) {
        return;
    }

    const style =
        document.createElement("style");

    style.id =
        "perfect-score-animation-style";

    style.textContent = `

        .perfect-overlay {
            position: fixed;
            inset: 0;
            z-index: 99999;

            display: flex;
            align-items: center;
            justify-content: center;

            overflow: hidden;

            background:
                radial-gradient(
                    circle at center,
                    #273553 0%,
                    #111827 48%,
                    #050810 100%
                );

            opacity: 0;

            animation:
                perfectOverlayIn
                0.7s ease forwards;
        }

        .perfect-content {
            position: relative;
            z-index: 10;

            width: 100%;
            max-width: 500px;

            min-height: 100%;

            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;

            text-align: center;
        }

        .perfect-glow {
            position: absolute;

            width: 320px;
            height: 320px;

            border-radius: 50%;

            background:
                radial-gradient(
                    circle,
                    rgba(255,215,80,0.38),
                    rgba(255,193,7,0.12) 42%,
                    transparent 72%
                );

            filter: blur(8px);

            animation:
                perfectGlow
                2.2s ease-in-out infinite;
        }

        .perfect-ring {
            position: absolute;

            border: 1px solid
                rgba(255,215,90,0.25);

            border-radius: 50%;

            width: 360px;
            height: 360px;

            animation:
                perfectRing
                3s ease-in-out infinite;
        }

        .perfect-ring.two {
            width: 470px;
            height: 470px;

            animation-delay: 0.5s;
        }

        .perfect-ring.three {
            width: 610px;
            height: 610px;

            animation-delay: 1s;
        }

        .perfect-trophy {
            position: relative;
            z-index: 5;

            font-size: 105px;

            line-height: 1;

            opacity: 0;

            filter:
                drop-shadow(
                    0 0 12px
                    rgba(255,215,70,0.95)
                )
                drop-shadow(
                    0 0 35px
                    rgba(255,193,7,0.7)
                );

            animation:
                perfectTrophyIn
                1s
                cubic-bezier(.17,.89,.32,1.28)
                0.2s
                forwards,

                perfectTrophyFloat
                2.5s
                ease-in-out
                1.3s
                infinite;
        }

        .perfect-score-number {
            position: relative;
            z-index: 5;

            margin-top: 8px;

            font-size: 88px;
            font-weight: 900;

            line-height: 1;

            color: #ffd54f;

            text-shadow:
                0 0 10px
                rgba(255,215,70,0.9),

                0 0 28px
                rgba(255,193,7,0.7),

                0 0 55px
                rgba(255,193,7,0.35);

            opacity: 0;

            animation:
                perfectScoreIn
                0.8s
                cubic-bezier(.17,.89,.32,1.28)
                1s
                forwards;
        }

        .perfect-title {
            position: relative;
            z-index: 5;

            margin-top: 18px;

            font-size: 26px;
            font-weight: bold;

            color: #fff3b0;

            opacity: 0;

            animation:
                perfectTextIn
                0.8s
                ease
                1.7s
                forwards;
        }

        .perfect-subtitle {
            position: relative;
            z-index: 5;

            margin-top: 12px;

            padding: 0 25px;

            font-size: 16px;

            line-height: 1.9;

            color:
                rgba(255,255,255,0.84);

            opacity: 0;

            animation:
                perfectTextIn
                0.8s
                ease
                2s
                forwards;
        }

        .perfect-particle {
            position: absolute;

            width: 5px;
            height: 5px;

            border-radius: 50%;

            background: #ffd54f;

            box-shadow:
                0 0 7px #ffd54f,
                0 0 15px
                rgba(255,193,7,0.8);

            animation:
                perfectParticle
                linear
                infinite;
        }

        .perfect-confetti {
            position: absolute;

            top: -25px;

            width: 8px;
            height: 15px;

            border-radius: 1px;

            animation:
                perfectConfetti
                linear
                forwards;
        }

        @keyframes perfectOverlayIn {
            from {
                opacity: 0;
            }

            to {
                opacity: 1;
            }
        }

        @keyframes perfectGlow {
            0%, 100% {
                transform: scale(0.85);
                opacity: 0.55;
            }

            50% {
                transform: scale(1.18);
                opacity: 1;
            }
        }

        @keyframes perfectRing {
            0%, 100% {
                transform: scale(0.9);
                opacity: 0.12;
            }

            50% {
                transform: scale(1.05);
                opacity: 0.38;
            }
        }

        @keyframes perfectTrophyIn {
            0% {
                transform:
                    translateY(180px)
                    scale(0.2)
                    rotate(-15deg);

                opacity: 0;
            }

            70% {
                transform:
                    translateY(-15px)
                    scale(1.12)
                    rotate(3deg);

                opacity: 1;
            }

            100% {
                transform:
                    translateY(0)
                    scale(1)
                    rotate(0);

                opacity: 1;
            }
        }

        @keyframes perfectTrophyFloat {
            0%, 100% {
                transform:
                    translateY(0);
            }

            50% {
                transform:
                    translateY(-12px);
            }
        }

        @keyframes perfectScoreIn {
            0% {
                transform: scale(0.1);
                opacity: 0;
            }

            65% {
                transform: scale(1.18);
                opacity: 1;
            }

            100% {
                transform: scale(1);
                opacity: 1;
            }
        }

        @keyframes perfectTextIn {
            from {
                opacity: 0;
                transform:
                    translateY(20px);
            }

            to {
                opacity: 1;
                transform:
                    translateY(0);
            }
        }

        @keyframes perfectParticle {
            from {
                transform:
                    translateY(110vh)
                    rotate(0deg);

                opacity: 0;
            }

            10% {
                opacity: 1;
            }

            90% {
                opacity: 1;
            }

            to {
                transform:
                    translateY(-15vh)
                    rotate(360deg);

                opacity: 0;
            }
        }

        @keyframes perfectConfetti {
            0% {
                transform:
                    translateY(-25px)
                    rotate(0deg);

                opacity: 1;
            }

            100% {
                transform:
                    translateY(110vh)
                    rotate(720deg);

                opacity: 0;
            }
        }

    `;

    document.head.appendChild(style);

    perfectAnimationStyleAdded = true;
}


/* =========================================================
اجرای انیمیشن امتیاز کامل
========================================================= */

function showPerfectScoreAnimation() {

    addPerfectAnimationStyles();

    const oldOverlay =
        document.querySelector(
            ".perfect-overlay"
        );

    if (oldOverlay) {
        oldOverlay.remove();
    }

    const overlay =
        document.createElement("div");

    overlay.className =
        "perfect-overlay";

    const content =
        document.createElement("div");

    content.className =
        "perfect-content";

    const glow =
        document.createElement("div");

    glow.className =
        "perfect-glow";

    const ring1 =
        document.createElement("div");

    ring1.className =
        "perfect-ring";

    const ring2 =
        document.createElement("div");

    ring2.className =
        "perfect-ring two";

    const ring3 =
        document.createElement("div");

    ring3.className =
        "perfect-ring three";

    const trophy =
        document.createElement("div");

    trophy.className =
        "perfect-trophy";

    trophy.textContent =
        "🏆";

    const score =
        document.createElement("div");

    score.className =
        "perfect-score-number";

    score.textContent =
        "۰";

    const title =
        document.createElement("div");

    title.className =
        "perfect-title";

    title.textContent =
        "✨ امتیاز کامل! ✨";

    const subtitle =
        document.createElement("div");

    subtitle.className =
        "perfect-subtitle";

    subtitle.textContent =
        "شما هر ۷ سؤال را درست پاسخ دادید";

    content.appendChild(glow);

    content.appendChild(ring1);
    content.appendChild(ring2);
    content.appendChild(ring3);

    content.appendChild(trophy);
    content.appendChild(score);
    content.appendChild(title);
    content.appendChild(subtitle);

    overlay.appendChild(content);

    document.body.appendChild(overlay);


    /* -----------------------------------------
       ذرات نور
    ----------------------------------------- */

    for (let i = 0; i < 35; i++) {

        const particle =
            document.createElement("div");

        particle.className =
            "perfect-particle";

        particle.style.left =
            Math.random() * 100 + "%";

        particle.style.animationDuration =
            (3 + Math.random() * 5) + "s";

        particle.style.animationDelay =
            Math.random() * 4 + "s";

        const size =
            2 + Math.random() * 5;

        particle.style.width =
            size + "px";

        particle.style.height =
            size + "px";

        overlay.appendChild(particle);
    }


    /* -----------------------------------------
       Confetti
    ----------------------------------------- */

    const confettiColors = [
        "#FFD54F",
        "#FFB300",
        "#FFF176",
        "#FFFFFF",
        "#F5C542"
    ];

    for (let i = 0; i < 100; i++) {

        const piece =
            document.createElement("div");

        piece.className =
            "perfect-confetti";

        piece.style.left =
            Math.random() * 100 + "%";

        piece.style.animationDuration =
            (3 + Math.random() * 4) + "s";

        piece.style.animationDelay =
            Math.random() * 1.3 + "s";

        piece.style.background =
            confettiColors[
                Math.floor(
                    Math.random() *
                    confettiColors.length
                )
            ];

        const width =
            5 + Math.random() * 7;

        piece.style.width =
            width + "px";

        piece.style.height =
            width * 1.7 + "px";

        overlay.appendChild(piece);
    }


    /* -----------------------------------------
       شمارش متحرک ۰ تا ۷۰۰
    ----------------------------------------- */

    const duration = 1300;

    const start =
        performance.now();

    function updateScore(now) {

        const progress =
            Math.min(
                (now - start) / duration,
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

        score.textContent =
            toPersianNumber(value);

        if (progress < 1) {
            requestAnimationFrame(
                updateScore
            );
        } else {
            score.textContent =
                "۷۰۰";
        }
    }

    setTimeout(() => {
        requestAnimationFrame(
            updateScore
        );
    }, 1000);


    /* -----------------------------------------
       بعد از پایان انیمیشن
       نمایش نتیجه اصلی
    ----------------------------------------- */

    setTimeout(() => {

        if (
            overlay &&
            overlay.parentNode
        ) {
            overlay.remove();
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

    if (state.score >= 600) {
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

    /*
     * فقط در صورتی که امتیاز دقیقاً ۷۰۰ باشد،
     * انیمیشن ویژه اجرا می‌شود.
     */

    if (state.score === 700) {
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
