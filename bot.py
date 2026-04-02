import requests, json, os, subprocess

TOKEN = os.environ["BOT_TOKEN"]
BASE = f"https://api.telegram.org/bot{TOKEN}"

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

# Load state
state = json.load(open("state.json"))
processed = json.load(open("processed.json"))

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

        send_message(chat_id, "Downloading... ⏳")

        # download
        subprocess.run(
            ["yt-dlp", text, "-o", "video.mp4"],
            check=True
        )

        # size check (~50MB)
        if os.path.getsize("video.mp4") > 50 * 1024 * 1024:
            send_message(chat_id, "File too large ❌")
        else:
            send_video(chat_id, "video.mp4")

    except Exception as e:
        send_message(chat_id, f"Error ❌: {str(e)[:100]}")

    finally:
        handled.add(uid)
        new_offset = uid + 1

        if os.path.exists("video.mp4"):
            os.remove("video.mp4")

# Save state
json.dump({"last_update_id": new_offset}, open("state.json", "w"))
json.dump({"handled_updates": list(handled)[-100:]}, open("processed.json", "w"))
