import os, json, uuid
import numpy as np
import face_recognition
from flask import Flask, request, render_template_string, redirect, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "o'zgartiring-bu-kalitni")
ADMIN_PAROL = os.environ.get("ADMIN_PAROL", "1234")  # o'zgartiring!

BAZA = "baza.json"
RASM_PAPKA = "rasmlar"
os.makedirs(RASM_PAPKA, exist_ok=True)


def bazani_ol():
    if os.path.exists(BAZA):
        with open(BAZA, encoding="utf-8") as f:
            return json.load(f)
    return []


def bazani_saqla(data):
    with open(BAZA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


STIL = """
<style>
 body{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;max-width:520px;margin:0 auto;padding:20px}
 h1{text-align:center}
 .karta{background:#1e293b;border-radius:14px;padding:18px;margin:16px 0}
 input,textarea,button{width:100%;padding:12px;margin:6px 0;border-radius:10px;border:0;font-size:16px;box-sizing:border-box}
 input,textarea{background:#0f172a;color:#e2e8f0;border:1px solid #334155}
 button{background:#6366f1;color:#fff;cursor:pointer;font-weight:600}
 img{max-width:100%;border-radius:12px}
 a{color:#a5b4fc}
 .xato{color:#fca5a5}
</style>
"""

BOSH = STIL + """
<h1>🔍 Kim bu?</h1>
<div class="karta">
 <form method="post" enctype="multipart/form-data">
  <p>Rasm yuklang, men kimligini topaman:</p>
  <input type="file" name="rasm" accept="image/*" capture required>
  <button>Qidirish</button>
 </form>
</div>
{% if xabar %}<div class="karta xato">{{ xabar }}</div>{% endif %}
{% if topildi %}
<div class="karta">
 <img src="/rasm/{{ topildi.rasm }}">
 <h2>{{ topildi.ism }}</h2>
 <p style="white-space:pre-wrap">{{ topildi.malumot }}</p>
 <small>Moslik: {{ foiz }}%</small>
</div>
{% endif %}
<p style="text-align:center"><a href="/admin">admin</a></p>
"""

ADMIN = STIL + """
<h1>⚙️ Admin</h1>
<div class="karta">
 <form method="post" enctype="multipart/form-data">
  <input name="ism" placeholder="Ismi" required>
  <textarea name="malumot" rows="5" placeholder="Hazil ma'lumotlar..." required></textarea>
  <input type="file" name="rasm" accept="image/*" required>
  <button>Qo'shish</button>
 </form>
 {% if xabar %}<p class="xato">{{ xabar }}</p>{% endif %}
</div>
<div class="karta">
 <b>Bazada: {{ odamlar|length }} ta</b>
 {% for o in odamlar %}
  <p>{{ o.ism }} — <a href="/ochir/{{ o.id }}">o'chirish</a></p>
 {% endfor %}
</div>
<p style="text-align:center"><a href="/">← qidiruv</a></p>
"""

KIRISH = STIL + """
<h1>🔒 Kirish</h1>
<div class="karta"><form method="post">
 <input type="password" name="parol" placeholder="Parol" required>
 <button>Kirish</button></form>
 {% if xabar %}<p class="xato">{{ xabar }}</p>{% endif %}
</div>
"""


def yuz_kodi(fayl):
    rasm = face_recognition.load_image_file(fayl)
    kodlar = face_recognition.face_encodings(rasm)
    return kodlar[0] if kodlar else None


@app.route("/", methods=["GET", "POST"])
def bosh():
    xabar, topildi, foiz = None, None, None
    if request.method == "POST":
        kod = yuz_kodi(request.files["rasm"])
        odamlar = bazani_ol()
        if kod is None:
            xabar = "Rasmda yuz topilmadi. Boshqa rasm sinab ko'ring."
        elif not odamlar:
            xabar = "Baza hali bo'sh."
        else:
            masofalar = face_recognition.face_distance(
                [np.array(o["kod"]) for o in odamlar], kod
            )
            i = int(np.argmin(masofalar))
            if masofalar[i] <= 0.6:
                topildi = odamlar[i]
                foiz = round((1 - masofalar[i]) * 100)
            else:
                xabar = "Bu odam bazada yo'q 🤷"
    return render_template_string(BOSH, xabar=xabar, topildi=topildi, foiz=foiz)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin"):
        xabar = None
        if request.method == "POST":
            if request.form["parol"] == ADMIN_PAROL:
                session["admin"] = True
                return redirect("/admin")
            xabar = "Parol noto'g'ri"
        return render_template_string(KIRISH, xabar=xabar)

    xabar = None
    if request.method == "POST":
        fayl = request.files["rasm"]
        kod = yuz_kodi(fayl)
        if kod is None:
            xabar = "Rasmda yuz topilmadi, aniqroq rasm tanlang."
        else:
            fayl.seek(0)
            id_ = uuid.uuid4().hex[:8]
            nom = id_ + ".jpg"
            fayl.save(os.path.join(RASM_PAPKA, nom))
            odamlar = bazani_ol()
            odamlar.append({
                "id": id_,
                "ism": request.form["ism"],
                "malumot": request.form["malumot"],
                "rasm": nom,
                "kod": kod.tolist(),
            })
            bazani_saqla(odamlar)
            xabar = "Qo'shildi ✅"
    return render_template_string(ADMIN, odamlar=bazani_ol(), xabar=xabar)


@app.route("/ochir/<id_>")
def ochir(id_):
    if not session.get("admin"):
        return redirect("/admin")
    odamlar = [o for o in bazani_ol() if o["id"] != id_]
    bazani_saqla(odamlar)
    return redirect("/admin")


@app.route("/rasm/<nom>")
def rasm(nom):
    from flask import send_from_directory
    return send_from_directory(RASM_PAPKA, nom)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
