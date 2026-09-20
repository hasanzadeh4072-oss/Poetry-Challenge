"use strict";

const QUESTION_COUNT = 7;
const QUESTION_TIME = 90;

const API_URL = "/api";

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

function toPersianNumber(value) {
    return String(value).replace(/\d/g, digit => "۰۱۲۳۴۵۶۷۸۹"[digit]);
}

function showScreen(screen) {
    [homeScreen, gameScreen, resultScreen].forEach(item => {
        item.classList.remove("active");
    });

    screen.classList.add("active");
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
        `${API_URL}/questions?level=${encodeURIComponent(level)}`
    );

    if (!response.ok) {
        throw new Error("خطا در دریافت سؤال‌ها");
    }

    const data = await response.json();

    if (!data || !Array.isArray(data.questions)) {
        throw new Error("ساختار سؤال‌ها نامعتبر است");
    }

    return data.questions;
}

async function startGame(level) {
    state.level = level;
    state.levelName = LEVEL_NAMES[level] || level;

    state.currentQuestion = 0;
    state.score = 0;
    state.wrongAnswers = 0;
    state.gameActive = false;

    levelName.textContent = state.levelName;
    scoreElement.textContent = toPersianNumber(0);

    showScreen(gameScreen);

    questionText.textContent = "در حال آماده‌سازی چالش...";
    optionsContainer.innerHTML = "";

    try {
        const allQuestions = await loadQuestions(level);

        if (allQuestions.length < QUESTION_COUNT) {
            throw new Error("تعداد سؤال‌های این سطح کافی نیست");
        }

        state.questions = shuffle(allQuestions).slice(0, QUESTION_COUNT);
        state.gameActive = true;

        showQuestion();

    } catch (error) {
        console.error(error);

        questionText.textContent =
            "دریافت سؤال‌ها با مشکل مواجه شد.";

        optionsContainer.innerHTML = "";

        const retryButton = document.createElement("button");

        retryButton.className = "primary-btn";
        retryButton.textContent = "🔄 تلاش دوباره";

        retryButton.addEventListener("click", () => {
            startGame(level);
        });

        optionsContainer.appendChild(retryButton);
    }
}

function showQuestion() {
    clearTimer();

    if (!state.gameActive) {
        return;
    }

    if (state.currentQuestion >= state.questions.length) {
        finishGame();
        return;
    }

    const current = state.questions[state.currentQuestion];

    state.answered = false;
    state.timeLeft = QUESTION_TIME;

    questionNumber.textContent =
        toPersianNumber(state.currentQuestion + 1);

    questionText.textContent =
        current.question || current["سؤال"] || "";

    optionsContainer.innerHTML = "";

    let options = current.options || current["گزینه‌ها"];

    if (!Array.isArray(options)) {
        options = [];
    }

    options = shuffle(options);

    options.forEach(option => {
        const button = document.createElement("button");

        button.className = "option-btn";
        button.type = "button";

        button.textContent =
            typeof option === "object"
                ? option.text || option["متن"] || option.answer || ""
                : option;

        button.addEventListener("click", () => {
            answerQuestion(option, button);
        });

        optionsContainer.appendChild(button);
    });

    updateTimer();

    state.timer = setInterval(() => {
        state.timeLeft--;

        updateTimer();

        if (state.timeLeft <= 0) {
            clearTimer();
            timeExpired();
        }
    }, 1000);
}

function updateTimer() {
    const minutes = Math.floor(state.timeLeft / 60);
    const seconds = state.timeLeft % 60;

    timerElement.textContent =
        `${toPersianNumber(minutes)}:${toPersianNumber(
            String(seconds).padStart(2, "0")
        )}`;

    timerElement.classList.remove("warning", "danger");

    if (state.timeLeft <= 10) {
        timerElement.classList.add("danger");
    } else if (state.timeLeft <= 30) {
        timerElement.classList.add("warning");
    }
}

function normalizeText(value) {
    return String(value ?? "")
        .trim()
        .replace(/ي/g, "ی")
        .replace(/ك/g, "ک");
}

function getCorrectAnswer(question) {
    return (
        question.correct_answer ??
        question["پاسخ صحیح"] ??
        question.correct ??
        ""
    );
}

function isCorrect(option, question) {
    const correctAnswer = getCorrectAnswer(question);

    if (typeof option === "object") {
        const optionValue =
            option.value ??
            option["مقدار"] ??
            option.answer ??
            option["پاسخ"] ??
            option.text ??
            option["متن"];

        return (
            normalizeText(optionValue) ===
            normalizeText(correctAnswer)
        );
    }

    return (
        normalizeText(option) ===
        normalizeText(correctAnswer)
    );
}

function answerQuestion(option, selectedButton) {
    if (
        !state.gameActive ||
        state.answered
    ) {
        return;
    }

    state.answered = true;

    clearTimer();

    const current = state.questions[state.currentQuestion];

    const correct = isCorrect(option, current);

    const buttons =
        optionsContainer.querySelectorAll(".option-btn");

    buttons.forEach(button => {
        button.disabled = true;
    });

    if (correct) {
        state.score += 100;
        selectedButton.classList.add("correct");
    } else {
        state.wrongAnswers++;

        selectedButton.classList.add("wrong");

        if (state.wrongAnswers % 2 === 0) {
            state.score -= 15;
        }

        buttons.forEach(button => {
            const buttonValue = button.textContent;

            if (
                normalizeText(buttonValue) ===
                normalizeText(getCorrectAnswer(current))
            ) {
                button.classList.add("correct");
            }
        });
    }

    scoreElement.textContent =
        toPersianNumber(state.score);

    setTimeout(() => {
        nextQuestion();
    }, 700);
}

function timeExpired() {
    if (
        !state.gameActive ||
        state.answered
    ) {
        return;
    }

    state.answered = true;

    const buttons =
        optionsContainer.querySelectorAll(".option-btn");

    buttons.forEach(button => {
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
        state.questions.length
    ) {
        finishGame();
    } else {
        showQuestion();
    }
}

function clearTimer() {
    if (state.timer !== null) {
        clearInterval(state.timer);
        state.timer = null;
    }
}

function finishGame() {
    clearTimer();

    state.gameActive = false;

    resultLevel.textContent = state.levelName;

    finalScore.textContent =
        toPersianNumber(state.score);

    let message;

    if (state.score >= 600) {
        message = "فوق‌العاده! 🌟";
    } else if (state.score >= 400) {
        message = "عالی! 👏";
    } else if (state.score >= 200) {
        message = "خوب بود! 🌿";
    } else {
        message = "این پایان راه نیست؛ دوباره تلاش کن. 💚";
    }

    resultMessage.textContent = message;

    showScreen(resultScreen);
}

function stopGame() {
    if (!state.gameActive) {
        showScreen(homeScreen);
        return;
    }

    clearTimer();

    state.gameActive = false;

    showScreen(homeScreen);
}

document.querySelectorAll(".level-btn").forEach(button => {
    button.addEventListener("click", () => {
        const level = button.dataset.level;

        if (level) {
            startGame(level);
        }
    });
});

stopButton.addEventListener("click", stopGame);

restartButton.addEventListener("click", () => {
    showScreen(homeScreen);
});

function initializeSoroushWebApp() {
    try {
        if (
            window.Soroush &&
            window.Soroush.WebApp
        ) {
            const webApp = window.Soroush.WebApp;

            if (typeof webApp.ready === "function") {
                webApp.ready();
            }

            if (typeof webApp.expand === "function") {
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
