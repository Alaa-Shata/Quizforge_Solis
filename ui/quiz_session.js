/* ======================================================
   QUIZFORGE - M2 QUIZ SESSION

   UI PROTOTYPE

   Includes:
   - Setup validation
   - Topic selection
   - Temporary mock question retrieval
   - Full-screen quiz mode
   - Active quiz
   - Answer submission
   - Immediate feedback
   - Progress tracking
   - Demo countdown
   - Timeout
   - Abandon confirmation
   - Finished screen

   Production scoring, adaptive difficulty and persistence
   will be connected to the approved team services.
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


/* ================= SESSION CONFIGURATION ================= */

const session = {
    learnerName: "",
    selectedTopics: [],
    questionCount: 5,
    timeLimitSeconds: 0
};

let availableTopics = [];
let quizQuestions = [];

let currentQuestionIndex = 0;
let selectedAnswer = null;
let submittedAnswers = [];

let remainingSeconds = 0;
let timerInterval = null;

let quizStatus = "SETUP";


/* ======================================================
   TOPIC INTEGRATION

   Jana's Question Bank data will replace the mock data
   when the team integration is ready.
   ====================================================== */

window.setQuizTopics = function(topics) {

    if (!Array.isArray(topics)) {
        console.error("Topics must be provided as an array.");
        return;
    }

    availableTopics = topics;
    session.selectedTopics = [];

    renderTopics();
    updateSummary();

};


/* ================= MOCK DATA INITIALIZATION ================= */

function initializeMockData() {

    if (!window.QUIZ_MOCK_DATA) {
        console.error(
            "Mock data was not loaded. Check the script order in HTML."
        );

        showError("Question data could not be loaded.");
        return;
    }

    if (
        !Array.isArray(window.QUIZ_MOCK_DATA.topics) ||
        !Array.isArray(window.QUIZ_MOCK_DATA.questions)
    ) {
        console.error("Mock data has an invalid structure.");
        showError("Question data has an invalid format.");
        return;
    }

    // TEMPORARY DEMO DATA.
    // Replace this source when the real Question Bank is integrated.

    availableTopics = window.QUIZ_MOCK_DATA.topics;

    renderTopics();
    updateSummary();

}


/* ================= TOPIC RENDERING ================= */

function renderTopics() {

    if (!topicsContainer) {
        console.error("Topics container was not found.");
        return;
    }

    topicsContainer.innerHTML = "";

    if (availableTopics.length === 0) {

        topicsContainer.innerHTML = `
            <div class="empty-state">
                <span>✧</span>
                <h4>Topics will appear here</h4>
                <p>Available topics will be loaded from the Question Bank.</p>
            </div>
        `;

        return;
    }

    const icons = ["✦", "◈", "◎", "⌘", "◇", "▦"];

    availableTopics.forEach((topic, index) => {

        const card = document.createElement("button");

        card.type = "button";
        card.className = "topic-card";
        card.dataset.topicId = topic.id;

        const isSelected = session.selectedTopics.some(
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

        card.addEventListener("click", () => {
            toggleTopic(topic);
        });

        topicsContainer.appendChild(card);

    });

}


/* ================= TOPIC SELECTION ================= */

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

    nameInput.addEventListener("input", () => {

        session.learnerName = nameInput.value.trim();

        updateSummary();
        clearError();

    });

}


/* ================= QUESTION COUNT ================= */

if (questionOptions) {

    questionOptions.addEventListener("click", event => {

        const button = event.target.closest(".choice-button");

        if (!button) return;

        questionOptions.querySelectorAll(".choice-button").forEach(item => {
            item.classList.remove("active");
        });

        button.classList.add("active");

        session.questionCount = Number(button.dataset.count);

        updateSummary();
        clearError();

    });

}


/* ================= TIME LIMIT ================= */

if (timeOptions) {

    timeOptions.addEventListener("click", event => {

        const button = event.target.closest(".time-button");

        if (!button) return;

        timeOptions.querySelectorAll(".time-button").forEach(item => {
            item.classList.remove("active");
        });

        button.classList.add("active");

        session.timeLimitSeconds = Number(button.dataset.time);

        updateSummary();
        clearError();

    });

}


/* ================= SUMMARY ================= */

function updateSummary() {

    const summaryName = document.getElementById("summary-name");
    const summaryTopics = document.getElementById("summary-topics");
    const summaryCount = document.getElementById("summary-count");
    const summaryTime = document.getElementById("summary-time");

    if (summaryName) {
        summaryName.textContent =
            session.learnerName || "Not added yet";
    }

    if (summaryTopics) {
        summaryTopics.textContent =
            `${session.selectedTopics.length} topics`;
    }

    if (summaryCount) {
        summaryCount.textContent = session.questionCount;
    }

    if (summaryTime) {
        summaryTime.textContent =
            session.timeLimitSeconds === 0
                ? "Unlimited"
                : `${session.timeLimitSeconds / 60} min`;
    }

}


/* ================= VALIDATION ================= */

function validateSession() {

    const name = session.learnerName.trim();

    if (name.length < 2 || name.length > 40) {

        showError("Your name must contain between 2 and 40 characters.");

        if (nameInput) nameInput.focus();

        return false;
    }

    if (session.selectedTopics.length === 0) {

        showError("Please select at least one topic.");

        return false;
    }

    const selectedIds = session.selectedTopics.map(topic =>
        String(topic.id)
    );

    const eligibleQuestions = getEligibleQuestions(selectedIds);

    if (eligibleQuestions.length < session.questionCount) {

        showError(
            `Only ${eligibleQuestions.length} questions are available for your selected topics.`
        );

        return false;
    }

    return true;

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


/* ================= QUESTION RETRIEVAL ================= */

function getEligibleQuestions(topicIds) {

    if (
        !window.QUIZ_MOCK_DATA ||
        !Array.isArray(window.QUIZ_MOCK_DATA.questions)
    ) {
        return [];
    }

    return window.QUIZ_MOCK_DATA.questions.filter(question =>
        topicIds.includes(String(question.topic_id))
    );

}


function shuffleArray(items) {

    const result = [...items];

    for (let i = result.length - 1; i > 0; i--) {

        const j = Math.floor(Math.random() * (i + 1));

        [result[i], result[j]] = [result[j], result[i]];

    }

    return result;

}


/* ================= START QUIZ ================= */

if (startButton) {
    startButton.addEventListener("click", startQuiz);
}


function startQuiz() {

    clearError();

    if (!validateSession()) {
        return;
    }

    const topicIds = session.selectedTopics.map(topic => topic.id);

    const eligibleQuestions = getEligibleQuestions(
        topicIds.map(String)
    );

    quizQuestions = shuffleArray(eligibleQuestions).slice(
        0,
        session.questionCount
    );

    if (quizQuestions.length === 0) {
        showError("No questions are available for this quiz.");
        return;
    }

    currentQuestionIndex = 0;
    selectedAnswer = null;
    submittedAnswers = [];

    remainingSeconds = session.timeLimitSeconds;
    quizStatus = "ACTIVE";

    const quizConfiguration = {

        learner_name: session.learnerName,

        topic_ids: topicIds,

        question_count: session.questionCount,

        time_limit_seconds: session.timeLimitSeconds,

        initial_difficulty: 2

    };

    window.quizforgeConfig = quizConfiguration;

    window.dispatchEvent(
        new CustomEvent("quizforge:start", {
            detail: quizConfiguration
        })
    );

    /*
       Future integration point.
       The approved Python QuizService will own the
       actual question retrieval and attempt lifecycle.
    */

    if (
        window.quizBridge &&
        typeof window.quizBridge.submitSetup === "function"
    ) {

        window.quizBridge.submitSetup(
            JSON.stringify(quizConfiguration)
        );

    }

    // Enter quiz mode.
    document.body.classList.add("quiz-active");

    // Build the quiz interface inside the existing HTML stage.
    const stageReady = renderQuizStage();

    if (!stageReady) {

        document.body.classList.remove("quiz-active");

        quizStatus = "SETUP";

        showError("The quiz interface could not be displayed.");

        return;
    }

    // Display the first question.
    showCurrentQuestion();

    // Start countdown.
    startTimer();

    // Move directly to the quiz at the top of the window.
    requestAnimationFrame(() => {

        window.scrollTo({
            top: 0,
            left: 0,
            behavior: "instant"
        });

    });

}


/* ================= QUIZ STAGE ================= */

function renderQuizStage() {

    // Use the existing quiz-stage from HTML.
    // Never create a second element with the same ID.

    const stage = document.getElementById("quiz-stage");

    if (!stage) {
        console.error("Quiz stage element was not found in HTML.");
        return false;
    }

    // Make sure the quiz section is visible.
    if (quizSection) {

        quizSection.style.display = "block";
        quizSection.style.visibility = "visible";

    }

    // Reveal the existing quiz stage.
    stage.hidden = false;
    stage.removeAttribute("hidden");

    stage.classList.remove("quiz-hidden");

    stage.style.display = "block";
    stage.style.visibility = "visible";
    stage.style.opacity = "1";

    stage.innerHTML = `

        <div class="quiz-topbar">

            <div>
                <span class="section-tag">YOUR QUIZ SESSION</span>
                <h2>Stay focused. You've got this.</h2>
            </div>

            <button id="abandon-quiz" class="abandon-button">
                Exit Quiz
            </button>

        </div>


        <div class="quiz-progress-card">

            <div class="quiz-progress-info">

                <span id="question-progress">
                    Question 1 of ${quizQuestions.length}
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

                <span id="question-topic">TOPIC</span>

                <div id="timer-display" class="timer-display">
                    Unlimited
                </div>

            </div>

            <h3 id="question-text"></h3>

            <div id="answer-options" class="answer-options"></div>

            <div id="feedback-panel" class="feedback-panel"></div>

            <div class="quiz-actions">

                <button id="submit-answer" class="quiz-action-button">
                    Submit Answer →
                </button>

                <button id="next-question" class="quiz-action-button">
                    Next Question →
                </button>

            </div>

        </div>

        <p class="quiz-footer-note">
            Take your time and choose the best answer.
        </p>

    `;

    const abandonButton = document.getElementById("abandon-quiz");
    const submitButton = document.getElementById("submit-answer");
    const nextButton = document.getElementById("next-question");

    if (!abandonButton || !submitButton || !nextButton) {

        console.error("One or more quiz controls could not be created.");

        return false;
    }

    abandonButton.addEventListener("click", abandonQuiz);
    submitButton.addEventListener("click", submitAnswer);
    nextButton.addEventListener("click", nextQuestion);

    return true;

}


/* ================= DISPLAY QUESTION ================= */

function showCurrentQuestion() {

    const question = quizQuestions[currentQuestionIndex];

    if (!question) {
        finishQuiz("COMPLETED");
        return;
    }

    const progressText = document.getElementById("question-progress");
    const topicElement = document.getElementById("question-topic");
    const questionText = document.getElementById("question-text");
    const difficultyBadge = document.getElementById("difficulty-badge");
    const progressFill = document.getElementById("quiz-progress-fill");
    const optionsContainer = document.getElementById("answer-options");
    const feedback = document.getElementById("feedback-panel");
    const submitButton = document.getElementById("submit-answer");
    const nextButton = document.getElementById("next-question");

    if (
        !progressText ||
        !topicElement ||
        !questionText ||
        !difficultyBadge ||
        !progressFill ||
        !optionsContainer ||
        !feedback ||
        !submitButton ||
        !nextButton
    ) {

        console.error("Quiz elements are missing from the page.");
        return;
    }

    selectedAnswer = null;

    progressText.textContent =
        `Question ${currentQuestionIndex + 1} of ${quizQuestions.length}`;

    topicElement.textContent =
        getTopicName(question.topic_id).toUpperCase();

    questionText.textContent = question.question || "Question text unavailable.";

    difficultyBadge.textContent = "Medium Difficulty";

    const progress =
        (currentQuestionIndex / quizQuestions.length) * 100;

    progressFill.style.width = `${progress}%`;

    optionsContainer.innerHTML = "";

    // Support the object structure used by the mock question data.
    if (
        !question.options ||
        typeof question.options !== "object"
    ) {

        questionText.textContent =
            "This question does not have valid answer options.";

        console.error("Invalid question options:", question);

        return;
    }

    Object.entries(question.options).forEach(([key, value]) => {

        const button = document.createElement("button");

        button.type = "button";
        button.className = "answer-option";
        button.dataset.answer = key;

        button.innerHTML = `
            <span class="option-letter">${escapeHTML(key)}</span>
            <span class="option-text">${escapeHTML(value)}</span>
        `;

        button.addEventListener("click", () => {
            selectAnswer(key, button);
        });

        optionsContainer.appendChild(button);

    });

    feedback.innerHTML = "";
    feedback.className = "feedback-panel";

    submitButton.style.display = "flex";
    submitButton.disabled = true;

    nextButton.style.display = "none";

    updateTimerDisplay();

    // Animate the new question.
    const card = document.querySelector(".quiz-main-card");

    if (card) {

        card.style.animation = "none";

        void card.offsetWidth;

        card.style.animation = "quizEnter .4s ease both";

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

    if (submittedAnswers.some(
        item => String(item.question_id) ===
        String(quizQuestions[currentQuestionIndex].id)
    )) {
        return;
    }

    selectedAnswer = answer;

    document.querySelectorAll(".answer-option").forEach(option => {
        option.classList.remove("selected");
    });

    button.classList.add("selected");

    const submitButton = document.getElementById("submit-answer");

    if (submitButton) {
        submitButton.disabled = false;
    }

}


/* ================= SUBMIT ANSWER ================= */

function submitAnswer() {

    if (quizStatus !== "ACTIVE" || !selectedAnswer) {
        return;
    }

    const question = quizQuestions[currentQuestionIndex];

    if (!question) return;

    const isCorrect =
        selectedAnswer === question.correct_answer;

    submittedAnswers.push({

        question_id: question.id,

        selected_answer: selectedAnswer,

        correct_answer: question.correct_answer,

        is_correct: isCorrect

    });

    const options = document.querySelectorAll(".answer-option");

    options.forEach(option => {

        option.disabled = true;

        if (option.dataset.answer === question.correct_answer) {
            option.classList.add("correct");
        }

        if (
            option.dataset.answer === selectedAnswer &&
            !isCorrect
        ) {
            option.classList.add("incorrect");
        }

    });

    showFeedback(isCorrect, question.explanation);

    const submitButton = document.getElementById("submit-answer");
    const nextButton = document.getElementById("next-question");

    if (submitButton) {
        submitButton.style.display = "none";
    }

    if (nextButton) {

        nextButton.style.display = "flex";

        nextButton.textContent =
            currentQuestionIndex === quizQuestions.length - 1
                ? "Finish Quiz ✓"
                : "Next Question →";

    }

    updateProgress();

    /*
       M3 Adaptive Engine integration point.
       M2 does not implement the adaptive algorithm.
    */

    window.dispatchEvent(
        new CustomEvent("quizforge:answer", {
            detail: {
                question_id: question.id,
                selected_answer: selectedAnswer,
                is_correct: isCorrect
            }
        })
    );

}


/* ================= FEEDBACK ================= */

function showFeedback(isCorrect, explanation) {

    const panel = document.getElementById("feedback-panel");

    if (!panel) return;

    panel.className = isCorrect
        ? "feedback-panel correct-feedback visible"
        : "feedback-panel incorrect-feedback visible";

    panel.innerHTML = `

        <div class="feedback-heading">

            <span>${isCorrect ? "✓" : "✕"}</span>

            <strong>
                ${isCorrect ? "Correct Answer!" : "Not Quite!"}
            </strong>

        </div>

        <p>${escapeHTML(explanation || "No explanation is available.")}</p>

    `;

}


/* ================= PROGRESS ================= */

function updateProgress() {

    const progressFill = document.getElementById("quiz-progress-fill");

    if (!progressFill) return;

    const progress =
        ((currentQuestionIndex + 1) / quizQuestions.length) * 100;

    progressFill.style.width = `${progress}%`;

}


/* ================= NEXT QUESTION ================= */

function nextQuestion() {

    if (quizStatus !== "ACTIVE") return;

    // Do not move forward before submitting the current answer.
    const currentQuestion = quizQuestions[currentQuestionIndex];

    const currentWasSubmitted = submittedAnswers.some(
        answer => String(answer.question_id) ===
        String(currentQuestion.id)
    );

    if (!currentWasSubmitted) {
        return;
    }

    currentQuestionIndex++;

    if (currentQuestionIndex >= quizQuestions.length) {

        finishQuiz("COMPLETED");

        return;
    }

    showCurrentQuestion();

}


/* ================= TIMER ================= */

function startTimer() {

    stopTimer();

    updateTimerDisplay();

    if (remainingSeconds <= 0) {
        return;
    }

    timerInterval = setInterval(() => {

        if (quizStatus !== "ACTIVE") {

            stopTimer();

            return;
        }

        remainingSeconds--;

        updateTimerDisplay();

        if (remainingSeconds <= 0) {

            stopTimer();

            finishQuiz("TIMED_OUT");

        }

    }, 1000);

}


function stopTimer() {

    if (timerInterval !== null) {

        clearInterval(timerInterval);

        timerInterval = null;

    }

}


function updateTimerDisplay() {

    const display = document.getElementById("timer-display");

    if (!display) return;

    if (session.timeLimitSeconds === 0) {

        display.textContent = "Unlimited";

        display.className = "timer-display";

        return;
    }

    const minutes = Math.floor(remainingSeconds / 60);

    const seconds = remainingSeconds % 60;

    display.textContent =
        `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

    display.className = "timer-display";

    if (remainingSeconds <= 10) {

        display.classList.add("timer-danger");

    } else if (remainingSeconds <= 60) {

        display.classList.add("timer-warning");

    }

}


/* ================= ABANDON QUIZ ================= */

function abandonQuiz() {

    if (quizStatus !== "ACTIVE") return;

    const confirmed = window.confirm(
        "Are you sure you want to exit this quiz?\nYour current attempt will be abandoned."
    );

    if (!confirmed) {
        return;
    }

    finishQuiz("ABANDONED");

}


/* ================= FINISH QUIZ ================= */

function finishQuiz(status) {

    if (quizStatus === "FINISHED") return;

    quizStatus = "FINISHED";

    stopTimer();

    const totalQuestions = quizQuestions.length;

    const correctAnswers = submittedAnswers.filter(
        answer => answer.is_correct
    ).length;

    const answeredQuestions = submittedAnswers.length;

    const unansweredQuestions =
        totalQuestions - answeredQuestions;

    const stage = document.getElementById("quiz-stage");

    if (!stage) {
        console.error("Quiz stage was not found.");
        return;
    }

    const statusText = {

        COMPLETED: "Quiz Completed",

        TIMED_OUT: "Time's Up!",

        ABANDONED: "Quiz Abandoned"

    };

    const statusDescription = {

        COMPLETED: "You have completed your quiz session.",

        TIMED_OUT: "Your time limit has ended.",

        ABANDONED: "You exited the quiz before completing it."

    };

    stage.innerHTML = `

        <div class="finished-card">

            <div class="finished-icon">
                ${status === "COMPLETED" ? "✓" : "◷"}
            </div>

            <span class="section-tag">SESSION SUMMARY</span>

            <h2>${statusText[status]}</h2>

            <p>${statusDescription[status]}</p>

            <div class="finished-stats">

                <div>
                    <strong>${totalQuestions}</strong>
                    <span>Total Questions</span>
                </div>

                <div>
                    <strong>${answeredQuestions}</strong>
                    <span>Answered</span>
                </div>

                <div>
                    <strong>${correctAnswers}</strong>
                    <span>Correct</span>
                </div>

                <div>
                    <strong>${unansweredQuestions}</strong>
                    <span>Unanswered</span>
                </div>

            </div>

            <div class="finished-note">
                Demo summary only. Final scoring and result persistence
                will be handled by the approved team services.
            </div>

            <button id="return-to-setup" class="quiz-action-button">
                Back to Setup ↗
            </button>

        </div>

    `;

    window.dispatchEvent(
        new CustomEvent("quizforge:finish", {
            detail: {
                status,
                total_questions: totalQuestions,
                answered_questions: answeredQuestions,
                correct_answers: correctAnswers,
                unanswered_questions: unansweredQuestions
            }
        })
    );

    const returnButton = document.getElementById("return-to-setup");

    if (returnButton) {
        returnButton.addEventListener("click", returnToSetup);
    }

}


/* ================= RETURN TO SETUP ================= */

function returnToSetup() {

    stopTimer();

    quizStatus = "SETUP";

    currentQuestionIndex = 0;
    selectedAnswer = null;
    submittedAnswers = [];
    quizQuestions = [];

    const stage = document.getElementById("quiz-stage");

    if (stage) {

        stage.innerHTML = "";

        stage.hidden = true;

        stage.style.display = "";
        stage.style.visibility = "";
        stage.style.opacity = "";

    }

    // Restore the full website.
    document.body.classList.remove("quiz-active");

    if (quizSection) {

        quizSection.style.display = "";
        quizSection.style.visibility = "";

    }

    // Return to the setup section.
    requestAnimationFrame(() => {

        if (quizSection) {

            quizSection.scrollIntoView({
                behavior: "smooth",
                block: "start"
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

const revealElements = document.querySelectorAll(".reveal");

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

function initializeQuizForge() {

    initializeMockData();

    updateSummary();

}


initializeQuizForge();
