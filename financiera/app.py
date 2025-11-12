from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = "clave_super_segura"

# --- Configuración de Supabase ---
url = "https://vxnpqpthtlcbhbtpgovh.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ4bnBxcHRodGxjYmhidHBnb3ZoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4OTgyNzIsImV4cCI6MjA3ODQ3NDI3Mn0.0nZo-u3xj9YAPW0YClrNQFuBkJjUpo1UQAFPCpMNvJc"
supabase: Client = create_client(url, key)

# ---------------------- FUNCIONES AUXILIARES ----------------------

def crear_usuario_base(usuario):
    return {
        "nombre": usuario,
        "saldo": 0.0,
        "ahorro": 0.0,
        "gastos": [],
        "metas": [],
        "misiones": {
            "rachas": {
                "ahorro": {"actual": 0, "record": 0, "ultima_fecha": None},
                "gasto_registrado": {"actual": 0, "record": 0, "ultima_fecha": None},
                "login": {"actual": 0, "record": 0, "ultima_fecha": None},
            },
            "logros": {
                "primer_ahorro": False,
                "primera_meta": False,
                "ahorrador_novato": False,
                "ahorrador_experto": False,
                "control_gastos": False,
            },
            "puntos": 0,
            "nivel": 1,
            "experiencia": 0,
        },
    }

def cargar_usuario(nombre):
    """Carga un usuario desde Supabase"""
    response = supabase.table("usuarios").select("*").eq("nombre", nombre).execute()
    if response.data:
        return response.data[0]
    return None

def guardar_usuario(nombre, password_hash, datos, saldo=0, ahorro=0):
    """Guarda o actualiza un usuario en Supabase"""
    existente = cargar_usuario(nombre)
    if existente:
        supabase.table("usuarios").update({
            "datos": datos,
            "saldo": saldo,
            "ahorro": ahorro
        }).eq("nombre", nombre).execute()
    else:
        supabase.table("usuarios").insert({
            "nombre": nombre,
            "password_hash": password_hash,
            "saldo": saldo,
            "ahorro": ahorro,
            "datos": datos
        }).execute()

# ---------------------- FLASK ROUTES ----------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario' in session:
        return redirect(url_for('inicio'))

    mensaje = ""

    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        contrasena = request.form.get('contrasena', '')
        accion = request.form.get('accion')

        user = cargar_usuario(usuario)

        if accion == 'login':
            if user and check_password_hash(user["password_hash"], contrasena):
                session['usuario'] = usuario
                return redirect(url_for('inicio'))
            else:
                mensaje = "❌ Usuario o contraseña incorrectos"

        elif accion == 'register':
            if not usuario or not contrasena:
                mensaje = "⚠️ Completa todos los campos"
            elif user:
                mensaje = "❌ El usuario ya existe"
            else:
                password_hash = generate_password_hash(contrasena)
                datos = crear_usuario_base(usuario)
                guardar_usuario(usuario, password_hash, datos)
                mensaje = "✅ Usuario registrado exitosamente. Ahora inicia sesión."

    return render_template('login.html', mensaje=mensaje)

@app.route('/inicio')
def inicio():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario_actual = session['usuario']
    user = cargar_usuario(usuario_actual)
    if not user:
        session.pop('usuario', None)
        return redirect(url_for('login'))

    return render_template('inicio.html',
                           usuario=user["datos"],
                           nombre_usuario=usuario_actual)

@app.route('/acciones', methods=['GET', 'POST'])
def acciones():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario_actual = session['usuario']
    user = cargar_usuario(usuario_actual)
    if not user:
        session.pop('usuario', None)
        return redirect(url_for('login'))

    usuario_data = user["datos"]
    saldo = float(user["saldo"])
    ahorro = float(user["ahorro"])
    mensaje = ""

    if request.method == 'POST':
        accion = request.form.get('accion')
        try:
            if accion == 'ingresar':
                cantidad = float(request.form.get('cantidad', 0))
                if cantidad > 0:
                    saldo += cantidad
                    mensaje = f"💰 Se han agregado ${cantidad:.2f} a tu cuenta."
                else:
                    mensaje = "⚠️ La cantidad debe ser mayor a 0"

            elif accion == 'gastar':
                categoria = request.form.get('categoria', '').strip()
                monto = float(request.form.get('monto', 0))
                descripcion = request.form.get('descripcion', '').strip()

                if not categoria:
                    mensaje = "⚠️ Ingresa una categoría"
                elif monto <= 0:
                    mensaje = "⚠️ El monto debe ser mayor a 0"
                elif monto > saldo:
                    mensaje = "⚠️ No tienes suficiente saldo"
                else:
                    saldo -= monto
                    gasto = {
                        'categoria': categoria,
                        'monto': monto,
                        'descripcion': descripcion,
                        'fecha': datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                    usuario_data["gastos"].append(gasto)
                    mensaje = f"🛍️ Has gastado ${monto:.2f} en {categoria}."

            elif accion == 'ahorrar':
                monto = float(request.form.get('monto_ahorro', 0))
                if monto <= 0:
                    mensaje = "⚠️ El monto debe ser mayor a 0"
                elif monto > saldo:
                    mensaje = "⚠️ No tienes suficiente saldo"
                else:
                    saldo -= monto
                    ahorro += monto
                    mensaje = f"🏦 Has ahorrado ${monto:.2f}."

            elif accion == 'nueva_meta':
                nombre_meta = request.form.get('nombre_meta', '').strip()
                monto_objetivo = float(request.form.get('monto_meta', 0))
                if not nombre_meta:
                    mensaje = "⚠️ Ingresa un nombre para la meta"
                elif monto_objetivo <= 0:
                    mensaje = "⚠️ El monto objetivo debe ser mayor a 0"
                else:
                    nueva_meta = {
                        'nombre': nombre_meta,
                        'objetivo': monto_objetivo,
                        'actual': 0.0,
                        'completada': False,
                        'fecha_creacion': datetime.now().strftime("%d/%m/%Y")
                    }
                    usuario_data["metas"].append(nueva_meta)
                    mensaje = f"🎯 Nueva meta '{nombre_meta}' creada."

            guardar_usuario(usuario_actual, user["password_hash"], usuario_data, saldo, ahorro)

        except ValueError:
            mensaje = "⚠️ Ingresa un monto válido"

    return render_template('acciones.html',
                           usuario=usuario_data,
                           mensaje=mensaje,
                           nombre_usuario=usuario_actual)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
