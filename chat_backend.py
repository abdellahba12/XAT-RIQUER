import google.generativeai as genai
import requests
import tempfile
import os
import json
import logging
from typing import Dict, List, Optional
import re
from datetime import datetime
import time
from functools import wraps
import unicodedata

# Configuració de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuració de API
api_key = os.environ.get("API_GEMINI")
if not api_key:
    logger.warning("No se encontró API_GEMINI en las variables de entorno")
else:
    logger.info("✅ API_GEMINI encontrada")

genai.configure(api_key=api_key)

# LISTAR MODELOS DISPONIBLES AL INICIO
logger.info("=" * 80)
logger.info("📋 LISTANDO MODELOS DISPONIBLES:")
try:
    available_models = []
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            available_models.append(model.name)
            logger.info(f"  ✅ {model.name}")
    logger.info(f"Total modelos disponibles: {len(available_models)}")
except Exception as e:
    logger.error(f"❌ Error listando modelos: {e}")
    available_models = []
logger.info("=" * 80)

def normalize_name_to_email(name: str) -> str:
    """Normalitza un nom de professor a format d'email sense accents"""
    name = name.lower()
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    name = name.replace(' ', '.')
    name = ''.join(char for char in name if char.isalnum() or char == '.')
    return name

# Decorador per gestionar límits de peticions
def retry_with_exponential_backoff(
    max_retries=3,
    initial_delay=5,
    exponential_base=2,
    max_delay=60
):
    """Decorador que reintenta amb backoff exponencial si hi ha error 429"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Detectar error 429 o límit de quota
                    if any(keyword in error_str for keyword in ["429", "resource exhausted", "quota", "rate limit"]):
                        if attempt < max_retries:
                            wait_time = delay + (attempt * 0.5)
                            logger.warning(f"⚠️ Límit de peticions. Reintent {attempt + 1}/{max_retries} després de {wait_time:.1f}s")
                            time.sleep(wait_time)
                            delay = min(delay * exponential_base, max_delay)
                            continue
                        else:
                            logger.error(f"❌ Màxim de reintents assolit després de {max_retries} intents")
                            return "Ho sento molt, el sistema està temporalment saturat. Si us plau, espera uns segons i torna-ho a intentar. 🙏"
                    else:
                        logger.error(f"❌ Error inesperat: {e}")
                        raise
            
            return None
        return wrapper
    return decorator


class RiquerChatBot:
    def __init__(self):
        self.model = None
        self.chat = None
        self.file_contents = []
        self.request_count = 0
        self.last_request_time = 0
        self.initialize_directories()
        self.initialize_files()
        self.initialize_chat()
    
    def initialize_directories(self):
        """Crear directorios necesarios"""
        os.makedirs('drive_files', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
    def initialize_files(self):
        """Descarga els arxius CSV/TXT"""
        file_urls = [
            "https://drive.google.com/uc?export=download&id=1-Stsv68nDGxH2kDy_idcGM6FoXYMO3I8",
            "https://drive.google.com/uc?export=download&id=1kOjm0jHpF-LqtXYC7uUC1HJAV7DQPBsy",
            "https://drive.google.com/uc?export=download&id=1iMfgjXLrn51EkYhCqMejJT7K5M5J5Ezy",
            "https://drive.google.com/uc?export=download&id=1N7Xpt9JSr1JPoIaju-ekIRW4NGVgPxMU",
            "https://drive.google.com/uc?export=download&id=1neJFgTH0GWO5HbL64V6Fro0r1SKw8mFw",
        ]
        
        successful_downloads = 0
        
        for i, url in enumerate(file_urls):
            try:
                logger.info(f"Descargando archivo {i+1}/{len(file_urls)}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                if response.content.startswith(b'<!DOCTYPE html>'):
                    logger.warning(f"Archivo {i+1}: HTML recibido")
                    continue
                
                if len(response.content) < 100:
                    logger.warning(f"Archivo {i+1}: Muy pequeño")
                    continue
                
                try:
                    content = response.content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        content = response.content.decode('latin-1')
                    except:
                        content = response.content.decode('utf-8', errors='ignore')
                
                self.file_contents.append(f"\n--- Archivo {i+1} ---\n{content}")
                successful_downloads += 1
                logger.info(f"✅ Archivo {i+1} cargado")
                
            except Exception as e:
                logger.error(f"❌ Error archivo {i+1}: {str(e)}")
                continue
        
        logger.info(f"Archivos cargados: {successful_downloads}/{len(file_urls)}")
    
    def get_teachers_list(self) -> List[Dict]:
        """Obtiene la lista de profesores"""
        teachers = [
            {'name': 'Jordi Pipó', 'email': 'jordi.pipo@inscalaf.cat'},
            {'name': 'Anna Bresolí', 'email': 'anna.bresoli@inscalaf.cat'},
            {'name': 'Gerard Corominas', 'email': 'gerard.corominas@inscalaf.cat'},
            {'name': 'Natàlia Muñoz', 'email': 'natalia.munoz@inscalaf.cat'}
        ]
        return teachers
    
    def send_email(self, subject: str, body: str, recipients: List[str]) -> Dict:
        """Envía emails via Mailgun API"""
        try:
            mailgun_api_key = os.environ.get("MAILGUN_API_KEY")
            mailgun_domain = os.environ.get("MAILGUN_DOMAIN")
            
            if not mailgun_api_key or not mailgun_domain:
                logger.error("❌ Mailgun no configurado")
                return {"status": "error", "error": "Configuració de Mailgun no disponible"}
            
            data = {
                'from': 'Institut Alexandre de Riquer <riquer@inscalaf.cat>',
                'to': recipients,
                'subject': subject,
                'text': body
            }
            
            response = requests.post(
                f"https://api.mailgun.net/v3/{mailgun_domain}/messages",
                auth=("api", mailgun_api_key),
                data=data,
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Email enviado a: {recipients}")
                return {
                    "status": "success",
                    "subject": subject,
                    "body": body,
                    "sender": "riquer@inscalaf.cat",
                    "recipients": recipients,
                }
            else:
                logger.error(f"❌ Mailgun error: {response.status_code}")
                return {"status": "error", "error": f"Error enviant email: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Error enviando email: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def initialize_chat(self):
        """Inicializa SOLO el modelo, NO el chat (lazy initialization)"""
        try:
            logger.info("🔧 Configurando modelo Gemini...")
            
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # USAR EL MODELO CORRECTO CON PREFIJO
            # Opción 1: Gemini 1.5 Flash (más estable y disponible)
            model_name = 'models/gemini-1.5-flash-002'
            
            # Opción 2: Si quieres probar Gemini 2.0 (experimental)
            # model_name = 'models/gemini-2.0-flash-exp'
            
            logger.info(f"📦 Intentando cargar modelo: {model_name}")
            
            self.model = genai.GenerativeModel(
                model_name,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # CRÍTICO: NO inicializar el chat aquí
            self.chat = None
            
            logger.info(f"✅ Modelo '{model_name}' cargado correctamente")
            logger.info(f"📊 Chat: {self.chat is not None} (se inicializará con el primer mensaje)")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando modelo: {str(e)}")
            logger.error(f"💡 Intenta con un modelo diferente o verifica tu API key")
            self.model = None
            self.chat = None
    
    def _ensure_chat_initialized(self):
        """Inicializa el chat solo cuando se necesita (lazy)"""
        if self.chat is not None:
            logger.info("ℹ️ Chat ya inicializado")
            return
        
        logger.info("=" * 80)
        logger.info("🚀 INICIALIZANDO CHAT POR PRIMERA VEZ")
        logger.info("=" * 80)
        
        if self.model is None:
            raise Exception("Model no inicialitzat")
        
        context = f"""Ets Riquer, assistent virtual de l'Institut Alexandre de Riquer de Calaf.
        
        PERSONALITAT: Amable, proper, eficient. SEMPRE en CATALÀ.
        
        FUNCIONS:
        - Informar sobre l'institut (horaris, cursos, contactes)
        - Ajudar a contactar professors → suggereix botó "Sol·licitar reunió"
        - Justificar faltes → suggereix botó "Justificar falta"
        - Resoldre dubtes acadèmics i administratius
        
        CONTACTE:
        📍 C. Sant Joan Bta. de la Salle 6-8, 08280 Calaf
        📞 93 868 04 14
        📧 a8043395@xtec.cat
        📧 abdellahbaghalbachiri@gmail.com (consergeria)
        🌐 inscalaf.cat
        
        HORARIS:
        🏫 Classes: 8:00-14:35h
        🏢 Atenció: dilluns-divendres 8:00-14:00h
        📋 Secretaria: dilluns-divendres 9:00-13:00h
        
        CURSOS: ESO (1r-4t), Batxillerat (1r-2n), FP (GM i GS)
        
        REGLES:
        ✓ Respostes breus i clares
        ✓ Només info verificada dels arxius
        ✓ Si no saps algo → indica-ho clarament
        ✓ Emojis moderats (màx 2 per resposta)
        ✗ NO inventis informació
        ✗ NO temes aliens a l'institut
        
        INFORMACIÓ DELS ARXIUS DE L'INSTITUT:
        {"".join(self.file_contents) if self.file_contents else "No s'han pogut carregar els arxius"}
        
        Respon SEMPRE en CATALÀ. Sigues útil i directe."""
        
        try:
            self.chat = self.model.start_chat(
                history=[
                    {"role": "user", "parts": [context]},
                    {"role": "model", "parts": ["Entès! Sóc Riquer, l'assistent virtual de l'Institut Alexandre de Riquer. "
                                               "He processat tota la informació de l'institut. "
                                               "Puc ajudar-te amb qualsevol consulta sobre l'institut. "
                                               "En què et puc ajudar avui?"]}
                ]
            )
            
            logger.info("✅ Chat inicialitzat correctament")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando chat: {str(e)}")
            raise
    
    def _apply_rate_limit(self):
        """Aplica rate limiting: mínim 2 segons entre peticions"""
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < 2.0:
            wait_time = 2.0 - time_since_last
            logger.info(f"⏳ Rate limit: esperant {wait_time:.1f}s")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        logger.info(f"📊 Petició #{self.request_count}")
    
    @retry_with_exponential_backoff(max_retries=3, initial_delay=5)
    def _send_to_gemini(self, message: str) -> str:
        """Envia missatge a Gemini"""
        # Asegurar chat inicializado
        self._ensure_chat_initialized()
        
        if not self.chat:
            raise Exception("Chat no inicialitzat")
        
        # Rate limiting
        self._apply_rate_limit()
        
        response = self.chat.send_message(message)
        return response.text
    
    def process_message(self, message: str, user_data: Dict) -> str:
        """Procesa un mensaje del usuario"""
        try:
            full_message = f"""IMPORTANT: Respon NOMÉS en català.

Usuari: {user_data.get('nom', 'Desconegut')}
Pregunta: {message}

RECORDA: 
- Respon sempre en CATALÀ
- Sigues amable i professional"""
            
            # Verificar si es formulario
            if self._is_form_submission(message):
                return self._handle_form_submission(message, user_data)
            
            # Enviar a Gemini
            response_text = self._send_to_gemini(full_message)
            
            return self._format_response(response_text)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error procesando mensaje: {error_msg}")
            
            if "temporalment saturat" in error_msg.lower():
                return error_msg
            else:
                return "Ho sento, hi ha hagut un error. Si us plau, torna-ho a intentar. 🙏"
    
    def _is_form_submission(self, message: str) -> bool:
        """Detecta formularios"""
        form_keywords = ["Justificar falta - Alumne:", "Contactar professor", "- Assumpte:", "Missatge:"]
        return any(keyword in message for keyword in form_keywords)
    
    def _handle_form_submission(self, message: str, user_data: Dict) -> str:
        """Maneja formularios"""
        try:
            if "Justificar falta" in message:
                return self._handle_absence_form(message, user_data)
            elif "Contactar professor" in message:
                return self._handle_teacher_contact_form(message, user_data)
            else:
                return "No s'ha pogut processar el formulari."
        except Exception as e:
            logger.error(f"❌ Error formulario: {str(e)}")
            return f"⚠️ Error al processar el formulari: {str(e)}"
    
    def _handle_absence_form(self, message: str, user_data: Dict) -> str:
        """Procesa formulario de ausencias"""
        try:
            lines = message.split('\n')
            data = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('Justificar falta - Alumne:'):
                    parts = line.replace('Justificar falta - ', '').split(', ')
                    for part in parts:
                        if part.startswith('Alumne:'):
                            data['alumne'] = part.replace('Alumne:', '').strip()
                        elif part.startswith('Curs:'):
                            data['curs'] = part.replace('Curs:', '').strip()
                        elif part.startswith('Data:'):
                            data['data'] = part.replace('Data:', '').strip()
                        elif part.startswith('Motiu:'):
                            data['motiu'] = part.replace('Motiu:', '').strip()
            
            alumne = data.get('alumne', '').strip()
            curs = data.get('curs', '').strip()
            data_falta = data.get('data', '').strip()
            motiu = data.get('motiu', '').strip()
            
            if not all([alumne, curs, data_falta, motiu]):
                return "⚠️ Si us plau, completa tots els camps"
            
            subject = f"Justificació de falta - {alumne} ({curs})"
            body = f"""Benvolguts,

Sol·licito justificar la falta d'assistència següent:

Alumne/a: {alumne}
Curs: {curs}  
Data: {data_falta}
Motiu: {motiu}

Atentament,
{user_data.get('nom', 'Família')}
{user_data.get('contacte', '')}

---
Enviat des del sistema de l'Institut Alexandre de Riquer
{datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            result = self.send_email(subject, body, ["abdellahbaghalbachiri@gmail.com"])
            
            if result["status"] == "success":
                return f"✅ Justificació enviada!\n\nDestinatari: abdellahbaghalbachiri@gmail.com"
            else:
                return f"❌ Error.\n\nAlternatives:\n• Trucar: 93 868 04 14\n• Email: abdellahbaghalbachiri@gmail.com"
                
        except Exception as e:
            logger.error(f"❌ Error ausencia: {str(e)}")
            return f"⚠️ Error: {str(e)}"
    
    def _handle_teacher_contact_form(self, message: str, user_data: Dict) -> str:
        """Procesa formulario de contacto"""
        try:
            professor_name = ""
            subject = ""
            message_content = ""
            
            if "Contactar professor " in message:
                start = message.find("Contactar professor ") + len("Contactar professor ")
                end = message.find(" - Assumpte:", start)
                if end > start:
                    professor_name = message[start:end].strip()
            
            if "Assumpte: " in message:
                start = message.find("Assumpte: ") + len("Assumpte: ")
                end = message.find(",", start)
                if end == -1:
                    end = message.find("\n", start)
                if end == -1:
                    end = len(message)
                subject = message[start:end].strip()
            
            if "Missatge: " in message:
                start = message.find("Missatge: ") + len("Missatge: ")
                end = message.find(", Disponibilitat:", start)
                if end == -1:
                    end = len(message)
                message_content = message[start:end].strip()
            
            teacher = next((t for t in self.get_teachers_list() if t['name'] == professor_name), None)
            
            if teacher:
                professor_email = teacher['email']
            else:
                email_name = normalize_name_to_email(professor_name)
                professor_email = f"{email_name}@inscalaf.cat"
            
            logger.info(f"📧 Email: {professor_name} -> {professor_email}")
            
            email_subject = f"{subject} - {user_data.get('nom', 'Família')}"
            email_body = f"""Benvolgut/da {professor_name},

{message_content}

Atentament,
{user_data.get('nom', 'Família')}
{user_data.get('contacte', '')}

---
Enviat des del sistema de l'Institut Alexandre de Riquer
{datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            result = self.send_email(email_subject, email_body, [professor_email])
            
            if result["status"] == "success":
                return f"✅ Missatge enviat!\n\nDestinatari: {professor_email}"
            else:
                return f"❌ Error.\n\nAlternatives:\n• Trucar: 93 868 04 14\n• Email: {professor_email}"
                
        except Exception as e:
            logger.error(f"❌ Error contacto: {str(e)}")
            return f"⚠️ Error: {str(e)}"
    
    def _format_response(self, response: str) -> str:
        """Formatea respuesta"""
        response = response.replace('**', '').replace('*', '')
        if not response.endswith('\n'):
            response += '\n'
        return response.strip()
    
    def get_system_status(self) -> Dict:
        """Estado del sistema"""
        return {
            'chat_initialized': self.chat is not None,
            'model_available': self.model is not None,
            'files_loaded': len(self.file_contents),
            'api_key_configured': bool(os.environ.get("API_GEMINI")),
            'mailgun_configured': all([
                os.environ.get("MAILGUN_API_KEY"),
                os.environ.get("MAILGUN_DOMAIN")
            ]),
            'total_requests': self.request_count
        }
    
    def health_check(self) -> str:
        """Comprobación de salud"""
        status = self.get_system_status()
        
        report = "🔍 **Informe d'Estat**\n\n"
        
        if status['model_available']:
            report += "✅ Model: Operatiu\n"
        else:
            report += "❌ Model: Error\n"
        
        if status['chat_initialized']:
            report += "✅ Chat: Actiu\n"
        else:
            report += "⚪ Chat: Pendent\n"
        
        report += f"📁 Arxius: {status['files_loaded']}\n"
        report += f"{'✅' if status['api_key_configured'] else '❌'} API Gemini\n"
        report += f"{'✅' if status['mailgun_configured'] else '❌'} Mailgun\n"
        report += f"📊 Peticions: {status['total_requests']}\n"
        
        return report

# Crear instancia global
logger.info("=" * 80)
logger.info("🏗️ CREANDO BOT GLOBAL")
logger.info("=" * 80)
bot = RiquerChatBot()
logger.info("=" * 80)
logger.info("✅ BOT CREADO")
logger.info("=" * 80)

# Funciones de utilidad
def process_user_message(message: str, user_name: str, user_contact: str) -> str:
    user_data = {'nom': user_name, 'contacte': user_contact}
    return bot.process_message(message, user_data)

def get_system_health() -> str:
    return bot.health_check()

def get_teachers_for_form() -> List[Dict]:
    return bot.get_teachers_list()

def get_bot_status() -> Dict:
    return bot.get_system_status()
