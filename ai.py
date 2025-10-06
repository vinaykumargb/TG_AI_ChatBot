import os
import requests
import aiohttp
import re
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from webContent import get_readable_content

def get_webContent(text: str) -> str:
    """
    Finds all website links in text, replaces them
    with their readable web content.
    """

    def replace_link(match):
        url = match.group()
        content = get_readable_content(url)
        # If fetching fails, keep the original link
        if content.startswith("Failed to fetch"):
            return url
        return content

    return re.sub(r'https?://\S+', replace_link, text)

# -------------------------------
# 1️⃣ Configure keys
# -------------------------------
TELEGRAM_TOKEN = os.getenv("AITOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"

# -------------------------------
# 2️⃣ Memory & Gemini call
# -------------------------------
MAX_MEMORY = 5
user_memory = {}

def get_thread_chat_key(message):
    """
    Returns a unique key for memory storage:
    - Forum thread: "chatid:threadid"
    - Private/group chat: chat.id
    """
    if getattr(message, "message_thread_id", None):
        return f"{message.chat.id}:{message.message_thread_id}"
    return str(message.chat.id)

async def ask_gemini(thread_key: str, user_text: str) -> str:
    if thread_key not in user_memory:
        user_memory[thread_key] = []

    # Add user message
    user_memory[thread_key].append({"role": "user", "content": get_webContent(user_text)})
    # Keep last MAX_MEMORY messages
    user_memory[thread_key] = user_memory[thread_key][-MAX_MEMORY:]

    # Prepare payload
    contents = [{"parts": [{"text": f"[Please keep responses under 4000 characters, and provide 1 empty newline space between statements/bullet points; don't forget to give hyphen to each points. You should keep the responses professional and upsc cse relavant. Your prompt with website link will be replaced by that website content, so answer user questions regarding this accordingly.]\n{msg['role'].title()}: {msg['content']}"}]} 
                for msg in user_memory[thread_key]]
    payload = {"contents": contents}

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GEMINI_URL, headers=headers, json=payload, timeout=60) as resp:
                if resp.status != 200:
                    return f"Error {resp.status}: {await resp.text()}"
                data = await resp.json()
                reply_text = data["candidates"][0]["content"]["parts"][0]["text"][:4096]

                # Add assistant reply to memory
                user_memory[thread_key].append({"role": "assistant", "content": reply_text})

                return reply_text
    except Exception as e:
        return f"Error: {e}"

# -------------------------------
# 3️⃣ Markdown to HTML
# -------------------------------
def markdown_to_html(text: str) -> str:
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Hyphen bullets
    text = re.sub(r"(?<=\n)\*(?=\s)", "-", text)
    text = re.sub(r"(?<=\s)\*(?=\s)", "-", text)
    # Italic
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)
    # Inline code
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    # Horizontal rule
    text = re.sub(r"^\s*---\s*$", r"<hr>", text, flags=re.MULTILINE)
    return text

# -------------------------------
# 4️⃣ Handlers
# -------------------------------
# -------------------------------
# 4️⃣ Handle user messages
# -------------------------------
# Map allowed chats and thread IDs (None for normal chat)
ALLOWED_CHATS = {
    -1003069777509: 2,       # forum group thread ID 2
    -1003018799293: 308 #CSQ
}

def is_allowed(message):
    chat_id = message.chat.id
    thread_id = getattr(message, "message_thread_id", None)

    if chat_id not in ALLOWED:
        return False

    # If a thread restriction exists, check it
    if ALLOWED[chat_id] is not None and thread_id != ALLOWED[chat_id]:
        return False

    return True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    user_text = update.message.text
    topic_id = update.message.message_thread_id
    
    if topic_id not in [308, 2]:
        return  # ignore other chats
    
    thread_id = ALLOWED_CHATS[chat_id]  # None if normal chat
    
    # Send "Thinking..." placeholder in the correct thread
    placeholder = await context.bot.send_message(
        chat_id=chat_id,
        text="🤔 Thinking... please wait...",
        message_thread_id=thread_id
    )

    # Get AI reply
    reply = await ask_gemini(chat_id, user_text)
    html_reply = markdown_to_html(reply)

    # Delete placeholder
    await placeholder.delete()

    # Send AI reply in the same chat/thread
    await context.bot.send_message(
        chat_id=chat_id,
        text=html_reply,
        parse_mode=ParseMode.HTML,
        message_thread_id=thread_id
    )


# -------------------------------
# 3️⃣ Start command
# -------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message else None  
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🤖 Hello! I'm your **UPSC CSE Assistant Bot**.\n\n"
            "📌 Use this thread for:\n"
            "• Summaries of news articles (just paste the link)\n"
            "• Quick explanations of GS topics (Polity, Economy, Environment, S&T, History, etc.)\n"
            "• Prelims-style MCQs and practice\n"
            "• Strategy tips for Prelims & Mains\n\n"
            "⚡ Think of me as your AI study companion — keeping everything focused on the **UPSC Civil Services Exam**."
        ),
        parse_mode="Markdown",
        message_thread_id=thread_id
    )

def main():
    import time
    while True:
        try:
            app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            print("✅ Gemini AI Telegram Bot is running...")
            app.run_polling(close_loop=False)

        except Exception as e:
            # Detect Telegram getUpdates Conflict
            if "terminated by other getUpdates request" in str(e):
                print("⚠️ Conflict detected: Another bot instance is running. Retrying in 5s...")
            else:
                print(f"Bot crashed: {e}, retrying in 5s...")
            time.sleep(5)


from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True  # Allow immediate rebinding of port

def start_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")

        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

        def do_POST(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")

    port = int(os.environ.get("PORT", 10000))
    server = ReusableHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

def console_listener():
    while True:
        cmd = input()
        if cmd.strip().lower() == "end":
            print("⚡ 'end' command received. Shutting down bot...")
            os._exit(0)

if __name__ == "__main__":
    # Start the dummy server
    start_dummy_server()

    # Start console listener thread
    threading.Thread(target=console_listener, daemon=True).start()

    # Start the bot
    main()