# VERDICT

**Deterministic Intelligence Engine powered by Gemini 3.**

VERDICT is a rigorous decision-making system that uses adversarial AI agents to analyze inputs against strict reality constraints. Unlike standard chatbots, VERDICT provides a binding decision: **APPROVED**, **CAUTION**, or **BLOCKED**.

![Decision Authority Architecture](<img width="5441" height="6230" alt="architecture_diagram" src="https://github.com/user-attachments/assets/0aab56b4-e172-4cd5-90c9-f0b15f94c68e" />
)

---

## 🚀 Features

- **Adversarial Architecture**: Decisions are debated by 4 distinct AI agents:
  - 🟢 **Green (Reality)**: Checks physical/financial constraints.
  - 🔴 **Red (Risk)**: Detects failure modes and self-deception.
  - 🔵 **Blue (Logic)**: Calculates ROI and long-term value.
  - 🟡 **Yellow (Opportunity)**: Identifies strategic upside.
- **Deterministic Core**: Inputs are processed through a strict logic gate, not a probabilistic LLM chat.
- **Bias Detection**: Real-time analysis of emotional language to prevent clouded judgment.
- **Security Hardened**: 
  - Rate limiting (Anti-abuse)
  - Input Sanitization (Injection prevention)
  - Production-ready error handling

---

## 🧠 Gemini 3 Integration

Gemini 3 is used as the core reasoning engine to analyze decisions, detect bias, and explain outcomes in real time. It powers:

1.  **Gatekeeper**: Extracting structured constraints from natural language.
2.  **Sensors**: Running parallel adversarial simulations for risk/reward.
3.  **Optimizer**: Suggesting concrete improvements for blocked decisions.

---

## ⚙️ How it Works (The Pipeline)

Every user request goes through a rigorous, multi-stage deterministic pipeline:

1.  **Input Gatekeeper**: First, we use Gemini 3 to parse the user's natural language into a structured JSON `decision_object`. If key details are missing, it strictly rejects the input.
2.  **Emotional Bias Detector**: We analyze the input for emotional charging. If the user is too emotional (e.g., angry, desperate), the system forces a cooling-off period or rejects the request.
3.  **The Sensor Council**: Four parallel AI agents analyze the structured data:
    - *Green Agent*: Validates capabilities.
    - *Red Agent*: Hunts for risks.
    - *Blue Agent*: Calculates logic/ROI.
    - *Yellow Agent*: Look for opportunities.
4.  **Deterministic Core**: The outputs are fed into a **non-AI logic gate**. The final verdict (APPROVED/BLOCKED) is calculated mathematically based on the agents' scores, not by an LLM writing text.
5.  **Strategic Optimizer**: If a decision is blocked, a separate Gemini 3 agent analyzes *why* and generates specific, actionable steps to turn that "No" into a "Yes".

---

## 💻 Tech Stack

-   **Backend**: Python 3.12+, FastAPI, Uvicorn
-   **AI Engine**: Google Gemini 3.5 (via `google-generativeai`)
-   **Frontend**: Vanilla JavaScript (ES6+), CSS3 Variables (No frameworks), HTML5
-   **Architecture**: Stateless REST API with Event-Driven AI Agents

---

## 🛠️ Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API Key
# Copy .env.example to .env and add your key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_actual_key
```

## ▶️ Running

```bash
python backend/main.py
```

Server runs at http://localhost:8000

---

## 🛡️ License

MIT License - see [LICENSE](LICENSE) file for details.
