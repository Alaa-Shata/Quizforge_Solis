/* ======================================================
   QUIZFORGE - M2 QUIZ SESSION

   Supports:
   - Python Backend Integration
   - SQLite Question Bank
   - Mock Preview Mode
   - Quiz Setup
   - Answer Submission
   - Immediate Feedback
   - Timer
   - Timeout
   - Abandon Confirmation
   - Session Summary
   ====================================================== */


/* ================= DOM ELEMENTS ================= */

const nameInput = document.getElementById("learner-name");

const topicsContainer = document.getElementById("topics-container");

const questionOptions = document.getElementById("question-options");

const timeOptions = document.getElementById("time-options");

const startButton = document.getElementById("start-quiz");

const errorBox = document.getElementById("form-error");

const setupLayout = document.querySelector(".setup-layout");

const quizSection = document.querySelector(".quiz-section");

const quizHeading = document.querySelector(".quiz-heading");

const quizStage = document.getElementById("quiz-stage");


/* ================= SESSION CONFIGURATION ================= */

const session = {

    learnerName: "",

    selectedTopics: [],

    questionCount: 5,

    timeLimitSeconds: 600

};


let availableTopics = [];

let quizQuestions = [];

let currentQuestionIndex = 0;

let selectedAnswer = null;

let submittedAnswers = [];

let remainingSeconds = 600;

let timerInterval = null;

let quizStatus = "SETUP";

let backendMode = false;

let quizBridge = null;

let currentQuestion = null;

let currentAttemptStatus = null;


/* ======================================================
   BACKEND CONNECTION
   ====================================================== */

function connectBackend() {

    if (!window.qt || !window.QWebChannel) {
        document.body.innerHTML = '<main style="padding:40px;font-family:Arial;text-align:center"><h2>Backend Connection Unavailable</h2><p>QuizForge Preview requires the Python Backend. Please restart the Preview application.</p></main>';
        return;
    }

    new QWebChannel(
        window.qt.webChannelTransport,

        function (channel) {

            quizBridge = channel.objects.quizBridge;

            if (!quizBridge) {
                document.body.innerHTML = '<main style="padding:40px;font-family:Arial;text-align:center"><h2>Backend Connection Failed</h2><p>QuizForge could not find the quiz backend controller.</p></main>';
                return;
            }

            backendMode = true;

            quizBridge.topicsReady.connect(function (data) {

                try {

                    window.setQuizTopics(
                        JSON.parse(data)
                    );

                } catch (error) {

                    console.error(
                        "Could not load topics:",
                        error
                    );

                    showError(
                        "Could not load available topics."
                    );

                }

            });


            quizBridge.sessionStarted.connect(function (data) {

                const result = JSON.parse(data);

                quizQuestions = [];

                submittedAnswers = [];

                currentQuestionIndex = 0;

                currentQuestion = result.question;

                remainingSeconds = result.remaining_seconds ?? 0;

                quizStatus = "ACTIVE";

                enterQuizMode();

                renderQuizStage();

                showBackendQuestion(currentQuestion);

                updateTimerDisplay();

            });


            quizBridge.answerFeedback.connect(function (data) {

                const feedback = JSON.parse(data);

                handleBackendFeedback(feedback);

            });


            quizBridge.questionReady.connect(function (data) {

                const result = JSON.parse(data);

                currentQuestionIndex =
                    result.question_number - 1;

                currentQuestion = result.question;

                selectedAnswer = null;

                showBackendQuestion(currentQuestion);

            });


            quizBridge.sessionFinished.connect(function (data) {

                const result = JSON.parse(data);

                renderFinishedScreen(result);

            });


            quizBridge.errorOccurred.connect(function (message) {
                console.log("BACKEND ERROR RECEIVED:", message);
                handleBackendError(message);
            });


            quizBridge.timerUpdated.connect(function (seconds) {

                remainingSeconds = seconds;

                updateTimerDisplay();

            });


            quizBridge.loadTopics();

        }

    );

}


/* ================= TOPICS ================= */

window.setQuizTopics = function (topics) {

    if (!Array.isArray(topics)) {

        console.error(
            "Topics must be an array."
        );

        return;

    }

    availableTopics = topics;

    session.selectedTopics = [];

    renderTopics();

    updateSummary();

};


function initializeMockData() {

    if (!window.QUIZ_MOCK_DATA) {

        showError(
            "Question data could not be loaded."
        );

        return;

    }

    availableTopics =
        window.QUIZ_MOCK_DATA.topics || [];

    renderTopics();

    updateSummary();

}


/* ================= TOPIC RENDERING ================= */

function renderTopics() {

    if (!topicsContainer) return;

    topicsContainer.innerHTML = "";

    if (availableTopics.length === 0) {

        topicsContainer.innerHTML = `

            <div class="empty-state">

                <span>✧</span>

                <h4>Topics will appear here</h4>

                <p>No available topics were found.</p>

            </div>

        `;

        return;

    }

    const icons = [
        "✦",
        "◈",
        "◎",
        "⌘",
        "◇",
        "▦"
    ];

    availableTopics.forEach((topic, index) => {

        const card = document.createElement("button");

        card.type = "button";

        card.className = "topic-card";

        card.dataset.topicId = topic.id;

        const isSelected =
            session.selectedTopics.some(
                item => String(item.id) === String(topic.id)
            );

        if (isSelected) {
            card.classList.add("active");
        }

        card.innerHTML = `

            <span class="topic-icon">
                ${icons[index % icons.length]}
            </span>

            <span>

                <strong>${escapeHTML(topic.name)}</strong>

                <small>Select topic</small>

            </span>

            <span class="card-check">✓</span>

        `;

        card.addEventListener("click", function () {

            toggleTopic(topic);

        });

        topicsContainer.appendChild(card);

    });

}


function toggleTopic(topic) {

    const index = session.selectedTopics.findIndex(
        item => String(item.id) === String(topic.id)
    );

    if (index >= 0) {

        session.selectedTopics.splice(index, 1);

    } else {

        session.selectedTopics.push(topic);

    }

    renderTopics();

    updateSummary();

    clearError();

}


/* ================= NAME INPUT ================= */

if (nameInput) {

    nameInput.addEventListener("input", function () {

        session.learnerName = nameInput.value.trim();

        updateSummary();

        clearError();

    });

}


/* ================= QUESTION COUNT ================= */

if (questionOptions) {

    questionOptions.addEventListener("click", function (event) {

        const button = event.target.closest(".choice-button");

        if (!button) return;

        questionOptions
            .querySelectorAll(".choice-button")
            .forEach(item => item.classList.remove("active"));

        button.classList.add("active");

        session.questionCount = Number(
            button.dataset.count
        );

        updateSummary();

        clearError();

    });

}


/* ================= TIME LIMIT ================= */

if (timeOptions) {

    timeOptions.addEventListener("click", function (event) {

        const button = event.target.closest(".time-button");

        if (!button) return;

        timeOptions
            .querySelectorAll(".time-button")
            .forEach(item => item.classList.remove("active"));

        button.classList.add("active");

        session.timeLimitSeconds = Number(
            button.dataset.time
        );

        updateSummary();

        clearError();

    });

}


/* ================= SUMMARY ================= */

function updateSummary() {

    const summaryName =
        document.getElementById("summary-name");

    const summaryTopics =
        document.getElementById("summary-topics");

    const summaryCount =
        document.getElementById("summary-count");

    const summaryTime =
        document.getElementById("summary-time");

    if (summaryName) {

        summaryName.textContent =
            session.learnerName || "Not added yet";

    }

    if (summaryTopics) {

        summaryTopics.textContent =
            `${session.selectedTopics.length} topics`;

    }

    if (summaryCount) {

        summaryCount.textContent =
            session.questionCount;

    }

    if (summaryTime) {

        summaryTime.textContent =
            `${session.timeLimitSeconds / 60} min`;

    }

}


/* ================= VALIDATION ================= */

function validateSession() {

    const name = session.learnerName.trim();

    if (name.length < 2 || name.length > 40) {

        showError(
            "Your name must contain between 2 and 40 characters."
        );

        nameInput?.focus();

        return false;

    }

    if (session.selectedTopics.length === 0) {

        showError(
            "Please select at least one topic."
        );

        return false;

    }

    if (session.questionCount < 5 || session.questionCount > 30) {

        showError(
            "Question count must be between 5 and 30."
        );

        return false;

    }

    return true;

}


function handleBackendError(message) {
    console.log("BACKEND ERROR RECEIVED:", message);

    if (String(message).toLowerCase().includes("save")) {

        let panel = document.getElementById("retry-save-panel");

        if (!panel) {
            panel = document.createElement("div");
            panel.id = "retry-save-panel";
            panel.className = "finished-note";
            panel.style.marginTop = "16px";
            quizStage.appendChild(panel);
        }

        panel.innerHTML = `
            <p>${escapeHTML(message)}</p>
            <button
                id="retry-save-button"
                class="quiz-action-button"
                type="button"
            >
                Retry Save
            </button>
        `;

        const retryButton = document.getElementById("retry-save-button");

        retryButton.addEventListener("click", function () {
            retryButton.disabled = true;
            retryButton.textContent = "Retrying...";
            quizBridge.retrySave();
        });

        return;
    }

    showError(message);
}

function showError(message) {

    if (!errorBox) {

        console.error(message);

        return;

    }

    errorBox.textContent = message;

    errorBox.classList.add("visible");

}


function clearError() {

    if (!errorBox) return;

    errorBox.textContent = "";

    errorBox.classList.remove("visible");

}


/* ================= MOCK QUESTION RETRIEVAL ================= */

function getEligibleQuestions(topicIds) {
    if (!window.QUIZ_MOCK_DATA || !Array.isArray(window.QUIZ_MOCK_DATA.questions)) return [];
    const selectedTopics = new Set(topicIds.map(String));
    const uniqueQuestions = new Map();
    for (const question of window.QUIZ_MOCK_DATA.questions) {
        if (!selectedTopics.has(String(question.topic_id))) continue;
        const id = String(question.id);
        if (!uniqueQuestions.has(id)) uniqueQuestions.set(id, question);
    }
    return Array.from(uniqueQuestions.values());
}


function shuffleArray(items) {

    const result = [...items];

    for (let i = result.length - 1; i > 0; i--) {

        const j = Math.floor(
            Math.random() * (i + 1)
        );

        [result[i], result[j]] =
            [result[j], result[i]];

    }

    return result;

}


/* ================= START QUIZ ================= */

if (startButton) {

    startButton.addEventListener("click", startQuiz);

}


function startQuiz() {

    clearError();

    if (!validateSession()) return;

    const topicIds = [...new Set(session.selectedTopics.map(topic => Number(topic.id)))];

    const config = {

        learner_name: session.learnerName,

        topic_ids: topicIds,

        question_count: session.questionCount,

        time_limit_seconds: session.timeLimitSeconds

    };

    if (backendMode) {

        quizBridge.startQuiz(
            JSON.stringify(config)
        );

        return;

    }

    // Preview mode only.

    const eligibleQuestions =
        getEligibleQuestions(
            topicIds.map(String)
        );

    if (eligibleQuestions.length < session.questionCount) {

        showError(
            `Only ${eligibleQuestions.length} questions are available.`
        );

        return;

    }

    quizQuestions = shuffleArray(
        eligibleQuestions
    ).slice(0, session.questionCount);

    currentQuestionIndex = 0;

    selectedAnswer = null;

    submittedAnswers = [];

    remainingSeconds = session.timeLimitSeconds;

    quizStatus = "ACTIVE";

    enterQuizMode();

    renderQuizStage();

    showMockQuestion();

    startMockTimer();

}


function enterQuizMode() {

    document.body.classList.add("quiz-active");

    requestAnimationFrame(function () {

        window.scrollTo({
            top: 0,
            left: 0,
            behavior: "instant"
        });

    });

}


/* ================= QUIZ STAGE ================= */

function renderQuizStage() {

    if (!quizStage) {

        showError(
            "Quiz stage was not found."
        );

        return;

    }

    quizStage.hidden = false;

    quizStage.removeAttribute("hidden");

    quizStage.style.display = "block";

    quizStage.innerHTML = `

        <div class="quiz-topbar">

            <div>

                <span class="section-tag">
                    YOUR QUIZ SESSION
                </span>

                <h2>Stay focused. You've got this.</h2>

            </div>

            <button
                id="abandon-quiz"
                class="abandon-button"
                type="button"
            >
                Exit Quiz
            </button>

        </div>


        <div class="quiz-progress-card">

            <div class="quiz-progress-info">

                <span id="question-progress">
                    Question 1
                </span>

                <span id="difficulty-badge">
                    Medium Difficulty
                </span>

            </div>

            <div class="quiz-progress-track">

                <div id="quiz-progress-fill"></div>

            </div>

        </div>


        <div class="quiz-main-card">

            <div class="question-meta">

                <span id="question-topic">
                    TOPIC
                </span>

                <div id="timer-display" class="timer-display">
                    10:00
                </div>

            </div>

            <h3 id="question-text"></h3>

            <div id="answer-options" class="answer-options"></div>

            <div id="feedback-panel" class="feedback-panel"></div>

            <div class="quiz-actions">

                <button
                    id="submit-answer"
                    class="quiz-action-button"
                    type="button"
                    disabled
                >
                    Submit Answer →
                </button>

                <button
                    id="next-question"
                    class="quiz-action-button"
                    type="button"
                    style="display:none"
                >
                    Next Question →
                </button>

            </div>

        </div>

        <p class="quiz-footer-note">
            Take your time and choose the best answer.
        </p>

    `;

    document
        .getElementById("abandon-quiz")
        .addEventListener("click", abandonQuiz);

    document
        .getElementById("submit-answer")
        .addEventListener("click", submitAnswer);

    document
        .getElementById("next-question")
        .addEventListener("click", nextQuestion);

}


/* ================= MOCK QUESTION DISPLAY ================= */

function showMockQuestion() {

    currentQuestion =
        quizQuestions[currentQuestionIndex];

    if (!currentQuestion) {

        finishMockQuiz("COMPLETED");

        return;

    }

    const question = currentQuestion;

    const questionText =
        question.question || "Question unavailable.";

    const options =
        question.options || {};

    renderQuestion({

        id: question.id,

        text: questionText,

        options: options,

        topic_name: getTopicName(question.topic_id),

        difficulty: question.difficulty || 2

    });

}


/* ================= BACKEND QUESTION DISPLAY ================= */

function showBackendQuestion(question) {

    currentQuestion = question;

    renderQuestion(question);

}


/* ================= COMMON QUESTION DISPLAY ================= */

function renderQuestion(question) {

    const progressText =
        document.getElementById("question-progress");

    const topicElement =
        document.getElementById("question-topic");

    const questionText =
        document.getElementById("question-text");

    const difficultyBadge =
        document.getElementById("difficulty-badge");

    const progressFill =
        document.getElementById("quiz-progress-fill");

    const optionsContainer =
        document.getElementById("answer-options");

    const feedback =
        document.getElementById("feedback-panel");

    const submitButton =
        document.getElementById("submit-answer");

    const nextButton =
        document.getElementById("next-question");

    if (
        !progressText ||
        !topicElement ||
        !questionText ||
        !optionsContainer ||
        !submitButton ||
        !nextButton
    ) {

        return;

    }

    selectedAnswer = null;

    const total = backendMode
        ? session.questionCount
        : quizQuestions.length;

    progressText.textContent =
        `Question ${currentQuestionIndex + 1} of ${total}`;

    topicElement.textContent =
        (question.topic_name || "Quiz").toUpperCase();

    questionText.textContent =
        question.text || "Question unavailable.";

    const difficulty = Number(question.difficulty || 2);

    const difficultyNames = {
        1: "Easy Difficulty",
        2: "Medium Difficulty",
        3: "Hard Difficulty"
    };

    if (difficultyBadge) {

        difficultyBadge.textContent =
            difficultyNames[difficulty] || "Medium Difficulty";

    }

    progressFill.style.width =
        `${(currentQuestionIndex / total) * 100}%`;

    optionsContainer.innerHTML = "";

    Object.entries(question.options).forEach(
        ([key, value]) => {

            const button = document.createElement("button");

            button.type = "button";

            button.className = "answer-option";

            button.dataset.answer = key;

            button.innerHTML = `

                <span class="option-letter">
                    ${escapeHTML(key)}
                </span>

                <span class="option-text">
                    ${escapeHTML(value)}
                </span>

            `;

            button.addEventListener("click", function () {

                selectAnswer(key, button);

            });

            optionsContainer.appendChild(button);

        }
    );

    feedback.innerHTML = "";

    feedback.className = "feedback-panel";

    submitButton.style.display = "flex";

    submitButton.disabled = true;

    nextButton.style.display = "none";

    updateTimerDisplay();

    const card =
        document.querySelector(".quiz-main-card");

    if (card) {

        card.style.animation = "none";

        void card.offsetWidth;

        card.style.animation =
            "quizEnter .4s ease both";

    }

}


/* ================= TOPIC NAME ================= */

function getTopicName(topicId) {

    const topic = availableTopics.find(
        item => String(item.id) === String(topicId)
    );

    return topic ? topic.name : "Quiz";

}


/* ================= SELECT ANSWER ================= */

function selectAnswer(answer, button) {

    if (quizStatus !== "ACTIVE") return;

    selectedAnswer = answer;

    document
        .querySelectorAll(".answer-option")
        .forEach(option => {

            option.classList.remove("selected");

        });

    button.classList.add("selected");

    const submitButton =
        document.getElementById("submit-answer");

    if (submitButton) {

        submitButton.disabled = false;

    }

}


/* ================= SUBMIT ANSWER ================= */

function submitAnswer() {

    if (
        quizStatus !== "ACTIVE" ||
        !selectedAnswer
    ) {

        return;

    }

    if (backendMode) {

        quizBridge.submitAnswer(selectedAnswer);

        return;

    }

    const question = currentQuestion;

    const isCorrect =
        selectedAnswer === question.correct_answer;

    const feedback = {

        is_correct: isCorrect,

        correct_option: question.correct_answer,

        explanation: question.explanation || ""

    };

    submittedAnswers.push({

        question_id: question.id,

        selected_answer: selectedAnswer,

        is_correct: isCorrect

    });

    displayFeedback(feedback);

}


/* ================= BACKEND FEEDBACK ================= */

function handleBackendFeedback(feedback) {

    if (!currentQuestion) return;

    submittedAnswers.push({

        question_id: currentQuestion.id,

        selected_answer: selectedAnswer,

        is_correct: feedback.is_correct

    });

    displayFeedback(feedback);

}


/* ================= DISPLAY FEEDBACK ================= */

function displayFeedback(feedback) {

    const correctOption =
        feedback.correct_option;

    const options =
        document.querySelectorAll(".answer-option");

    options.forEach(option => {

        option.disabled = true;

        if (option.dataset.answer === correctOption) {

            option.classList.add("correct");

        }

        if (
            option.dataset.answer === selectedAnswer &&
            !feedback.is_correct
        ) {

            option.classList.add("incorrect");

        }

    });

    showFeedback(
        feedback.is_correct,
        feedback.explanation
    );

    const submitButton =
        document.getElementById("submit-answer");

    const nextButton =
        document.getElementById("next-question");

    if (submitButton) {

        submitButton.style.display = "none";

    }

    if (nextButton) {

        nextButton.style.display = "flex";

        nextButton.textContent =
            currentQuestionIndex === session.questionCount - 1
                ? "Finish Quiz ✓"
                : "Next Question →";

    }

    updateProgress();

}


/* ================= FEEDBACK ================= */

function showFeedback(isCorrect, explanation) {

    const panel =
        document.getElementById("feedback-panel");

    if (!panel) return;

    panel.className = isCorrect
        ? "feedback-panel correct-feedback visible"
        : "feedback-panel incorrect-feedback visible";

    panel.innerHTML = `

        <div class="feedback-heading">

            <span>
                ${isCorrect ? "✓" : "✕"}
            </span>

            <strong>
                ${isCorrect ? "Correct Answer!" : "Not Quite!"}
            </strong>

        </div>

        <p>
            ${escapeHTML(explanation || "No explanation is available.")}
        </p>

    `;

}


/* ================= PROGRESS ================= */

function updateProgress() {

    const progressFill =
        document.getElementById("quiz-progress-fill");

    if (!progressFill) return;

    const total = backendMode
        ? session.questionCount
        : quizQuestions.length;

    progressFill.style.width =
        `${((currentQuestionIndex + 1) / total) * 100}%`;

}


/* ================= NEXT QUESTION ================= */

function nextQuestion() {

    if (quizStatus !== "ACTIVE") return;

    if (backendMode) {

        quizBridge.nextQuestion();

        return;

    }

    currentQuestionIndex++;

    if (currentQuestionIndex >= quizQuestions.length) {

        finishMockQuiz("COMPLETED");

        return;

    }

    showMockQuestion();

}


/* ================= MOCK TIMER ================= */

function startMockTimer() {

    stopMockTimer();

    updateTimerDisplay();

    timerInterval = setInterval(function () {

        if (quizStatus !== "ACTIVE") {

            stopMockTimer();

            return;

        }

        remainingSeconds--;

        updateTimerDisplay();

        if (remainingSeconds <= 0) {

            stopMockTimer();

            finishMockQuiz("TIMED_OUT");

        }

    }, 1000);

}


function stopMockTimer() {

    if (timerInterval !== null) {

        clearInterval(timerInterval);

        timerInterval = null;

    }

}


/* ================= TIMER DISPLAY ================= */

function updateTimerDisplay() {

    const display =
        document.getElementById("timer-display");

    if (!display) return;

    const minutes =
        Math.floor(remainingSeconds / 60);

    const seconds =
        remainingSeconds % 60;

    display.textContent =
        `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

    display.className = "timer-display";

    if (remainingSeconds <= 10) {

        display.classList.add("timer-danger");

    } else if (remainingSeconds <= 60) {

        display.classList.add("timer-warning");

    }

}


/* ================= CUSTOM CONFIRM DIALOG ================= */

function showConfirmDialog() {

    const modal =
        document.getElementById("confirm-modal");

    if (!modal) return;

    modal.hidden = false;

    modal.classList.add("visible");

    const cancelButton =
        document.getElementById("modal-cancel");

    const okButton =
        document.getElementById("modal-ok");

    const closeModal = function () {

        modal.hidden = true;

        modal.classList.remove("visible");

    };

    cancelButton.onclick = closeModal;

    okButton.onclick = function () {

        closeModal();

        confirmAbandon();

    };

}


/* ================= ABANDON ================= */

function abandonQuiz() {

    if (quizStatus !== "ACTIVE") return;

    showConfirmDialog();

}


function confirmAbandon() {

    if (backendMode) {

        quizBridge.abandonQuiz();

        return;

    }

    finishMockQuiz("ABANDONED");

}


/* ================= MOCK FINISH ================= */

function finishMockQuiz(status) {
    if (quizStatus === "FINISHED") return;
    quizStatus = "FINISHED";
    stopMockTimer();
    const totalQuestions = quizQuestions.length;
    const questionsPresented = status === "COMPLETED" ? totalQuestions : Math.min(currentQuestionIndex + 1, totalQuestions);
    const presentedQuestions = quizQuestions.slice(0, questionsPresented);
    const answeredQuestions = submittedAnswers.length;
    const correctAnswers = submittedAnswers.filter(answer => answer.is_correct).length;
    const answersById = new Map(submittedAnswers.map(answer => [String(answer.question_id), answer]));
    const getWeight = question => {
        const difficulty = Number(question.difficulty);
        return [1, 2, 3].includes(difficulty) ? difficulty : 2;
    };
    const maxPoints = presentedQuestions.reduce((sum, question) => sum + getWeight(question), 0);
    const earnedPoints = presentedQuestions.reduce((sum, question) => {
        const answer = answersById.get(String(question.id));
        return sum + (answer && answer.is_correct ? getWeight(question) : 0);
    }, 0);
    renderFinishedScreen({
        status: status,
        total_questions: totalQuestions,
        questions_presented: questionsPresented,
        not_presented_questions: Math.max(0, totalQuestions - questionsPresented),
        answered_questions: answeredQuestions,
        correct_answers: correctAnswers,
        unanswered_questions: Math.max(0, questionsPresented - answeredQuestions),
        completion_percentage: totalQuestions > 0 ? answeredQuestions / totalQuestions * 100 : 0,
        earned_points: earnedPoints,
        max_points: maxPoints,
        score_percent: maxPoints > 0 ? earnedPoints / maxPoints * 100 : 0,
        attempt_id: null
    });
}


/* ================= FINISHED SCREEN ================= */

function renderFinishedScreen(result) {

    quizStatus = "FINISHED";

    stopMockTimer();

    const statusText = {

        COMPLETED: "Quiz Completed",

        TIMED_OUT: "Time's Up!",

        ABANDONED: "Quiz Abandoned"

    };

    const statusDescription = {

        COMPLETED:
            "You have completed your quiz session.",

        TIMED_OUT:
            "Your time limit has ended.",

        ABANDONED:
            "You exited the quiz before completing it."

    };

    const savedMessage = result.attempt_id
        ? `Attempt #${result.attempt_id} saved successfully.`
        : result.save_error
            ? "Your result could not be saved."
            : "Preview summary only.";

    quizStage.innerHTML = `

        <div class="finished-card">

            <div class="finished-icon">
                ${result.status === "COMPLETED" ? "✓" : "◷"}
            </div>

            <span class="section-tag">
                SESSION SUMMARY
            </span>

            <h2>
                ${statusText[result.status] || "Session Finished"}
            </h2>

            <p>
                ${statusDescription[result.status] || ""}
            </p>

            <div class="finished-stats">

                <div>
                    <strong>${result.total_questions}</strong>
                    <span>Total Questions</span>
                </div>

                <div>
                    <strong>${result.questions_presented ?? 0}</strong>
                    <span>Questions Presented</span>
                </div>

                <div>
                    <strong>${result.not_presented_questions ?? 0}</strong>
                    <span>Not Presented</span>
                </div>

                <div>
                    <strong>${Number(result.completion_percentage ?? 0).toFixed(2)}%</strong>
                    <span>Completion</span>
                </div>

                <div>
                    <strong>${result.answered_questions}</strong>
                    <span>Answered</span>
                </div>

                <div>
                    <strong>${result.correct_answers}</strong>
                    <span>Correct</span>
                </div>

                <div>
                    <strong>${result.unanswered_questions}</strong>
                    <span>Unanswered</span>
                </div>

            </div>

            <div class="finished-note">

                Score: ${result.earned_points}/${result.max_points}
                (${Number(result.score_percent).toFixed(2)}%)

                <br><br>

                ${escapeHTML(savedMessage)}

            </div>

            <button
                id="return-to-setup"
                class="quiz-action-button"
                type="button"
            >
                Back to Setup ↗
            </button>

        </div>

    `;

    const returnButton =
        document.getElementById("return-to-setup");

    returnButton.addEventListener(
        "click",
        returnToSetup
    );

}


/* ================= RETURN TO SETUP ================= */

function returnToSetup() {

    stopMockTimer();

    quizStatus = "SETUP";

    currentQuestionIndex = 0;

    selectedAnswer = null;

    submittedAnswers = [];

    quizQuestions = [];

    currentQuestion = null;

    if (quizStage) {

        quizStage.innerHTML = "";

        quizStage.hidden = true;

        quizStage.style.display = "";

    }

    document.body.classList.remove("quiz-active");

    if (quizSection) {

        quizSection.style.display = "";

        quizSection.style.visibility = "";

    }

    requestAnimationFrame(function () {

        quizSection?.scrollIntoView({

            behavior: "smooth",

            block: "start"

        });

    });

}


/* ================= BACK HOME ================= */

const backHomeButton =
    document.getElementById("back-home");

if (backHomeButton) {

    backHomeButton.addEventListener("click", function () {

        if (quizStatus === "ACTIVE") {

            abandonQuiz();

        } else {

            document
                .getElementById("home")
                ?.scrollIntoView({
                    behavior: "smooth"
                });

        }

    });

}


/* ================= HTML SAFETY ================= */

function escapeHTML(value) {

    return String(value ?? "")

        .replaceAll("&", "&amp;")

        .replaceAll("<", "&lt;")

        .replaceAll(">", "&gt;")

        .replaceAll('"', "&quot;")

        .replaceAll("'", "&#039;");

}


/* ================= SCROLL REVEAL ================= */



const revealElements =
    document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window) {

    const observer = new IntersectionObserver(

        entries => {

            entries.forEach(entry => {

                if (entry.isIntersecting) {

                    entry.target.classList.add("visible");

                    observer.unobserve(entry.target);

                }

            });

        },

        { threshold: 0.12 }

    );

    revealElements.forEach(element => {

        observer.observe(element);

    });

} else {

    revealElements.forEach(element => {

        element.classList.add("visible");

    });

}


/* ================= INITIALIZATION ================= */

updateSummary();

connectBackend();