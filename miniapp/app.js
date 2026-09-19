const API_URL = "/api";

const QUESTION_COUNT = 7;
const QUESTION_TIME = 90;

let selectedLevel = null;
let questions = [];
let currentQuestion = 0;
let score = 0;
let correctAnswers = 0;
let wrongAnswers = 0;
let unanswered = 0;
let timerInterval = null;
let answered = false;

const homeScreen = document.getElementById("home-screen");
const levelScreen = document.getElementById("level-screen");
const gameScreen = document.getElementById("game-screen");
const resultScreen = document.getElementById("result-screen");

const startButton = document.getElementById("start-button");
const restartButton = document.getElementById("restart-button");

const questionNumber = document.getElementById("question-number");
const scoreElement = document.getElementById("score");
const timerElement = document.getElementById("timer");
const questionElement = document.getElementById("question");
const optionsElement = document.getElementById("options");

const resultLevel = document.getElementById("result-level");
const resultCorrect = document.getElementById("result-correct");
const resultWrong = document.getElementById("result-wrong");
const resultUnanswered = document.getElementById("result-unanswered");
const resultScore = document.getElementById("result-score");


function showScreen(screen) {
    homeScreen.classList.add("hidden");
    levelScreen.classList.add("hidden");
    gameScreen.classList.add("hidden");
    resultScreen.classList.add("hidden");

    screen.classList.remove("hidden");
}


function shuffle(array) {
    const copy = [...array];

    for (let i = copy.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));

        [copy[i], copy[j]] = [copy[j], copy[i]];
    }

    return copy;
}


function toPersianNumber(value) {
    return String(value).replace(/\d/g, digit => {
        return "۰۱۲۳۴۵۶۷۸۹"[digit];
    });
}


function startGame(level) {
    selectedLevel = level;

    fetch(`${API_URL}/questions?level=${encodeURIComponent(level)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error("خطا در دریافت سؤال‌ها");
            }

            return response.json();
        })
        .then(data => {
            if (!data.questions || data.questions.length < QUESTION_COUNT) {
                alert("تعداد سؤال‌های این سطح کافی نیست.");
                return;
            }

            questions = shuffle(data.questions).slice(
                0,
                QUESTION_COUNT
            );

            currentQuestion = 0;
            score = 0;
            correctAnswers = 0;
            wrongAnswers = 0;
            unanswered = 0;

            showScreen(gameScreen);

            showQuestion();
        })
        .catch(error => {
            console.error(error);

            alert(
                "دریافت سؤال‌ها با مشکل مواجه شد.\n" +
                "لطفاً دوباره تلاش کنید."
            );
        });
}


function showQuestion() {
    clearInterval(timerInterval);

    if (currentQuestion >= QUESTION_COUNT) {
        finishGame();
        return;
    }

    answered = false;

    const item = questions[currentQuestion];

    questionNumber.textContent =
        `سؤال ${toPersianNumber(currentQuestion + 1)} از ${toPersianNumber(QUESTION_COUNT)}`;

    scoreElement.textContent =
        `امتیاز: ${toPersianNumber(score)}`;

    questionElement.textContent = item.question;

    optionsElement.innerHTML = "";

    const options = shuffle(item.options);

    options.forEach((option, index) => {
        const button = document.createElement("button");

        button.className = "option-button";
        button.textContent = option;

        button.addEventListener("click", () => {
            submitAnswer(option, index, button);
        });

        optionsElement.appendChild(button);
    });

    startTimer();
}


function startTimer() {
    let remaining = QUESTION_TIME;

    timerElement.textContent = toPersianNumber(remaining);

    timerInterval = setInterval(() => {
        remaining--;

        timerElement.textContent =
            toPersianNumber(Math.max(remaining, 0));

        if (remaining <= 0) {
            clearInterval(timerInterval);

            if (!answered) {
                handleTimeout();
            }
        }
    }, 1000);
}


function disableOptions() {
    const buttons = optionsElement.querySelectorAll(
        ".option-button"
    );

    buttons.forEach(button => {
        button.disabled = true;
    });
}


function submitAnswer(selectedAnswer, selectedIndex, clickedButton) {
    if (answered) {
        return;
    }

    answered = true;

    clearInterval(timerInterval);

    disableOptions();

    const item = questions[currentQuestion];

    const isCorrect =
        selectedAnswer === item.correct_answer;

    if (isCorrect) {
        score += 100;
        correctAnswers++;

        clickedButton.textContent =
            `✅ ${selectedAnswer}`;

    } else {
        wrongAnswers++;

        if (wrongAnswers % 2 === 0) {
            score -= 15;
        }

        clickedButton.textContent =
            `❌ ${selectedAnswer}`;
    }

    scoreElement.textContent =
        `امتیاز: ${toPersianNumber(score)}`;

    setTimeout(() => {
        currentQuestion++;
        showQuestion();
    }, 700);
}


function handleTimeout() {
    if (answered) {
        return;
    }

    answered = true;

    disableOptions();

    unanswered++;

    questionElement.textContent =
        "⏱ زمان این سؤال تمام شد.";

    setTimeout(() => {
        currentQuestion++;
        showQuestion();
    }, 700);
}


function finishGame() {
    clearInterval(timerInterval);

    showScreen(resultScreen);

    const levelNames = {
        ashenaei: "آشنایی",
        danaei: "دانایی",
        ostad: "استادی"
    };

    resultLevel.textContent =
        levelNames[selectedLevel] || selectedLevel;

    resultCorrect.textContent =
        toPersianNumber(correctAnswers);

    resultWrong.textContent =
        toPersianNumber(wrongAnswers);

    resultUnanswered.textContent =
        toPersianNumber(unanswered);

    resultScore.textContent =
        toPersianNumber(score);
}


startButton.addEventListener("click", () => {
    showScreen(levelScreen);
});


document.querySelectorAll(".level-button").forEach(button => {
    button.addEventListener("click", () => {
        const level = button.dataset.level;

        startGame(level);
    });
});


restartButton.addEventListener("click", () => {
    selectedLevel = null;
    questions = [];
    currentQuestion = 0;
    score = 0;
    correctAnswers = 0;
    wrongAnswers = 0;
    unanswered = 0;

    showScreen(homeScreen);
});
