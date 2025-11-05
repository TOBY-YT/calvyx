from flask import Flask, request, jsonify
from flask_cors import CORS
from stl import mesh
import tempfile, os, json, uuid

app = Flask(__name__)
CORS(app)

# ===============================
# ⚙️ Nastavení
# ===============================
DATA_FILE = "marze.json"
ADMIN_SECRET = "Toby123"  # ZMĚŇ si to na něco svého (tajné heslo!)

# ===============================
# 🧠 Pomocné funkce
# ===============================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===============================
# 💰 Ceníky
# ===============================
MATERIALS = {
    "PLA": 2.0,
    "PETG": 2.4,
    "TPU": 3.2,
    "ASA": 2.8
}

STRENGTHS = {
    "slabá": 1.0,
    "střední": 1.3,
    "pevná": 1.6
}

# ===============================
# 🌐 Endpoint: Stav serveru
# ===============================
@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "Calvyx backend běží"})

# ===============================
# 🧩 Endpoint: Vytvoření nového klíče
# ===============================
@app.route("/create", methods=["POST"])
def create_user():
    marze = request.form.get("margin", "0")
    email = request.form.get("email")
    jmeno = request.form.get("name")

    try:
        marze_val = float(marze)
    except:
        marze_val = 0.0

    klic = str(uuid.uuid4())[:8]
    data = load_data()
    data[klic] = {
        "marze": marze_val,
        "aktivni": True,
        "email": email,
        "jmeno": jmeno
    }
    save_data(data)

    print(f"✅ Nový klíč vytvořen: {klic} ({email or 'neznámý'}) marže {marze_val}%")

    return jsonify({
        "ok": True,
        "key": klic,
        "iframe": f'<iframe src="https://levne3d.cz/kalkulacka.html?klic={klic}" width="600" height="700" style="border:none;"></iframe>'
    })

# ===============================
# 🧮 Endpoint: Výpočet ceny
# ===============================
@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        klic = request.args.get("klic")
        data = load_data()
        user = data.get(klic)

        if not user:
            return jsonify({"error": "Neplatný klíč."}), 400

        # starý formát = jen číslo
        if isinstance(user, (int, float)):
            marze = user / 100
            aktivni = True
        else:
            marze = float(user.get("marze", 0)) / 100
            aktivni = user.get("aktivni", True)

        if not aktivni:
            return jsonify({"error": "Tento účet nemá aktivní členství."}), 403

        file = request.files.get("file")
        if not file:
            return jsonify({"error": "Soubor STL nebyl zaslán."}), 400

        material = request.form.get("material", "PLA")
        strength = request.form.get("strength", "střední")

        # výpočet objemu
        with tempfile.NamedTemporaryFile(delete=False, suffix=".stl") as tmp:
            file.save(tmp.name)
            model = mesh.Mesh.from_file(tmp.name)
            volume = abs(model.get_mass_properties()[0]) / 1000  # cm³
            os.unlink(tmp.name)

        base_price = volume * MATERIALS.get(material, 0.05) * STRENGTHS.get(strength, 1.0)
        final_price = base_price * (1 + marze)

        return jsonify({
            "objem_cm3": round(volume, 2),
            "materiál": material,
            "pevnost": strength,
            "marže": f"{marze*100:.1f}%",
            "cena": round(final_price, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ===============================
# 🧩 Admin: Deaktivace klíče
# ===============================
@app.route("/admin/deactivate", methods=["GET"])
def admin_deactivate():
    key = request.args.get("key")
    secret = request.args.get("secret")

    if secret != ADMIN_SECRET:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    if not key:
        return jsonify({"ok": False, "error": "Missing key"}), 400

    data = load_data()
    if key not in data:
        return jsonify({"ok": False, "error": "Key not found"}), 404

    if isinstance(data[key], dict):
        data[key]["aktivni"] = False
    else:
        data[key] = {"marze": data[key], "aktivni": False}

    save_data(data)
    print(f"🚫 Klíč {key} deaktivován")
    return jsonify({"ok": True, "message": f"Klíč {key} deaktivován."})

# ===============================
# 🧩 Admin: Aktivace klíče
# ===============================
@app.route("/admin/activate", methods=["GET"])
def admin_activate():
    key = request.args.get("key")
    secret = request.args.get("secret")

    if secret != ADMIN_SECRET:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    data = load_data()
    if key not in data:
        return jsonify({"ok": False, "error": "Key not found"}), 404

    if isinstance(data[key], dict):
        data[key]["aktivni"] = True
    else:
        data[key] = {"marze": data[key], "aktivni": True}

    save_data(data)
    print(f"✅ Klíč {key} znovu aktivován")
    return jsonify({"ok": True, "message": f"Klíč {key} aktivován."})

# ===============================
# 📋 Admin: Výpis všech uživatelů
# ===============================
@app.route("/admin/list", methods=["GET"])
def admin_list():
    secret = request.args.get("secret")
    if secret != ADMIN_SECRET:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    data = load_data()
    users = []
    for key, val in data.items():
        if isinstance(val, dict):
            users.append({
                "klic": key,
                "marze": val.get("marze"),
                "aktivni": val.get("aktivni"),
                "email": val.get("email"),
                "jmeno": val.get("jmeno")
            })
        else:
            users.append({
                "klic": key,
                "marze": val,
                "aktivni": True,
                "email": None,
                "jmeno": None
            })

    return jsonify({"ok": True, "count": len(users), "users": users})

# ===============================
# 🚀 Spuštění
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
