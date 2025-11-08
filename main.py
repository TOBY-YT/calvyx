from flask import Flask, request, jsonify
from flask_cors import CORS
from stl import mesh
import tempfile, os, uuid
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# ===============================
# ⚙️ Nastavení Supabase
# ===============================
SUPABASE_URL = "https://euhdtukmbilcmxljjlnp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV1aGR0dWttYmlsY214bGpqbG5wIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjU5MTIzNywiZXhwIjoyMDc4MTY3MjM3fQ.TfMYnJbBHkH6loIZ0fYg4-8lJHM4D3qbDHFQTLHL5wc"
ADMIN_SECRET = "Toby123"

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ VAROVÁNÍ: Supabase credentials nejsou nastavené!")
    print("Nastav environment variables: SUPABASE_URL a SUPABASE_KEY")
    supabase = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase připojeno!")
        print(f"📍 URL: {SUPABASE_URL}")
    except Exception as e:
        print(f"❌ Chyba při připojení k Supabase: {e}")
        supabase = None

# ===============================
# 💰 Výchozí ceníky
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
# 🧠 Databázové funkce
# ===============================
def get_all_keys():
    """Načte všechny klíče z databáze"""
    if not supabase:
        return []
    try:
        response = supabase.table("keys").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ Chyba při načítání klíčů: {e}")
        return []

def get_key(klic):
    """Načte jeden klíč z databáze"""
    if not supabase:
        return None
    try:
        response = supabase.table("keys").select("*").eq("klic", klic).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Chyba při načítání klíče {klic}: {e}")
        return None

def save_key(klic, data):
    """Uloží nebo aktualizuje klíč v databázi"""
    if not supabase:
        print("❌ Supabase není připojeno!")
        return False
    try:
        # Zkontroluj, jestli klíč existuje
        existing = get_key(klic)
        
        payload = {
            "klic": klic,
            "jmeno": data.get("jmeno"),
            "marze": float(data.get("marze", 0)),
            "aktivni": data.get("aktivni", True),
            "email": data.get("email"),
            "ceny": data.get("ceny", MATERIALS)
        }
        
        if existing:
            # Update
            supabase.table("keys").update(payload).eq("klic", klic).execute()
            print(f"♻️ Klíč {klic} aktualizován")
        else:
            # Insert
            supabase.table("keys").insert(payload).execute()
            print(f"✅ Klíč {klic} vytvořen v DB")
        
        return True
    except Exception as e:
        print(f"❌ Chyba při ukládání klíče {klic}: {e}")
        return False

def delete_key(klic):
    """Smaže klíč z databáze"""
    if not supabase:
        return False
    try:
        supabase.table("keys").delete().eq("klic", klic).execute()
        print(f"🗑️ Klíč {klic} smazán")
        return True
    except Exception as e:
        print(f"❌ Chyba při mazání klíče {klic}: {e}")
        return False

# ===============================
# 🌐 Endpoint: Stav serveru
# ===============================
@app.route("/")
def home():
    keys = get_all_keys()
    return jsonify({
        "status": "ok", 
        "message": "Calvyx backend běží",
        "total_keys": len(keys),
        "database": "Supabase" if supabase else "Not connected"
    })

# ===============================
# 🧩 Endpoint: Vytvoření nového klíče
# ===============================
@app.route("/create", methods=["POST"])
def create_user():
    if not supabase:
        return jsonify({"ok": False, "error": "Databáze není připojena"}), 503
    
    # Podporujeme jak form-data tak JSON
    if request.is_json:
        data_input = request.json
        jmeno = data_input.get("name")
        marze = data_input.get("margin", "0")
        ceny_filament = data_input.get("prices", {})
    else:
        jmeno = request.form.get("name")
        marze = request.form.get("margin", "0")
        # Načtení cen z formuláře
        ceny_filament = {}
        for material in MATERIALS.keys():
            price_key = f"price_{material}"
            if price_key in request.form:
                ceny_filament[material] = float(request.form.get(price_key))

    if not jmeno:
        return jsonify({"ok": False, "error": "Jméno je povinné."}), 400

    try:
        marze_val = float(marze)
    except:
        marze_val = 0.0

    # Pokud nebyly poslány vlastní ceny, použijeme výchozí
    if not ceny_filament:
        ceny_filament = MATERIALS.copy()
    else:
        # Doplníme chybějící materiály výchozími cenami
        for material, default_price in MATERIALS.items():
            if material not in ceny_filament:
                ceny_filament[material] = default_price

    # 🧠 Pokud už existuje stejná firma, aktualizujeme její data
    all_keys = get_all_keys()
    for key_data in all_keys:
        if key_data.get("jmeno") == jmeno:
            klic = key_data["klic"]
            save_key(klic, {
                "jmeno": jmeno,
                "marze": marze_val,
                "aktivni": True,
                "email": None,
                "ceny": ceny_filament
            })
            print(f"♻️ Aktualizována marže a ceny pro {jmeno} ({klic})")
            return jsonify({
                "ok": True,
                "key": klic,
                "iframe": f'<iframe src="https://levne3d.cz/kalkulacka.html?klic={klic}" width="600" height="700" style="border:none;"></iframe>',
                "updated": True
            })

    # 🆕 Nový klíč
    klic = str(uuid.uuid4())[:8]
    success = save_key(klic, {
        "jmeno": jmeno,
        "marze": marze_val,
        "aktivni": True,
        "email": None,
        "ceny": ceny_filament
    })
    
    if not success:
        return jsonify({"ok": False, "error": "Chyba při ukládání do databáze"}), 500

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
        
        if not supabase:
            return jsonify({"error": "Databáze není připojena"}), 503
        
        user = get_key(klic)

        if not user:
            return jsonify({"error": "Neplatný klíč."}), 400

        marze = float(user.get("marze", 0)) / 100
        aktivni = user.get("aktivni", True)
        ceny = user.get("ceny", MATERIALS)

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

        # 🧮 Výpočet podle individuálních cen
        material_price = ceny.get(material, MATERIALS.get(material, 2.0))
        strength_mult = STRENGTHS.get(strength, 1.0)
        base_price = volume * material_price * strength_mult
        final_price = base_price * (1 + marze)

        print(f"📊 Výpočet pro {klic}: objem={volume:.2f}cm³, cena={final_price:.2f}Kč")

        return jsonify({
            "objem_cm3": round(volume, 2),
            "materiál": material,
            "pevnost": strength,
            "marže": f"{marze*100:.1f}%",
            "cena": round(final_price, 2)
        })
    except Exception as e:
        print(f"❌ Chyba při výpočtu: {str(e)}")
        return jsonify({"error": str(e)}), 400

# ===============================
# 🔍 Endpoint: Zjištění nastavení klíče
# ===============================
@app.route("/get_settings", methods=["GET"])
def get_settings():
    klic = request.args.get("klic")
    if not klic:
        return jsonify({"error": "Klíč nebyl zadán"}), 400
    
    user = get_key(klic)
    
    if not user:
        return jsonify({"error": "Neplatný klíč"}), 404
    
    return jsonify({
        "ok": True,
        "marze": user.get("marze", 0),
        "aktivni": user.get("aktivni", True),
        "jmeno": user.get("jmeno"),
        "ceny": user.get("ceny", MATERIALS)
    })

# ===============================
# 🆕 Admin: Ruční vytvoření klíče
# ===============================
@app.route("/admin/create_manual", methods=["POST"])
def admin_create_manual():
    secret = request.form.get("secret") or (request.json.get("secret") if request.is_json else None)
    
    if secret != ADMIN_SECRET:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    
    if request.is_json:
        jmeno = request.json.get("name")
        marze = float(request.json.get("margin", 0))
    else:
        jmeno = request.form.get("name")
        marze = float(request.form.get("margin", 0))
    
    if not jmeno:
        return jsonify({"ok": False, "error": "Jméno je povinné"}), 400
    
    klic = str(uuid.uuid4())[:8]
    
    success = save_key(klic, {
        "jmeno": jmeno,
        "marze": marze,
        "aktivni": True,
        "email": None,
        "ceny": MATERIALS.copy()
    })
    
    if not success:
        return jsonify({"ok": False, "error": "Chyba při ukládání"}), 500
    
    return jsonify({
        "ok": True,
        "message": f"Klíč vytvořen: {klic}",
        "key": klic,
        "name": jmeno,
        "margin": marze
    })

# ===============================
# 🗑️ Admin: Smazání klíče
# ===============================
@app.route("/admin/delete", methods=["POST", "GET"])
def admin_delete():
    secret = request.args.get("secret") or request.form.get("secret")
    key = request.args.get("key") or request.form.get("key")
    
    if secret != ADMIN_SECRET:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    
    if not key:
        return jsonify({"ok": False, "error": "Missing key"}), 400
    
    if delete_key(key):
        return jsonify({"ok": True, "message": f"Klíč {key} smazán"})
    else:
        return jsonify({"ok": False, "error": "Chyba při mazání"}), 500

# ===============================
# 🧩 Admin: Deaktivace klíče (URL přístup)
# ===============================
@app.route("/admin/deactivate", methods=["GET"])
def admin_deactivate():
    key = request.args.get("key")
    secret = request.args.get("secret")

    if secret != ADMIN_SECRET:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    if not key:
        return jsonify({"ok": False, "error": "Missing key"}), 400

    user = get_key(key)
    if not user:
        return jsonify({"ok": False, "error": "Key not found"}), 404

    user["aktivni"] = False
    save_key(key, user)
    
    return jsonify({"ok": True, "message": f"Klíč {key} deaktivován."})

# ===============================
# 🧩 Admin: Aktivace klíče (URL přístup)
# ===============================
@app.route("/admin/activate", methods=["GET"])
def admin_activate():
    key = request.args.get("key")
    secret = request.args.get("secret")

    if secret != ADMIN_SECRET:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    user = get_key(key)
    if not user:
        return jsonify({"ok": False, "error": "Key not found"}), 404

    user["aktivni"] = True
    save_key(key, user)
    
    return jsonify({"ok": True, "message": f"Klíč {key} aktivován."})

# ===============================
# 📋 Admin: Výpis všech uživatelů
# ===============================
@app.route("/admin/list", methods=["GET"])
def admin_list():
    secret = request.args.get("secret")
    if secret != ADMIN_SECRET:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    keys = get_all_keys()
    users = []
    
    for key_data in keys:
        users.append({
            "klic": key_data.get("klic"),
            "marze": key_data.get("marze"),
            "aktivni": key_data.get("aktivni", True),
            "jmeno": key_data.get("jmeno"),
            "ceny": key_data.get("ceny", MATERIALS)
        })

    return jsonify({"ok": True, "count": len(users), "users": users})

# ===============================
# 🖥️ Admin: HTML přehled
# ===============================
@app.route("/admin", methods=["GET"])
def admin_panel():
    secret = request.args.get("secret", "")
    if secret != ADMIN_SECRET:
        return """
        <html><body style='font-family:system-ui;padding:40px;background:#f9fafb;'>
        <h2>🔒 Unauthorized</h2>
        <p>Zadej správný ?secret= do URL.</p>
        </body></html>
        """, 401

    return """
<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<title>Calvyx Admin</title>
<style>
body{font-family:system-ui;padding:20px;background:#f9fafb;margin:0;}
.container{max-width:1400px;margin:0 auto;}
.box{background:#fff;padding:20px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:20px;}
h1{margin:0 0 8px 0;color:#111;}
.small{font-size:0.9rem;color:#555;margin-bottom:16px;}
table{border-collapse:collapse;width:100%;margin-top:12px;}
th,td{border:1px solid #e5e7eb;padding:10px;text-align:left;}
th{background:#f3f4f6;font-weight:600;}
button{padding:8px 14px;border-radius:8px;border:0;cursor:pointer;font-weight:500;transition:all 0.2s;}
button:hover{transform:translateY(-1px);}
.on{background:#10b981;color:white;}
.off{background:#ef4444;color:white;}
.delete{background:#f59e0b;color:white;}
.prices{font-size:0.85rem;color:#666;}
code{background:#f3f4f6;padding:2px 6px;border-radius:4px;font-size:0.9em;}
.form-group{margin-bottom:16px;}
.form-group label{display:block;margin-bottom:6px;font-weight:600;color:#374151;}
.form-group input{width:100%;padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:14px;}
.btn-primary{background:linear-gradient(135deg,#06b6d4,#3b82f6);color:white;padding:12px 24px;border:none;border-radius:8px;font-weight:600;cursor:pointer;width:100%;}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(6,182,212,0.3);}
#status{padding:12px;border-radius:8px;margin-bottom:16px;}
.create-form{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
@media(max-width:768px){.create-form{grid-template-columns:1fr;}}
</style>
</head>
<body>
<div class='container'>
<div class='box'>
<h1>🎛️ Calvyx – Admin Panel</h1>
<p class='small'>Správa klíčů přes Supabase databázi</p>
<div id='status' style='display:none;'></div>
</div>

<div class='box'>
<h2 style='margin-top:0;'>➕ Vytvořit nový klíč</h2>
<div class='create-form'>
<div class='form-group'>
<label>Jméno / Název firmy:</label>
<input type='text' id='newName' placeholder='Např. Jan Novák'>
</div>
<div class='form-group'>
<label>Marže (%):</label>
<input type='number' id='newMargin' value='25' min='0' max='100'>
</div>
</div>
<button class='btn-primary' onclick='createKey()'>✨ Vytvořit klíč</button>
</div>

<div class='box'>
<h2 style='margin-top:0;'>📋 Seznam klíčů</h2>
<div id='listStatus'>Načítám data...</div>
<table id='tbl' style='display:none;'>
<thead><tr><th>Klíč</th><th>Jméno</th><th>Marže</th><th>Ceny filamentů</th><th>Status</th><th>Akce</th></tr></thead>
<tbody id='rows'></tbody>
</table>
</div>
</div>

<script>
const SECRET=new URLSearchParams(location.search).get('secret')||'';

function showStatus(msg,type='success'){
const el=document.getElementById('status');
el.style.display='block';
el.style.background=type==='error'?'#fee2e2':'#d1fae5';
el.style.color=type==='error'?'#991b1b':'#065f46';
el.textContent=msg;
setTimeout(()=>el.style.display='none',4000);
}

async function createKey(){
const name=document.getElementById('newName').value;
const margin=document.getElementById('newMargin').value;
if(!name){showStatus('Jméno je povinné!','error');return;}
const fd=new FormData();
fd.append('secret',SECRET);
fd.append('name',name);
fd.append('margin',margin);
try{
const res=await fetch('/admin/create_manual',{method:'POST',body:fd});
const j=await res.json();
if(j.ok){
showStatus('✅ Klíč vytvořen: '+j.key);
document.getElementById('newName').value='';
loadList();
}else{
showStatus('❌ '+j.error,'error');
}
}catch(e){showStatus('❌ Chyba: '+e.message,'error');}
}

async function loadList(){
try{
const res=await fetch('/admin/list?secret='+SECRET);
const j=await res.json();
if(!j.ok){document.getElementById('listStatus').textContent='Chyba: '+(j.error||'?');return;}
document.getElementById('listStatus').textContent='Celkem záznamů: '+j.count;
const rows=document.getElementById('rows');
rows.innerHTML='';
j.users.forEach(u=>{
const pricesStr=Object.entries(u.ceny).map(([m,p])=>`${m}:${p.toFixed(2)}Kč`).join(', ');
const tr=document.createElement('tr');
tr.innerHTML=`
<td><code>${u.klic}</code></td>
<td>${u.jmeno||'-'}</td>
<td>${u.marze}%</td>
<td class='prices'>${pricesStr}</td>
<td>${u.aktivni?'✅ Aktivní':'❌ Neaktivní'}</td>
<td>
${u.aktivni
?`<button class='off' onclick="toggle('${u.klic}',false)">Deaktivovat</button>`
:`<button class='on' onclick="toggle('${u.klic}',true)">Aktivovat</button>`}
<button class='delete' onclick="deleteKey('${u.klic}')">Smazat</button>
</td>`;
rows.appendChild(tr);
});
document.getElementById('tbl').style.display='table';
}catch(e){document.getElementById('listStatus').textContent='❌ Chyba načítání';}
}

async function toggle(k,a){
if(!confirm((a?'Aktivovat':'Deaktivovat')+' '+k+'?'))return;
const url=a?'/admin/activate':'/admin/deactivate';
const res=await fetch(url+'?key='+k+'&secret='+SECRET);
const j=await res.json();
showStatus(j.message||j.error,j.ok?'success':'error');
loadList();
}

async function deleteKey(k){
if(!confirm('Opravdu smazat klíč '+k+'? Tato akce je nevratná!'))return;
const fd=new FormData();
fd.append('secret',SECRET);
fd.append('key',k);
const res=await fetch('/admin/delete',{method:'POST',body:fd});
const j=await res.json();
showStatus(j.message||j.error,j.ok?'success':'error');
loadList();
}

loadList();
</script>
</body>
</html>
"""

# ===============================
# 🚀 Spuštění
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

