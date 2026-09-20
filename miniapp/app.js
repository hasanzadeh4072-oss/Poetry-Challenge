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
            position: fixed !important;
            top: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            left: 0 !important;

            width: 100vw !important;
            height: 100vh !important;

            z-index: 2147483647 !important;

            display: flex !important;
            align-items: center !important;
            justify-content: center !important;

            overflow: hidden !important;

            margin: 0 !important;
            padding: 0 !important;

            box-sizing: border-box !important;

            background:
                radial-gradient(
                    circle at center,
                    #303d60 0%,
                    #151c30 42%,
                    #05070d 100%
                ) !important;

            opacity: 1 !important;

            isolation: isolate !important;
        }


        .perfect-content {
            position: relative !important;

            width: 100% !important;
            height: 100% !important;

            display: flex !important;
            flex-direction: column !important;

            align-items: center !important;
            justify-content: center !important;

            text-align: center !important;

            z-index: 10 !important;

            overflow: hidden !important;

            box-sizing: border-box !important;
        }


        .perfect-glow {
            position: absolute !important;

            width: 330px !important;
            height: 330px !important;

            border-radius: 50% !important;

            background:
                radial-gradient(
                    circle,
                    rgba(255,215,70,0.48),
                    rgba(255,193,7,0.18) 40%,
                    transparent 72%
                ) !important;

            filter: blur(7px) !important;

            z-index: 1 !important;

            animation:
                perfectGlow
                2s ease-in-out infinite !important;
        }


        .perfect-ring {
            position: absolute !important;

            width: 300px !important;
            height: 300px !important;

            border:
                2px solid
                rgba(255,215,70,0.28) !important;

            border-radius: 50% !important;

            z-index: 2 !important;

            animation:
                perfectRing
                2.8s ease-in-out infinite !important;
        }


        .perfect-ring.two {
            width: 430px !important;
            height: 430px !important;

            animation-delay: 0.4s !important;
        }


        .perfect-ring.three {
            width: 580px !important;
            height: 580px !important;

            animation-delay: 0.8s !important;
        }


        .perfect-trophy {
            position: relative !important;

            z-index: 20 !important;

            font-size: 105px !important;

            line-height: 1 !important;

            opacity: 0 !important;

            transform:
                translateY(100px)
                scale(0.35) !important;

            filter:
                drop-shadow(
                    0 0 12px
                    rgba(255,215,70,1)
                )
                drop-shadow(
                    0 0 35px
                    rgba(255,193,7,0.9)
                ) !important;

            animation:
                perfectTrophy
                1s
                cubic-bezier(.17,.89,.32,1.28)
                forwards !important;
        }


        .perfect-score-number {
            position: relative !important;

            z-index: 20 !important;

            margin-top: 12px !important;

            font-size: 88px !important;
            font-weight: 900 !important;

            line-height: 1 !important;

            color: #ffd54f !important;

            text-shadow:
                0 0 10px rgba(255,215,70,1),
                0 0 25px rgba(255,193,7,0.9),
                0 0 50px rgba(255,193,7,0.55) !important;

            opacity: 0 !important;

            transform: scale(0.2) !important;

            animation:
                perfectScore
                0.9s
                cubic-bezier(.17,.89,.32,1.28)
                0.6s
                forwards !important;
        }


        .perfect-title {
            position: relative !important;

            z-index: 20 !important;

            margin-top: 22px !important;

            font-size: 28px !important;
            font-weight: 900 !important;

            color: #fff4b0 !important;

            text-shadow:
                0 0 12px
                rgba(255,215,70,0.7) !important;

            opacity: 0 !important;

            animation:
                perfectText
                0.7s
                ease
                1.3s
                forwards !important;
        }


        .perfect-subtitle {
            position: relative !important;

            z-index: 20 !important;

            margin-top: 12px !important;

            padding: 0 24px !important;

            font-size: 17px !important;

            line-height: 1.9 !important;

            color:
                rgba(255,255,255,0.9) !important;

            opacity: 0 !important;

            animation:
                perfectText
                0.7s
                ease
                1.6s
                forwards !important;
        }


        .perfect-particle {
            position: absolute !important;

            z-index: 5 !important;

            width: 5px;
            height: 5px;

            border-radius: 50% !important;

            background: #ffd54f !important;

            box-shadow:
                0 0 8px #ffd54f,
                0 0 18px #ffb300 !important;

            animation:
                perfectParticle
                linear
                infinite !important;
        }


        .perfect-confetti {
            position: absolute !important;

            top: -30px !important;

            z-index: 15 !important;

            width: 8px;
            height: 15px;

            border-radius: 2px !important;

            animation:
                perfectConfetti
                linear
                forwards !important;
        }


        @keyframes perfectGlow {
            0%, 100% {
                transform: scale(0.8);
                opacity: 0.5;
            }

            50% {
                transform: scale(1.2);
                opacity: 1;
            }
        }


        @keyframes perfectRing {
            0%, 100% {
                transform: scale(0.88);
                opacity: 0.12;
            }

            50% {
                transform: scale(1.08);
                opacity: 0.42;
            }
        }


        @keyframes perfectTrophy {
            0% {
                opacity: 0;
                transform:
                    translateY(130px)
                    scale(0.25)
                    rotate(-15deg);
            }

            65% {
                opacity: 1;
                transform:
                    translateY(-12px)
                    scale(1.12)
                    rotate(4deg);
            }

            100% {
                opacity: 1;
                transform:
                    translateY(0)
                    scale(1)
                    rotate(0);
            }
        }


        @keyframes perfectScore {
            0% {
                opacity: 0;
                transform: scale(0.15);
            }

            65% {
                opacity: 1;
                transform: scale(1.18);
            }

            100% {
                opacity: 1;
                transform: scale(1);
            }
        }


        @keyframes perfectText {
            from {
                opacity: 0;
                transform: translateY(20px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
            }
        }


        @keyframes perfectParticle {
            0% {
                transform:
                    translateY(110vh)
                    scale(0.4)
                    rotate(0deg);

                opacity: 0;
            }

            15% {
                opacity: 1;
            }

            85% {
                opacity: 1;
            }

            100% {
                transform:
                    translateY(-15vh)
                    scale(1)
                    rotate(360deg);

                opacity: 0;
            }
        }


        @keyframes perfectConfetti {
            0% {
                transform:
                    translateY(-30px)
                    rotate(0deg);

                opacity: 1;
            }

            100% {
                transform:
                    translateY(115vh)
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


    /* -----------------------------------------
       نمایش مستقیم روی کل صفحه
    ----------------------------------------- */

    document.body.appendChild(
        overlay
    );


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
            Math.random() * 3 + "s";

        const size =
            2 + Math.random() * 5;

        particle.style.width =
            size + "px";

        particle.style.height =
            size + "px";

        overlay.appendChild(
            particle
        );
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
            (2.5 + Math.random() * 3.5) + "s";

        piece.style.animationDelay =
            Math.random() * 1.2 + "s";

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

        overlay.appendChild(
            piece
        );
    }


    /* -----------------------------------------
       شمارش ۰ تا ۷۰۰
    ----------------------------------------- */

    const duration = 1500;

    const start =
        performance.now();

    function updateScore(now) {

        if (
            !overlay.parentNode
        ) {
            return;
        }

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


    requestAnimationFrame(
        updateScore
    );


    /* -----------------------------------------
       پایان انیمیشن
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
