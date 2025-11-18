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

# Configuració de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuració de API
api_key = os.environ.get("API_GEMINI")
if not api_key:
    logger.warning("No se encontró API_GEMINI en las variables de entorno")

genai.configure(api_key=api_key)

# Decorator per manejar rate limiting
def retry_on_rate_limit(max_retries=3, base_delay=2):
    """Decorator que reintenta crides quan hi ha rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    # Detectar errors de rate limit
                    if '429' in error_msg or 'quota' in error_msg or 'rate' in error_msg or 'exhausted' in error_msg:
                        if attempt < max_retries - 1:
                            # Exponential backoff
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Rate limit detectat. Reintentant en {delay}s... (intent {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(f"Rate limit exhaustit després de {max_retries} intents")
                            raise Exception("El servei està temporalment saturat. Si us plau, espera uns segons i torna-ho a intentar.")
                    else:
                        # Altre tipus d'error
                        raise
            
            return None
        return wrapper
    return decorator

class RiquerChatBot:
    def __init__(self):
        self.model = None
        self.chat = None
        self.file_contents = []  # Contingut dels arxius com a text
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Mínim 1 segon entre requests
        self.initialize_directories()
        self.initialize_files()
        self.initialize_chat()
    
    def initialize_directories(self):
        """Crear directorios necesarios"""
        os.makedirs('drive_files', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
    def _rate_limit_check(self):
        """Comprova i aplica rate limiting manual"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.info(f"Rate limiting: esperant {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def initialize_files(self):
        """Descarga els arxius CSV/TXT i els guarda com a text"""
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
                logger.info(f"Descargando archivo {i+1} de {len(file_urls)}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                # Verificar si es una página HTML de error
                if response.content.startswith(b'<!DOCTYPE html>'):
                    logger.warning(f"Archivo {i+1}: Recibido HTML en lugar del archivo")
                    continue
                
                # Verificar tamaño mínimo
                if len(response.content) < 100:
                    logger.warning(f"Archivo {i+1}: Tamaño muy pequeño ({len(response.content)} bytes)")
                    continue
                
                # Intentar decodificar el contenido
                try:
                    content = response.content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        content = response.content.decode('latin-1')
                    except:
                        content = response.content.decode('utf-8', errors='ignore')
                
                # Guardar contenido
                self.file_contents.append(f"\n--- Archivo {i+1} ---\n{content}")
                successful_downloads += 1
                logger.info(f"Archivo {i+1} cargado correctamente")
                
            except Exception as e:
                logger.error(f"Error cargando archivo {url}: {str(e)}")
                continue
        
        logger.info(f"Archivos cargados exitosamente: {successful_downloads}/{len(file_urls)}")
    
    def get_teachers_list(self) -> List[Dict]:
        """Obtiene la lista de profesores para el formulario"""
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
                logger.error("Faltan variables de Mailgun")
                return {
                    "status": "error",
                    "error": "Configuració de Mailgun no disponible"
                }
            
            data = {
                'from': 'Institut Alexandre de Riquer <riquer@inscalaf.cat>',
                'to': recipients,
                'subject': subject,
                'text': body
            }
            
            # Enviar via Mailgun API
            response = requests.post(
                f"https://api.mailgun.net/v3/{mailgun_domain}/messages",
                auth=("api", mailgun_api_key),
                data=data,
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info(f"Correo enviado correctamente a: {recipients}")
                return {
                    "status": "success",
                    "subject": subject,
                    "body": body,
                    "sender": "riquer@inscalaf.cat",
                    "recipients": recipients,
                }
            else:
                logger.error(f"Mailgun error: {response.status_code} - {response.text}")
                
                # Missatge d'error més específic
                if response.status_code == 403:
                    error_detail = "El compte de Mailgun requereix verificació. Contacta amb l'administrador."
                else:
                    error_detail = f"Error enviant email: {response.status_code}"
                
                return {
                    "status": "error",
                    "error": error_detail
                }
                
        except Exception as e:
            logger.error(f"Error enviando correo: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def initialize_chat(self):
        """Inicializa el chat con Gemini"""
        try:
            # Crear model amb configuració de generació més conservadora
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            self.model = genai.GenerativeModel(
                'gemini-2.0-flash-exp',  # Usar modelo experimental más rápido
                generation_config=generation_config
            )
            
            # Contexto del sistema en catalán con los archivos como texto (versión comprimida)
            context = f"""
            Ets Riquer, l'assistent virtual de l'Institut Alexandre de Riquer de Calaf.
            Ets amable, professional i eficient. SEMPRE respon en CATALÀ.
            Dona respostes curtes sempre que sigui possible.
            
            REGLES IMPORTANTS:
            1. Sempre respon en CATALÀ
            2. Només respon preguntes relacionades amb l'institut
            3. Per contactar amb professors, ajuda a preparar un correu
            4. Per justificar absències, envia a 'abdellahbaghalbachiri@gmail.com'
            5. Sigues concís però complet
            6. Utilitza emojis moderadament
            7. NOMÉS utilitza informació dels arxius de l'institut
            8. Si no trobes informació, explica que no està disponible
            
            INFORMACIÓ DE L'INSTITUT:
            - Nom: Institut Alexandre de Riquer
            - Adreça: C. Sant Joan Bta. de la Salle 6-8, 08280 Calaf
            - Telèfon: 93 868 04 14
            - Email: a8043395@xtec.cat
            - Web: http://www.inscalaf.cat
            - Consergeria: abdellahbaghalbachiri@gmail.com
            
            HORARIS:
            - Escolar: 8:00 a 14:35
            - Atenció pública: dilluns a divendres 8:00-14:00h
            
            CURSOS: ESO, Batxillerat, Formació Professional
            
            {"".join(self.file_contents[:2]) if self.file_contents else "Arxius no disponibles"}
            """
            
            # Iniciar chat
            self.chat = self.model.start_chat(
                history=[
                    {
                        "role": "user", 
                        "parts": [context]
                    },
                    {
                        "role": "model", 
                        "parts": ["Entès! Sóc Riquer. Puc ajudar-te amb qualsevol consulta sobre l'institut. En què et puc ajudar?"]
                    }
                ]
            )
            
            logger.info(f"Chat inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando el chat: {str(e)}")
            self.model = None
            self.chat = None
    
    @retry_on_rate_limit(max_retries=3, base_delay=2)
    def _send_message_with_retry(self, message: str) -> str:
        """Envia missatge amb retry logic"""
        self._rate_limit_check()  # Rate limiting manual
        
        response = self.chat.send_message(message)
        return response.text
    
    def process_message(self, message: str, user_data: Dict) -> str:
        """Procesa un mensaje del usuario"""
        try:
            if not self.chat:
                return "Ho sento, hi ha hagut un problema tècnic. Si us plau, recarrega la pàgina."
            
            # Construir mensaje completo (més curt)
            full_message = f"""CATALÀ: Respon NOMÉS en català.

Usuari: {user_data.get('nom', 'Desconegut')}
Pregunta: {message}

Sigues breu i directe."""
            
            # Verificar si es un formulario
            if self._is_form_submission(message):
                return self._handle_form_submission(message, user_data)
            
            # Enviar a Gemini amb retry
            try:
                response_text = self._send_message_with_retry(full_message)
                return self._format_response(response_text)
            except Exception as e:
                error_msg = str(e).lower()
                if 'saturat' in error_msg or 'rate' in error_msg or '429' in error_msg:
                    return "⏳ El servei està temporalment saturat. Si us plau, espera uns segons i torna-ho a intentar."
                else:
                    logger.error(f"Error en Gemini API: {str(e)}")
                    return "Ho sento, hi ha hagut un error temporal. Si us plau, torna-ho a intentar en uns segons."
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            return "Ho sento, hi ha hagut un error processant la teva consulta. Si us plau, torna-ho a intentar."
    
    def _is_form_submission(self, message: str) -> bool:
        """Detecta si el mensaje es un formulario"""
        form_keywords = [
            "Justificar falta - Alumne:",
            "Contactar professor",
            "- Assumpte:",
            "Missatge:"
        ]
        return any(keyword in message for keyword in form_keywords)
    
    def _handle_form_submission(self, message: str, user_data: Dict) -> str:
        """Controla els formularis i envia mails"""
        try:
            if "Justificar falta" in message:
                return self._handle_absence_form(message, user_data)
            elif "Contactar professor" in message:
                return self._handle_teacher_contact_form(message, user_data)
            else:
                return "No s'ha pogut processar el formulari. Si us plau, torna-ho a intentar."
        except Exception as e:
            logger.error(f"Error manejando formulario: {str(e)}")
            return f"⚠️ Error al processar el formulari: {str(e)}"
    
    def _handle_absence_form(self, message: str, user_data: Dict) -> str:
        """Procesa el formulari de faltes"""
        try:
            # Extreure dades
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
            
            # Validar dades
            if not all([alumne, curs, data_falta, motiu]):
                return "⚠️ Si us plau, completa tots els camps requerits"
            
            # Construir mail
            subject = f"Justificació de falta - {alumne} ({curs})"
            body = f"""Benvolguts,

Sol·licito justificar la falta d'assistència següent:

Alumne/a: {alumne}
Curs: {curs}  
Data de la falta: {data_falta}
Motiu: {motiu}

Atentament,
{user_data.get('nom', 'Família')}
Contacte: {user_data.get('contacte', '')}

---
Enviat des del sistema de l'Institut Alexandre de Riquer
{datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            # Intentar enviar email
            result = self.send_email(subject, body, ["abdellahbaghalbachiri@gmail.com"])
            
            if result["status"] == "success":
                return f"✅ Justificació enviada correctament!\n\nDestinatari: abdellahbaghalbachiri@gmail.com\n\nEn breu rebràs confirmació."
            else:
                return f"❌ No s'ha pogut enviar automàticament.\n\n💡 Alternatives:\n• Trucar: 93 868 04 14\n• Email: abdellahbaghalbachiri@gmail.com\n\nMotiu tècnic: {result.get('error', 'Error desconegut')}"
                
        except Exception as e:
            logger.error(f"Error en justificació: {str(e)}")
            return f"⚠️ Error al processar la justificació. Si us plau, contacta directament amb l'institut."
    
    def _handle_teacher_contact_form(self, message: str, user_data: Dict) -> str:
        """Procesa el formulario de contacto con profesor"""
        try:
            # Extreure dades
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
            
            # Validar dades
            if not all([professor_name, subject, message_content]):
                return "⚠️ Si us plau, completa tots els camps requerits"
            
            # Generar email del professor
            email_name = professor_name.lower().replace(' ', '.')
            professor_email = f"{email_name}@inscalaf.cat"
            
            # Construir email
            email_subject = f"{subject} - {user_data.get('nom', 'Família')}"
            email_body = f"""Benvolgut/da {professor_name},

{message_content}

Atentament,
{user_data.get('nom', 'Família')}
{user_data.get('contacte', '')}

---
Enviat des del sistema de l'Institut Alexandre de Riquer
{datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            # Intentar enviar email
            result = self.send_email(email_subject, email_body, [professor_email])
            
            if result["status"] == "success":
                return f"✅ Missatge enviat correctament!\n\nDestinatari: {professor_email}\n\nEl professor/a rebrà el teu missatge."
            else:
                return f"❌ No s'ha pogut enviar automàticament.\n\n💡 Alternatives:\n• Trucar: 93 868 04 14\n• Email directe: {professor_email}\n\nMotiu tècnic: {result.get('error', 'Error desconegut')}"
                
        except Exception as e:
            logger.error(f"Error contactando profesor: {str(e)}")
            return f"⚠️ Error al contactar amb el professor. Si us plau, prova més tard o contacta directament."
    
    def _format_response(self, response: str) -> str:
        """Formatea la respuesta para mejorar la presentación"""
        # Eliminar asteriscos de formato markdown
        response = response.replace('**', '')
        response = response.replace('*', '')
        
        # Asegurar salto de línea al final
        if not response.endswith('\n'):
            response += '\n'
        
        return response.strip()
    
    def get_system_status(self) -> Dict:
        """Estado del sistema"""
        status = {
            'chat_initialized': self.chat is not None,
            'model_available': self.model is not None,
            'files_loaded': len(self.file_contents),
            'api_key_configured': bool(os.environ.get("API_GEMINI")),
            'mailgun_configured': all([
                os.environ.get("MAILGUN_API_KEY"),
                os.environ.get("MAILGUN_DOMAIN")
            ])
        }
        
        return status
    
    def health_check(self) -> str:
        """Comprobación de salud del sistema"""
        status = self.get_system_status()
        
        health_report = "🔍 **Informe d'Estat del Sistema**\n\n"
        
        # Estado del chat
        if status['chat_initialized'] and status['model_available']:
            health_report += "✅ Chat: Operatiu\n"
        else:
            health_report += "❌ Chat: Error d'inicialització\n"
        
        # Archivos
        health_report += f"📁 Arxius carregats: {status['files_loaded']}\n"
        
        # Configuración
        health_report += f"{'✅' if status['api_key_configured'] else '❌'} API Gemini: {'Configurada' if status['api_key_configured'] else 'No configurada'}\n"
        health_report += f"{'✅' if status['mailgun_configured'] else '❌'} Mailgun: {'Configurat' if status['mailgun_configured'] else 'No configurat'}\n"
        
        return health_report

# Crear instancia global
bot = RiquerChatBot()

# Funciones de utilidad para Flask
def process_user_message(message: str, user_name: str, user_contact: str) -> str:
    """Procesa mensajes para la interfaz Flask"""
    user_data = {
        'nom': user_name,
        'contacte': user_contact
    }
    return bot.process_message(message, user_data)

def get_system_health() -> str:
    """Obtiene el estado de salud del sistema"""
    return bot.health_check()

def get_teachers_for_form() -> List[Dict]:
    """Obtiene la lista de profesores para formularios"""
    return bot.get_teachers_list()

def get_bot_status() -> Dict:
    """Obtiene el estado detallado del bot"""
    return bot.get_system_status()
