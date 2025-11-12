from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = "clave_super_segura"

# --- Configuración de Supabase ---
url = "https://srgmftywhdvjarflzfzi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNyZ21mdHl3aGR2amFyZmx6ZnppIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI5MDUxMzksImV4cCI6MjA3ODQ4MTEzOX0.y8l7iWF-S934QtsoJG8174cHzzlQTXl4RGbS4YMmyrQ"
supabase: Client = create_client(url, key)

# ---------------------- FUNCIONES AUXILIARES ----------------------

def cargar_usuario(nombre):
    """Carga un usuario desde Supabase"""
    response = supabase.table("usuarios").select("*").eq("nombre", nombre).execute()
    if response.data:
        return response.data[0]
    return None

def crear_usuario(nombre, password):
    """Crea un nuevo usuario en la BD"""
    password_hash = generate_password_hash(password)
    supabase.table("usuarios").insert({
        "nombre": nombre,
        "password_hash": password_hash,
        "saldo": 0.0,
        "ahorro": 0.0
    }).execute()

def actualizar_saldo_ahorro(usuario_id, saldo, ahorro):
    """Actualiza el saldo y ahorro del usuario"""
    supabase.table("usuarios").update({
        "saldo": saldo,
        "ahorro": ahorro
    }).eq("id", usuario_id).execute()

def cargar_gastos(usuario_id):
    """Carga los gastos de un usuario"""
    response = supabase.table("gastos").select("*").eq("usuario_id", usuario_id).order("fecha", desc=True).execute()
    return response.data if response.data else []

def crear_gasto(usuario_id, categoria, monto, descripcion):
    """Crea un nuevo gasto"""
    supabase.table("gastos").insert({
        "usuario_id": usuario_id,
        "categoria": categoria,
        "monto": monto,
        "descripcion": descripcion
    }).execute()

def cargar_metas(usuario_id):
    """Carga las metas de un usuario"""
    response = supabase.table("metas").select("*").eq("usuario_id", usuario_id).order("fecha_creacion", desc=True).execute()
    return response.data if response.data else []

def crear_meta(usuario_id, nombre, objetivo):
    """Crea una nueva meta"""
    supabase.table("metas").insert({
        "usuario_id": usuario_id,
        "nombre": nombre,
        "objetivo": objetivo,
        "actual": 0.0,
        "completada": False
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
                session['usuario_id'] = user["id"]
                return redirect(url_for('inicio'))
            else:
                mensaje = "❌ Usuario o contraseña incorrectos"

        elif accion == 'register':
            if not usuario or not contrasena:
                mensaje = "⚠️ Completa todos los campos"
            elif user:
                mensaje = "❌ El usuario ya existe"
            else:
                crear_usuario(usuario, contrasena)
                mensaje = "✅ Usuario registrado exitosamente. Ahora inicia sesión."

    return render_template('login.html', mensaje=mensaje)

@app.route('/inicio')
def inicio():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario_actual = session['usuario']
    usuario_id = session['usuario_id']
    
    user = cargar_usuario(usuario_actual)
    if not user:
        session.clear()
        return redirect(url_for('login'))

    gastos = cargar_gastos(usuario_id)
    metas = cargar_metas(usuario_id)

    return render_template('inicio.html',
                           usuario={
                               "nombre": user["nombre"],
                               "saldo": float(user["saldo"]),
                               "ahorro": float(user["ahorro"]),
                               "gastos": gastos,
                               "metas": metas
                           },
                           nombre_usuario=usuario_actual)

@app.route('/acciones', methods=['GET', 'POST'])
def acciones():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario_actual = session['usuario']
    usuario_id = session['usuario_id']
    
    user = cargar_usuario(usuario_actual)
    if not user:
        session.clear()
        return redirect(url_for('login'))

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
                    actualizar_saldo_ahorro(usuario_id, saldo, ahorro)
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
                    actualizar_saldo_ahorro(usuario_id, saldo, ahorro)
                    crear_gasto(usuario_id, categoria, monto, descripcion)
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
                    actualizar_saldo_ahorro(usuario_id, saldo, ahorro)
                    mensaje = f"🏦 Has ahorrado ${monto:.2f}."

            elif accion == 'nueva_meta':
                nombre_meta = request.form.get('nombre_meta', '').strip()
                monto_objetivo = float(request.form.get('monto_meta', 0))
                if not nombre_meta:
                    mensaje = "⚠️ Ingresa un nombre para la meta"
                elif monto_objetivo <= 0:
                    mensaje = "⚠️ El monto objetivo debe ser mayor a 0"
                else:
                    crear_meta(usuario_id, nombre_meta, monto_objetivo)
                    mensaje = f"🎯 Nueva meta '{nombre_meta}' creada."

        except ValueError:
            mensaje = "⚠️ Ingresa un monto válido"
        except Exception as e:
            mensaje = f"❌ Error: {str(e)}"

    gastos = cargar_gastos(usuario_id)
    metas = cargar_metas(usuario_id)

    return render_template('acciones.html',
                           usuario={
                               "nombre": user["nombre"],
                               "saldo": saldo,
                               "ahorro": ahorro,
                               "gastos": gastos,
                               "metas": metas
                           },
                           mensaje=mensaje,
                           nombre_usuario=usuario_actual)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route("/misiones")
def misiones():
    # Simulamos que tienes un usuario logueado
    # (puedes ajustar esto para que venga de session o Supabase)
    nombre_usuario = "David"

    # Datos de ejemplo que tu plantilla espera
    misiones_data = {
        "nivel": 3,
        "puntos": 120,
        "experiencia": 45,
        "rachas": {
            "ahorro": {"actual": 4, "record": 6},
            "gasto_registrado": {"actual": 2, "record": 5},
            "login": {"actual": 5, "record": 7},
        },
        "logros": {
            "primer_ahorro": True,
            "primera_meta": True,
            "ahorrador_novato": False,
            "ahorrador_experto": False,
            "control_gastos": False,
        },
    }

    usuario = {"gastos": [1, 2, 3, 4, 5]}  # para {{ usuario.gastos|length }}

    return render_template(
        "misiones.html",
        misiones=misiones_data,
        nombre_usuario=nombre_usuario,
        usuario=usuario
    )

if __name__ == '__main__':
    app.run(debug=True)
