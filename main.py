from flask import Flask, request, jsonify
from stl import mesh
import tempfile, os

app = Flask(__name__)

MATERIALS = {
    "PLA": 0.05,
    "PETG": 0.06,
    "TPU": 0.08,
    "ASA": 0.07
}

STRENGTHS = {
    "slabá": 1.0,
    "střední": 1.3,
    "pevná": 1.6
}

@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "3D kalkulačka API běží"})

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        file = request.files["file"]
        material = request.form.get("material", "PLA")
        strength = request.form.get("strength", "střední")
        margin = float(request.form.get("margin", 0)) / 100

        with tempfile.NamedTemporaryFile(delete=False, suffix=".stl") as tmp:
            file.save(tmp.name)
            model = mesh.Mesh.from_file(tmp.name)
            volume = abs(model.get_mass_properties()[0]) / 1000  # cm³
            os.unlink(tmp.name)

        base_price = volume * MATERIALS[material] * STRENGTHS[strength]
        final_price = base_price * (1 + margin)

        return jsonify({
            "objem_cm3": round(volume, 2),
            "materiál": material,
            "pevnost": strength,
            "marže": f"{margin * 100:.1f}%",
            "cena": round(final_price, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400
