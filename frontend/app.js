// ═══════════════════════════════════════════════════════════════════
// VERDICT - FRONTEND v2
// ═══════════════════════════════════════════════════════════════════

console.log('=== VERDICT Loading ===');

const CONFIG = {
    API_BASE: 'http://localhost:8000',
    TYPING_SPEED: 25,
    ADVISOR_GAP: 500
};

const VOICE_PROFILES = {
    red: { rate: 0.8, pitch: 0.6, preferredVoice: ['David', 'Google UK English Male'] },
    blue: { rate: 0.95, pitch: 1.0, preferredVoice: ['Mark', 'Google US English'] },
    yellow: { rate: 1.15, pitch: 1.4, preferredVoice: ['Zira', 'Google UK English Female'] },
    green: { rate: 0.9, pitch: 0.85, preferredVoice: ['Tom', 'Alex'] }
};

const ADVISOR_ORDER = ['red', 'blue', 'yellow', 'green'];
let isProcessing = false;
let synth = window.speechSynthesis;
let voices = [];
let advisorVoices = {};

// DOM Elements
const $ = id => document.getElementById(id);
const delay = ms => new Promise(r => setTimeout(r, ms));

// Load voices
function loadVoices() {
    voices = synth ? synth.getVoices().filter(v => v.lang.startsWith('en')) : [];

    ADVISOR_ORDER.forEach((id, i) => {
        const profile = VOICE_PROFILES[id];
        let voice = voices.find(v =>
            profile.preferredVoice.some(p => v.name.toLowerCase().includes(p.toLowerCase()))
        );
        advisorVoices[id] = voice || voices[i % voices.length] || null;
    });
}

if (synth) {
    loadVoices();
    synth.onvoiceschanged = loadVoices;
}

// Speech
function speak(text, advisorId) {
    return new Promise(resolve => {
        if (!synth || !text) {
            resolve();
            return;
        }

        const profile = VOICE_PROFILES[advisorId];
        const voice = advisorVoices[advisorId];
        const utterance = new SpeechSynthesisUtterance(text);

        if (voice) utterance.voice = voice;
        utterance.rate = profile.rate;
        utterance.pitch = profile.pitch;
        utterance.lang = 'en-US';

        utterance.onend = resolve;
        utterance.onerror = () => resolve();

        synth.speak(utterance);
    });
}

// Type text animation
async function typeText(el, text) {
    if (!el || !text) return;
    for (let i = 0; i <= text.length; i++) {
        el.innerHTML = text.slice(0, i) + '<span class="cursor"></span>';
        await delay(CONFIG.TYPING_SPEED);
    }
    el.innerHTML = text;
}

// Loading
let loadingInterval;
let loadingTimeout;
const LOADING_MESSAGES = [
    "Parsing decision…",
    "Evaluating constraints…",
    "Rendering verdict…"
];

function showLoading() {
    $('loading-overlay').classList.add('is-visible');

    // Reset steps
    ['step-1', 'step-2', 'step-3'].forEach(id => {
        $(id).classList.remove('is-active', 'is-complete');
        $(id).querySelector('.analysis-step__icon').textContent = '○';
    });

    // Initial message
    const msgEl = $('loading-message');
    msgEl.textContent = "Gemini 3 reasoning engine activated.";

    // Start cycling messages after 1.5s (to let the first message be read)
    let msgIndex = 0;

    if (loadingTimeout) clearTimeout(loadingTimeout);
    if (loadingInterval) clearInterval(loadingInterval);

    // Wait slightly before starting the cycle
    loadingTimeout = setTimeout(() => {
        loadingInterval = setInterval(() => {
            if (msgEl) {
                msgEl.textContent = LOADING_MESSAGES[msgIndex];
                msgIndex = (msgIndex + 1) % LOADING_MESSAGES.length;
            }
        }, 1000);
    }, 1500);

    animateSteps();
}

async function animateSteps() {
    for (const id of ['step-1', 'step-2', 'step-3']) {
        const step = $(id);
        step.classList.add('is-active');
        step.querySelector('.analysis-step__icon').textContent = '◐';
        await delay(800);
        step.classList.remove('is-active');
        step.classList.add('is-complete');
        step.querySelector('.analysis-step__icon').textContent = '●';
    }
}

function hideLoading() {
    $('loading-overlay').classList.remove('is-visible');
    if (loadingTimeout) {
        clearTimeout(loadingTimeout);
        loadingTimeout = null;
    }
    if (loadingInterval) {
        clearInterval(loadingInterval);
        loadingInterval = null;
    }
}

// Error handling
function showError(msg) {
    console.error('ERROR:', msg);
    const el = $('error-message');
    el.textContent = msg;
    el.classList.add('is-visible');
}

function hideError() {
    $('error-message').classList.remove('is-visible');
}

// API call
async function makeDecision(message) {
    const res = await fetch(`${CONFIG.API_BASE}/api/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
    });

    const data = await res.json();

    if (!res.ok) {
        throw new Error(data.error || `HTTP ${res.status}`);
    }

    return data;
}

// Animate single advisor
async function animateAdvisor(id, text) {
    const card = $(`advisor-${id}`);
    const textEl = $(`advisor-${id}-text`);

    if (!card || !textEl) {
        console.error(`Elements not found for ${id}`);
        return;
    }

    card.classList.add('is-visible');
    await delay(400);
    card.classList.add('is-speaking');

    await Promise.all([
        typeText(textEl, text),
        speak(text, id)
    ]);

    card.classList.remove('is-speaking');
}

// Animate all advisors
async function runAdvisors(sensors) {
    if (!sensors) {
        console.error('No sensors data!');
        throw new Error('No sensor data received');
    }

    for (const id of ADVISOR_ORDER) {
        const sensorData = sensors[id];
        if (!sensorData) {
            continue;
        }
        const text = sensorData.sentence || 'No analysis available';
        await animateAdvisor(id, text);
        await delay(CONFIG.ADVISOR_GAP);
    }
}

// Animate score
function animateScore(type, value) {
    const ring = $(`ring-${type}`);
    const valEl = $(`score-${type}`);

    if (!ring || !valEl) return;

    setTimeout(() => {
        ring.style.strokeDashoffset = 100 - value;
    }, 100);

    let current = 0;
    const step = () => {
        current += 2;
        if (current > value) current = value;
        valEl.textContent = current + '%';
        if (current < value) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

// Show final decision
async function showFinalDecision(card) {
    await delay(600);

    const fd = $('final-decision');
    // Robustly handle verdict string (trim whitespace, ignore case)
    const rawVerdict = card.verdict || '';
    const verdict = rawVerdict.toString().trim().toUpperCase();

    // Add appropriate class based on verdict
    if (verdict === 'APPROVED') {
        fd.classList.add('approved');
        $('decision-icon').textContent = '✓';
    } else if (verdict === 'CAUTION') {
        fd.classList.add('caution');
        $('decision-icon').textContent = '⚠';
    } else {
        fd.classList.add('blocked');
        $('decision-icon').textContent = '✗';
    }

    // Display the verdict text
    $('decision-verdict').textContent = rawVerdict;

    const reason = $('decision-reason');
    if (card.blocking_reason) {
        reason.textContent = card.blocking_reason;
        reason.style.display = 'block';
    } else {
        reason.style.display = 'none';
    }

    const scores = card.scores || {};
    animateScore('constraint', scores.constraint || 0);
    animateScore('risk', scores.risk || 0);
    animateScore('roi', scores.roi || 0);
    animateScore('overall', scores.overall || 0);

    fd.classList.add('is-visible');
    await delay(400);
    $('new-analysis-btn').classList.add('is-visible');
}

// Show Strategic Optimizer
function showOptimizer(suggestions) {
    const optimizer = $('strategic-optimizer');
    const container = $('optimizer-suggestions');

    if (!optimizer || !container) {
        return;
    }
    if (!suggestions || !Array.isArray(suggestions) || suggestions.length === 0) {
        return;
    }

    // Clear previous suggestions
    container.innerHTML = '';

    // Add each suggestion
    suggestions.forEach((text, index) => {
        const suggestionEl = document.createElement('div');
        suggestionEl.className = 'optimizer-suggestion';
        suggestionEl.innerHTML = `
            <div class="suggestion-number">${index + 1}</div>
            <div class="suggestion-text">${text}</div>
        `;
        container.appendChild(suggestionEl);
    });

    // Show the optimizer card
    optimizer.classList.add('is-visible');
}

// Reset view
function resetView() {
    if (synth) synth.cancel();

    $('advisor-section').classList.remove('is-visible');
    $('final-decision').classList.remove('is-visible', 'approved', 'caution', 'blocked');
    $('new-analysis-btn').classList.remove('is-visible');
    $('strategic-optimizer').classList.remove('is-visible');
    $('optimizer-suggestions').innerHTML = '';

    ADVISOR_ORDER.forEach(id => {
        $(`advisor-${id}`).classList.remove('is-visible', 'is-speaking');
        $(`advisor-${id}-text`).innerHTML = '';
    });

    ['constraint', 'risk', 'roi', 'overall'].forEach(type => {
        $(`ring-${type}`).style.strokeDashoffset = '100';
        $(`score-${type}`).textContent = '0%';
    });

    $('input-section').classList.remove('is-hidden');
    $('decision-input').value = '';
    $('decision-input').focus();
}

// Main submit handler
async function handleSubmit() {
    if (isProcessing) {
        return;
    }

    const message = $('decision-input').value.trim();

    if (!message || message.length < 10) {
        showError('Please describe your decision (at least 10 characters).');
        return;
    }

    isProcessing = true;
    hideError();
    $('submit-btn').disabled = true;
    $('submit-btn').classList.add('is-loading');
    showLoading();

    try {
        const response = await makeDecision(message);

        hideLoading();

        if (!response.success) {
            throw new Error(response.error || 'Analysis failed');
        }

        // Hide input and show results directly
        $('input-section').classList.add('is-hidden');
        $('advisor-section').classList.add('is-visible');

        // Run advisors
        await runAdvisors(response.sensors);

        // Show final decision
        await showFinalDecision(response.decision_card);

        // Show optimizer if suggestions available
        if (response.optimizer_suggestions && response.optimizer_suggestions.length > 0) {
            await delay(500);
            showOptimizer(response.optimizer_suggestions);
        }

    } catch (error) {
        console.error('Error:', error);
        hideLoading();
        showError(error.message || 'Failed to analyze. Please try again.');
    } finally {
        isProcessing = false;
        $('submit-btn').disabled = false;
        $('submit-btn').classList.remove('is-loading');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function () {
    console.log('DOM loaded, initializing...');

    const submitBtn = $('submit-btn');
    const newBtn = $('new-analysis-btn');
    const input = $('decision-input');

    if (submitBtn) {
        submitBtn.onclick = handleSubmit;
    }

    if (newBtn) {
        newBtn.onclick = resetView;
    }

    if (input) {
        input.onkeydown = e => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') handleSubmit();
        };
        input.focus();
    }

    console.log('=== VERDICT Ready ===');
});
