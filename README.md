# WhatsApp AI — Full-Stack Conversational Assistant

A complete, production-grade conversational system featuring a **modern WhatsApp Web React frontend** connected to a resilient **FastAPI backend** powered by **Google GenAI SDK (`google.genai`)**, **Gemini 2.5 Flash**, **SQLite persistent multi-turn memory**, and **Meta WhatsApp Cloud API** (with fallback support for Twilio, Green-API, and offline mock modes).

---

## 🏗️ Architecture & Technical Stack

```
                              +------------------------------------+
                              |  Meta WhatsApp Cloud API / Twilio  |
                              +-----------------+------------------+
                                                | Webhook HTTP POST
                                                v
+------------------------+             +-------------------------------------------------------+
|  React 19 + Vite Web   |   HTTP      |  FastAPI Backend Microservice (Uvicorn)               |
|  Frontend Application  |<----------->|                                                       |
|  (WhatsApp Web UI)     |             |  1. Inbound Webhooks & Direct Chat Endpoints          |
|                        |             |     • GET /webhook (Meta handshake verification)      |
|  • Left Sidebar        |             |     • POST /webhook (Meta webhook message intake)     |
|    - Search & Filter   |             |     • GET /conversations (distinct contacts & preview)|
|    - Contacts & Badges |             |     • POST /chat (Direct web turn & AI generation)    |
|    - New Chat Modal    |             |     • GET /history/{sender_id} (turns in order)       |
|    - Diagnostics Panel |             |     • POST /history/{sender_id}/clear (clear history) |
|  • Main Chat Panel     |             |     • GET /health (telemetry & metrics)               |
|    - WhatsApp Bubbles  |             |                                                       |
|    - Blue Read Checks  |             |  2. Async Queue & Multi-Worker Pipeline               |
|    - Typing Indicator  |             |     • asyncio.Queue with backpressure control         |
|    - Auto-scroll       |             |     • Per-user FIFO locks (asyncio.Lock)              |
|    - Dark Mode Toggle  |             |     • Deduplication by Message ID (wamid)             |
|  • Message Composer    |             |                                                       |
|    - Multiline Textarea|             |  3. Google GenAI Agent Core (`agent.py`)              |
|    - Quick Suggestions |             |     • Gemini 2.5 Flash model via google.genai         |
|    - Emoji Bar         |             |     • General-Purpose Q&A (Math, Coding, Science,     |
|    - Keyboard shortcuts|             |       History, Translation to Kannada, etc.)         |
|                        |             |     • Automatic Function Calling (AFC) for tools      |
|                        |             |                                                       |
|                        |             |  4. State & Memory Store (`memory.py`)                |
|                        |             |     • SQLite database in WAL mode                     |
|                        |             |     • Sliding dialog context window (20 turns)        |
+------------------------+             +-------------------------------------------------------+
```

---

## 💻 Tech Stack Summary

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite 8, JavaScript (ES Modules), HTML5, Responsive CSS |
| **Icons** | Lucide React |
| **HTTP Communication** | Resilient Fetch API client with timeouts & error handling |
| **Backend** | Python 3.10+ / 3.14, FastAPI, Starlette CORS Middleware, Uvicorn |
| **AI Agent** | Google GenAI SDK (`google.genai`), Gemini 2.5 Flash (`gemini-2.5-flash`) |
| **Storage & Memory** | SQLite with Write-Ahead Logging (WAL) and FIFO turn order |
| **Messaging Client** | Meta WhatsApp Cloud API (Graph API v21.0), Twilio, Green-API, Mock |

---

## ⚡ Exact Windows CMD Commands to Run Both Applications

Open two separate Command Prompt (`cmd.exe`) windows on your Windows laptop.

### Terminal 1: Run the FastAPI Backend

```cmd
cd "c:\Users\vishw\Downloads\cousin chatbot"
python main.py
```
> **Backend URL**: `http://127.0.0.1:8000`  
> **Interactive API Docs (Swagger)**: `http://127.0.0.1:8000/docs`

*(Optional: If you use a virtual environment, activate it with `call .venv\Scripts\activate.bat` before running `python main.py`).*

### Terminal 2: Run the Vite Web Frontend

```cmd
cd "c:\Users\vishw\Downloads\cousin chatbot\frontend"
npm run dev
```
> **Frontend URL**: `http://localhost:5173`

---

## 🔑 Environment Variables & Configuration

### Backend Configuration (`.env`)

Located in the project root (`c:\Users\vishw\Downloads\cousin chatbot\.env`). Copy from `.env.example`:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `HOST` | Backend server listen address | `0.0.0.0` |
| `PORT` | Backend server port | `8000` |
| `GEMINI_API_KEY` | Official Google Gemini API key (or `ANTIGRAVITY_API_KEY`) | `your_gemini_api_key_here` |
| `AGENT_MODEL` | AI Model name (e.g. `gemini-2.5-flash`, `gemini-2.0-flash`) | `gemini-2.5-flash` |
| `AGENT_TEMPERATURE` | Agent creativity parameter | `0.7` |
| `MESSAGING_PROVIDER` | Messaging backend (`whatsapp`, `twilio`, `green_api`, `mock`) | `whatsapp` |
| `WHATSAPP_TOKEN` | Meta WhatsApp Cloud API Permanent System User Token | `your_token_here` |
| `PHONE_NUMBER_ID` | Meta WhatsApp Business Phone Number ID | `your_phone_number_id` |
| `VERIFY_TOKEN` | Webhook verification handshake token | `my_whatsapp_webhook_secret_token_123` |
| `APP_SECRET` | Meta App Secret for HMAC SHA-256 header validation | `your_meta_app_secret` |
| `DB_PATH` | Path to persistent SQLite conversation database | `data/conversations.db` |
| `MAX_HISTORY_TURNS` | Max turns kept in LLM context prompt | `20` |

### Frontend Configuration (`frontend/.env`)

Located in `frontend/.env`. Copy from `frontend/.env.example`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base HTTP URL pointing to the FastAPI backend | `http://127.0.0.1:8000` |

*Note: The frontend also allows changing or testing the backend API URL dynamically at runtime inside the **Settings & Diagnostics** panel.*

---

## 🎨 WhatsApp Web Frontend Features

### 1. Left Sidebar
- **Brand Header**: WhatsApp AI badge with live backend connectivity status pill.
- **Search Bar**: Instant filter for contacts by phone number or last message preview.
- **Filter Tabs**: Filter by **All**, **Unread**, and **Favorites**.
- **Conversation List**: Avatars with initials and colors generated from sender IDs, timestamps, read checkmarks, and turn badges.
- **New Chat Modal**: Instant start conversation with any recipient phone number or quick demo numbers.
- **Dark Mode Toggle**: Clean switcher between WhatsApp Light mode (`#efeae2`) and WhatsApp Dark mode (`#0b141a`).
- **Settings & Diagnostics**: Inspect AI model, active provider, total SQLite messages, active workers, and credential health (no secrets exposed).

### 2. Main Chat Panel
- **Chat Header**: Contact avatar, name/number, online status ("online • Gemini 2.5 Flash"), favorite star toggle, and clear chat option.
- **Message Area**:
  - Classic WhatsApp subtle doodle background pattern in light and dark mode.
  - Date dividers ("TODAY", "YESTERDAY", formatted date).
  - Outgoing bubbles on the right (WhatsApp green `#d9fdd3` / `#005c4b`) with double blue read checkmarks (`✓✓`).
  - Incoming bubbles on the left (white `#ffffff` / dark `#202c33`) with AI Assistant avatar tag.
  - Full WhatsApp markdown formatting: `*bold*`, `_italics_`, `~strike~`, and `` `code` `` blocks.
  - Copy-to-clipboard on hover for every bubble.
  - Animated WhatsApp typing indicator (3 bouncing dots) while the AI generates its response.
  - Auto-scroll to the latest message with a floating jump-to-bottom button when scrolled up.
  - Welcome screen when no chat is selected.

### 3. Message Composer
- **Multiline Input**: Auto-resizing textarea supporting multiline messages.
- **Keyboard Shortcuts**: `Enter` to send, `Shift+Enter` for a new line.
- **Emoji Bar**: Quick insertion popover for frequently used emojis (`🌤️`, `💡`, `📊`, `✅`, `👋`).
- **Safety**: Send button disabled when empty or while AI response is generating.
- **Network Resilience**: Shows connection warning strip with one-click reconnect if backend is temporarily unreachable.

---

## 🤖 General-Purpose AI Agent & Tools

The AI Assistant is configured to handle broad, general-purpose questions directly via Gemini without artificial topic limitations:
- **Programming & Web Dev**: Python, JavaScript, Java, SQL, functions, debugging, syntax.
- **Mathematics & Science**: Arithmetic (e.g. $25 \times 48 = 1200$), algebra, physics, engineering.
- **General Knowledge & History**: Historical figures (e.g. First Prime Minister of India — Jawaharlal Nehru), geography, world affairs.
- **Languages & Translation**: Accurate translation into Indian and global languages, including Kannada (e.g. "ನೀವು ಹೇಗಿದ್ದೀರಿ?").
- **Multi-turn Memory Recall**: Follow-up questions (e.g. "What did I ask you in my previous message?") leveraging SQLite conversation context.

Optional specialized tools are available via Gemini Automatic Function Calling (AFC):
1. **Weather Tool** (`get_current_weather`): Real-time weather lookup.
2. **Knowledge Base Tool** (`lookup_knowledge_base`): Business policy and hours.
3. **Quote Calculator** (`calculate_service_quote`): Pricing estimates.

---

## 🧪 Testing & Verification

Run the full automated test suite (38 tests covering agent capabilities, general Q&A, memory, webhooks, live API, CORS, and WhatsApp client):

```cmd
python -m pytest -v
```

Build and lint the frontend:
```cmd
cd frontend
npm run lint
npm run build
```

---

## 📍 Local URLs Quick Reference

| Service | Local URL |
| :--- | :--- |
| **WhatsApp AI Web Frontend** | `http://localhost:5173` |
| **FastAPI Backend Service** | `http://127.0.0.1:8000` |
| **FastAPI Interactive Docs (Swagger)** | `http://127.0.0.1:8000/docs` |
| **Health Telemetry Endpoint** | `http://127.0.0.1:8000/health` |
| **Conversations API** | `http://127.0.0.1:8000/conversations` |
"# chatbot" 
