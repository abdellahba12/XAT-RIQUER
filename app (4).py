import os
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from chat_backend import RiquerChatBot
import logging
from functools import wraps
import secrets

# Configurar Flask
app = Flask(__name__, 
    static_folder='static',
    template_folder='templates'
)
CORS(app)

# Configurar clave secreta para sesiones
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Verificar configuración OAuth
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    logger.error("⚠️ GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET no están configurados!")
else:
    logger.info("✅ Credenciales OAuth encontradas")

# Configurar OAuth
oauth = OAuth(app)

# Función para obtener la URL base correcta
def get_base_url():
    # Para Hugging Face Spaces - siempre usar HTTPS
    if 'hf.space' in request.headers.get('Host', ''):
        return f"https://{request.headers.get('Host')}"
    
    # Si hay header X-Forwarded-Proto (proxy) - forzar HTTPS
    if request.headers.get('X-Forwarded-Proto'):
        return f"https://{request.headers.get('Host', '')}"
    
    # Para cualquier entorno con proxy, usar HTTPS por defecto
    host = request.headers.get('Host', request.host)
    return f"https://{host}"

# Registrar Google OAuth con configuración completa
try:
    google = oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        access_token_url='https://oauth2.googleapis.com/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'prompt': 'select_account'  # Forzar selección de cuenta
        }
    )
    logger.info("✅ Google OAuth registrado correctamente")
except Exception as e:
    logger.error(f"❌ Error registrando OAuth: {str(e)}")
    google = None

# Inicializar el bot
try:
    bot = RiquerChatBot()
    logger.info("✅ Bot inicializado correctamente")
except Exception as e:
    logger.error(f"❌ Error inicializando bot: {str(e)}")
    bot = None

# Decorator para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Ruta de login mejorada con manejo de errores
@app.route('/login')
def login():
    # Si ya está logueado, redirigir al chat
    if 'user' in session:
        return redirect(url_for('index'))
    
    # Verificar si hay error de OAuth
    error = request.args.get('error')
    error_description = request.args.get('error_description', '')
    
    if error:
        logger.error(f"OAuth error: {error} - {error_description}")
    
    # Verificar configuración
    oauth_configured = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    
    # Crear página de login con información de estado
    base_url = get_base_url()
    default_error_text = "Error d'autenticació amb Google"
    error_msg = f'<div class="error-message">Error: {error_description or default_error_text}</div>' if error else ''
    warning_msg = '<div class="warning-message">⚠️ OAuth no està configurat correctament. Comprova les variables d\'entorn.</div>' if not oauth_configured else ''
    disabled_style = 'style="pointer-events: none; opacity: 0.5;"' if not oauth_configured else ''
    oauth_status = '✅ Sí' if oauth_configured else '❌ No'
    
    return f'''
    <!DOCTYPE html>
    <html lang="ca">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Iniciar Sessió - Institut Alexandre de Riquer</title>
        <link rel="stylesheet" href="/static/css/styles.css">
        <style>
            .login-container {{
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }}
            .login-card {{
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.15);
                text-align: center;
                max-width: 400px;
                width: 100%;
                margin: 20px;
            }}
            .login-logo {{
                width: 120px;
                height: 120px;
                margin: 0 auto 20px;
                border-radius: 16px;
            }}
            .login-title {{
                color: #2a5d84;
                margin-bottom: 10px;
                font-size: 24px;
            }}
            .login-subtitle {{
                color: #5a6c7d;
                margin-bottom: 30px;
            }}
            .google-btn {{
                display: inline-flex;
                align-items: center;
                gap: 12px;
                background: white;
                color: #333;
                border: 2px solid #ddd;
                padding: 12px 24px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 500;
                transition: all 0.3s ease;
                margin: 10px 0;
            }}
            .google-btn:hover {{
                background: #f8f9fa;
                border-color: #4285f4;
                box-shadow: 0 2px 8px rgba(66, 133, 244, 0.3);
            }}
            .google-btn:disabled {{
                opacity: 0.5;
                cursor: not-allowed;
            }}
            .google-icon {{
                width: 20px;
                height: 20px;
            }}
            .info-text {{
                margin-top: 30px;
                font-size: 14px;
                color: #666;
            }}
            .error-message {{
                background: #fee;
                border: 1px solid #fcc;
                border-radius: 8px;
                padding: 12px;
                margin: 20px 0;
                color: #c00;
                font-size: 14px;
            }}
            .warning-message {{
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 12px;
                margin: 20px 0;
                color: #856404;
                font-size: 14px;
            }}
            .debug-info {{
                background: #f0f0f0;
                border-radius: 8px;
                padding: 12px;
                margin-top: 20px;
                font-size: 12px;
                color: #666;
                text-align: left;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-card">
                <img src="/static/logo.png" alt="Institut Alexandre de Riquer" class="login-logo" onerror="this.style.display='none'">
                <h1 class="login-title">Benvingut/da</h1>
                <p class="login-subtitle">Inicia sessió per accedir al xat de l'Institut</p>
                
                {error_msg}
                
                {warning_msg}
                
                <a href="/auth/google" class="google-btn" {disabled_style}>
                    <svg class="google-icon" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    Iniciar sessió amb Google
                </a>
                
                <p class="info-text">
                    En iniciar sessió, acceptes que s'utilitzi el teu nom i correu per personalitzar l'experiència del xat.
                </p>
                
            </div>
        </div>
    </body>
    </html>
    '''

# Callback de Google OAuth con mejor gestión de errores
@app.route('/auth/google')
def google_auth():
    if not google:
        logger.error("Google OAuth no está configurado")
        return redirect(url_for('login', error='oauth_not_configured'))
    
    try:
        # Obtener URL base dinámica - forzar HTTPS para Hugging Face
        base_url = get_base_url()
        redirect_uri = f"{base_url}/auth/google/callback"
        
        logger.info(f"=== OAuth Request ===")
        logger.info(f"Host header: {request.headers.get('Host')}")
        logger.info(f"X-Forwarded-Proto: {request.headers.get('X-Forwarded-Proto')}")
        logger.info(f"Base URL calculada: {base_url}")
        logger.info(f"Redirect URI: {redirect_uri}")
        logger.info(f"===================")
        
        # Forzar redirect_uri específico para Hugging Face
        if 'hf.space' in request.headers.get('Host', ''):
            redirect_uri = f"https://{request.headers.get('Host')}/auth/google/callback"
            logger.info(f"URI forzada para HF: {redirect_uri}")
        
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        logger.error(f"Error iniciando OAuth: {str(e)}")
        return redirect(url_for('login', error='oauth_init_error', error_description=str(e)))

@app.route('/auth/google/callback')
def google_callback():
    if not google:
        return redirect(url_for('login', error='oauth_not_configured'))
    
    try:
        token = google.authorize_access_token()
        
        # El token incluye la información del usuario
        user_info = token.get('userinfo')
        
        if not user_info:
            # Si no hay userinfo en el token, intentar obtenerla
            resp = google.get('userinfo')
            user_info = resp.json()
        
        if user_info:
            email = user_info.get('email', '')
            
            # Guardar información del usuario en la sesión
            session['user'] = {
                'email': email,
                'name': user_info.get('name', ''),
                'picture': user_info.get('picture', ''),
                'given_name': user_info.get('given_name', '')
            }
            
            logger.info(f"✅ Usuario autenticado: {email}")
            return redirect(url_for('index'))
        else:
            logger.error("No se pudo obtener información del usuario")
            return redirect(url_for('login', error='no_user_info'))
            
    except Exception as e:
        logger.error(f"❌ Error en OAuth callback: {str(e)}")
        return redirect(url_for('login', error='callback_error', error_description=str(e)))

# Ruta de logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Ruta principal - servir el HTML
@app.route('/')
@login_required
def index():
    return render_template('index_oauth.html', user=session['user'])

# Ruta de debug mejorada
@app.route('/debug')
def debug():
    return jsonify({
        'status': 'ok',
        'base_url': get_base_url(),
        'host': request.headers.get('Host'),
        'x_forwarded_proto': request.headers.get('X-Forwarded-Proto'),
        'x_forwarded_host': request.headers.get('X-Forwarded-Host'),
        'full_url': request.url,
        'redirect_uri': f"{get_base_url()}/auth/google/callback",
        'oauth_configured': bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        'client_id_exists': bool(GOOGLE_CLIENT_ID),
        'client_secret_exists': bool(GOOGLE_CLIENT_SECRET),
        'environment': 'Hugging Face Spaces' if 'hf.space' in request.headers.get('Host', '') else 'Local',
        'all_headers': dict(request.headers)
    })

# Ruta para archivos estáticos
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# API endpoint para el chat
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    if not bot:
        return jsonify({
            'status': 'error',
            'message': 'Bot no inicializado'
        }), 500
    
    try:
        data = request.json
        message = data.get('message', '')
        
        # Usar datos del usuario autenticado
        user = session.get('user', {})
        user_data = {
            'nom': user.get('name', 'Usuari'),
            'contacte': user.get('email', '')
        }
        
        # Procesar mensaje con el bot
        response = bot.process_message(message, user_data)
        
        return jsonify({
            'status': 'success',
            'response': response,
            'timestamp': data.get('timestamp', '')
        })
        
    except Exception as e:
        logger.error(f"Error en /api/chat: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error processant la consulta',
            'error': str(e)
        }), 500

# API endpoint para obtener lista de profesores
@app.route('/api/teachers')
@login_required
def get_teachers():
    """Endpoint para obtener la lista de profesores"""
    if not bot:
        return jsonify({
            'status': 'error',
            'error': 'Bot no inicializado'
        }), 500
    
    try:
        teachers = bot.get_teachers_list()
        return jsonify({
            'status': 'success',
            'teachers': teachers
        })
    except Exception as e:
        logger.error(f"Error obtenint professors: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
    
# API endpoint para cambiar idioma
@app.route('/api/language', methods=['POST'])
@login_required
def set_language():
    try:
        data = request.json
        language = data.get('language', 'ca')
        
        # Guardar preferencia de idioma en la sesión
        session['language'] = language
        
        return jsonify({
            'status': 'success',
            'language': language
        })
        
    except Exception as e:
        logger.error(f"Error setting language: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# API endpoint para obtener información del usuario
@app.route('/api/user')
@login_required
def get_user():
    return jsonify(session.get('user', {}))

# Ruta para el logo
@app.route('/logo.png')
def logo():
    if os.path.exists('static/logo.png'):
        return send_from_directory('static', 'logo.png')
    else:
        return '', 404

# Health check mejorado
@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok', 
        'service': 'Riquer Chat Bot with OAuth',
        'environment': 'Hugging Face Spaces' if 'hf.space' in request.headers.get('Host', '') else 'Local',
        'oauth_configured': bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        'bot_initialized': bot is not None
    })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('login'))

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

# Per Hugging Face Spaces
if __name__ == '__main__':
    # Crear directorios si no existen
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Obtenir port de Hugging Face
    port = int(os.environ.get('PORT', 7860))
    
    print("\n🚀 Riquer ChatBot iniciado!")
    print(f"📍 Port: {port}")
    print("🔐 OAuth configurado con Google" if (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET) else "⚠️  OAuth NO configurado")
    
    # Verificar configuración
    if not GOOGLE_CLIENT_ID:
        print("⚠️  ADVERTENCIA: GOOGLE_CLIENT_ID no está configurado")
    if not GOOGLE_CLIENT_SECRET:
        print("⚠️  ADVERTENCIA: GOOGLE_CLIENT_SECRET no está configurado")
    if not os.environ.get('API_GEMINI'):
        print("⚠️  ADVERTENCIA: API_GEMINI no está configurado")
    
    # Ejecutar servidor per Hugging Face
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Desactivar debug en producció
    )