# Project Pitch: VERDICT

## Inspiration
We live in an age of "chatbots" that are polite, agreeable, and often hallucinatory. But when it comes to high-stakes decisions—business strategy, crisis management, or financial planning—we don't need a chat partner; we need a rigorous judge. We built **VERDICT** to move beyond conversational AI into **Deterministic Decision Intelligence**, creating a system that doesn't just "talk" but actively debates, fact-checks, and issues a binding verdict.

## What it does
VERDICT is a deterministic decision engine that transforms natural language inputs into binding outcomes (APPROVED, CAUTION, BLOCKED).
1.  **Gatekeeper**: Parses unstructured user input into a strict JSON object.
2.  **Bias Detection**: Rejects inputs that are emotionally charged or irrational.
3.  **Adversarial Council**: Runs a simultaneous debate between 4 specialized AI agents (Reality, Risk, ROI, Opportunity).
4.  **Deterministic Core**: A non-AI logic gate calculates the final verdict mathematically based on agent scores.
5.  **Strategic Optimizer**: If a decision is blocked, it generates a concrete "Repair Plan" to fix the specific flaws.

## How we built it
We built the backend using **Python 3.12** and **FastAPI** for high-performance, stateless processing. The frontend is a lightweight, framework-free **Vanilla JS** application designed for speed and visual impact. The core intelligence is powered by **Google Gemini 3 Flash**, selected for its reasoning speed and large context window which allows us to load complex system instructions for each agent.

## Challenges
Our biggest challenge was the **Gemini API Rate Limits**. Initially, running 4 separate AI agents (Green, Red, Blue, Yellow) plus a Gatekeeper and Optimizer triggered "429 Too Many Requests" errors constantly.
We solved this by **batching the Sensor Council**: instead of 4 sequential or parallel API calls, we engineered a single, complex "Council Prompt" that forces Gemini to assume all 4 personas simultaneously and output a single structured JSON containing the analysis for all agents. This cut our API usage by 75% and reduced latency from 12s to under 3s, effectively solving the N+1 problem in LLM orchestration.

## Accomplishments
We are proud of creating a **Deterministic AI System**. Most AI apps are probabilistic and fuzzy. VERDICT is precise. It uses AI for reasoning but standard logic for the final decision, ensuring that if a decision violates physics (Green Agent) or is catastrophic (Red Agent), it is *always* blocked, regardless of how persuasive the text generation is.

## What we learned
We learned that **Prompt Engineering is Architecture**. By structuring our prompts to output strict JSON schemas, we could treat LLMs as reliable functional components rather than unpredictable text generators. We also learned that "less is more"—stripping away the "chat" interface focused the user entirely on the decision logic.

## What's next
Next, we plan to implement **Scenario Simulation**, allowing users to tweak variables (e.g., "What if cost checks were 10% looser?") and see how the verdict changes in real-time. We also aim to add **collaborative decision-making**, where teams can vote on the specific constraints before the AI renders its judgment.
