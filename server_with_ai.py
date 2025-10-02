# server_with_ai_process.py
import os
import subprocess
from flask import Flask

app = Flask(__name__)

# -----------------------------
# Start ai.py in a separate process
# -----------------------------
ai_process = subprocess.Popen(
    ["python", "ai.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT
)

# -----------------------------
# Health endpoint for Render
# -----------------------------
@app.route("/")
def index():
    return "Hello from Render! AI is running in a separate process."

@app.route("/_health")
def health():
    return "OK", 200

# -----------------------------
# Run Flask
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)