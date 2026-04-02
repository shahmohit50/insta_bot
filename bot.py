import requests, json, os, subprocess

TOKEN = os.environ["BOT_TOKEN"]
BASE = f"https://api.telegram.org/bot{TOKEN}"

raw_input = os.getenv("INSTA_URL")

INSTA_URL = None

if raw_input:
    try:
        # Try parsing as JSON (Pipedream case)
        data = json.loads(raw_input)

        INSTA_URL = (
            data.get("message", {})
                .get("text")
        )
    except Exception:
        # Fallback: treat as plain URL string
        INSTA_URL = raw_input
DEFAULT_CHAT_ID = os.getenv("CHAT_ID")


def send_message(chat_id, text):
    requests.post(f"{BASE}/sendMessage", data={
        "chat_id": chat_id,
        "text": text
    })


def send_video(chat_id, path):
    requests.post(
        f"{BASE}/sendVideo",
        data={"chat_id": chat_id},
        files={"video": open(path, "rb")}
    )


def process_url(chat_id, url):
    try:
        send_message(chat_id, "Downloading... ⏳")

        subprocess.run(
            ["yt-dlp", url, "-o", "video.mp4"],
            check=True
        )

        if os.path.getsize("video.mp4") > 50 * 1024 * 1024:
            send_message(chat_id, "File too large ❌")
        else:
            send_video(chat_id, "video.mp4")

    except Exception as e:
        send_message(chat_id, f"Error ❌: {str(e)[:100]}")

    finally:
        if os.path.exists("video.mp4"):
            os.remove("video.mp4")


# =====================================
# ✅ MODE 1: PIPEDREAM (if URL provided)
# =====================================
if INSTA_URL:
    if DEFAULT_CHAT_ID:
        process_url(DEFAULT_CHAT_ID, INSTA_URL)
    else:
        print("CHAT_ID not set, skipping Pipedream request")

else:
    # =====================================
    # ✅ MODE 2: TELEGRAM (fallback)
    # =====================================

    # Load state
    if os.path.exists("state.json"):
        state = json.load(open("state.json"))
    else:
        state = {"last_update_id": 0}

    if os.path.exists("processed.json"):
        processed = json.load(open("processed.json"))
    else:
        processed = {"handled_updates": []}

    offset = state.get("last_update_id", 0)
    handled = set(processed.get("handled_updates", []))

    # Fetch updates
    res = requests.get(f"{BASE}/getUpdates?offset={offset}&timeout=10").json()

    new_offset = offset

    for upd in res.get("result", []):
        uid = upd["update_id"]

        if uid in handled:
            continue

        message = upd.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        try:
            if not text or "instagram.com" not in text:
                send_message(chat_id, "Send a valid Instagram link 📎")
                continue

            process_url(chat_id, text)

        finally:
            handled.add(uid)
            new_offset = uid + 1

    # Save state
    json.dump({"last_update_id": new_offset}, open("state.json", "w"))
    json.dump({"handled_updates": list(handled)[-100:]}, open("processed.json", "w"))
