from flask import Flask, request, jsonify
from flask_cors import CORS
from stl import mesh
import tempfile, os, json, uuid

app = Flask(__name__)
CORS(app)

DATA_FILE = "marze.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

MATERIALS = {
    "PLA": 1.0,
    "PETG": 1.2,
    "TPU": 1.6,
    "ASA": 1.4,
}

STRENGTHS = {
    "slabá": 1.0,
    "střední": 1.3,
    "pevná": 1.6
}

@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "Calvyx backend běží"})

@app.route("/create", methods=["POST"])
def create_user():
    marze = request.form.get("margin", "0")
    klic = str(uuid.uuid4())[:8]
    data = load_data()
    data[klic] = float(marze)
    save_data(data)
    return jsonify({
        "ok": True,
        "key": klic,
        "iframe": f'<iframe src="https://levne3d.cz/kalkulacka.html?klic={klic}" width="600" height="700" style="border:none;"></iframe>'
    })

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        klic = request.args.get("klic")
        data = load_data()
        marze = float(data.get(klic, 0)) / 100

        file = request.files["file"]
        material = request.form.get("material", "PLA")
        strength = request.form.get("strength", "střední")

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

