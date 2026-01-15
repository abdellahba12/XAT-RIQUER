"""
XAT-RIQUER - Sistema de Xat Intel·ligent
Copyright © 2026 [Abdellah Baghal]. Tots els drets reservats.

Desenvolupat per: [Abdellah Baghal]
Institut: Alexandre de Riquer, Calaf

Aquest programari és propietat privada i està protegit per lleis de copyright.
"""



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
import unicodedata

# Configuració de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


logger.info(f"GEMINI_API_KEY valor real: {repr(os.getenv("API_GEMINI"))}")


# Configuració de API
api_key = os.environ.get("API_GEMINI")
if not api_key:
    logger.warning("No se encontró API_GEMINI en las variables de entorno")

genai.configure(api_key=api_key)

def normalize_name_to_email(name: str) -> str:
    """
    Normalitza un nom de professor a format d'email sense accents
    
    Exemples:
        'Jordi Pipó' -> 'jordi.pipo'
        'Anna Bresolí' -> 'anna.bresoli'
        'Natàlia Muñoz' -> 'natalia.munoz'
    """
    # Convertir a minúscules
    name = name.lower()
    
    # Normalitzar Unicode i eliminar diacrítics (accents)
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    
    # Substituir espais per punts
    name = name.replace(' ', '.')
    
    # Eliminar tots els caràcters que no siguin alfanumèrics o punts
    name = ''.join(char for char in name if char.isalnum() or char == '.')
    
    return name

# Configuració de API
api_key = os.environ.get("API_GEMINI")
if not api_key:
    logger.warning("No se encontró API_GEMINI en las variables de entorno")

genai.configure(api_key=api_key)

# Decorador per gestionar límits de peticions amb retry
def retry_with_exponential_backoff(
    max_retries=3,
    initial_delay=2,
    exponential_base=2,
    max_delay=32
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
                            wait_time = delay + (attempt * 0.5)  # Afegir jitter
                            logger.warning(f"⚠️ Límit de peticions assolit. Reintent {attempt + 1}/{max_retries} després de {wait_time:.1f}s")
                            time.sleep(wait_time)
                            delay = min(delay * exponential_base, max_delay)
                            continue
                        else:
                            logger.error(f"❌ Màxim de reintents assolit després de {max_retries} intents")
                            # Retornar missatge amigable
                            return "Ho sento molt, el sistema està temporalment saturat degut a l'alta demanda. Si us plau, espera uns segons i torna-ho a intentar. 🙏"
                    else:
                        # Si no és error 429, llançar immediatament
                        logger.error(f"Error inesperat: {e}")
                        raise
            
            return None
        return wrapper
    return decorator


class RiquerChatBot:
    def __init__(self):
        self.model = None
        self.chat = None
        self.file_contents = []  # Contingut dels arxius com a text
        self.request_count = 0  # Comptador de peticions
        self.initialize_directories()
        self.initialize_files()
        self.initialize_chat()
    
    def initialize_directories(self):
        """Crear directorios necesarios"""
        os.makedirs('drive_files', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
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
            {'name': 'Roger Codina', 'email': 'roger.codina@inscalaf.cat'}
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
                return {
                    "status": "error",
                    "error": f"Error enviant email: {response.status_code}"
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
            # Crear model amb configuració de seguretat relaxada
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
            
            self.model = genai.GenerativeModel(
                'gemini-2.5-flash',  # 30 RPM, 1M TPM - molt millor quota
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Contexto del sistema en catalán con los archivos como texto
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
            
            # Iniciar chat
            self.chat = self.model.start_chat(
                history=[
                    {
                        "role": "user", 
                        "parts": [context]
                    },
                    {
                        "role": "model", 
                        "parts": ["Entès! Sóc Riquer, l'assistent virtual de l'Institut Alexandre de Riquer. "
                                 "He processat tota la informació de l'institut. "
                                 "Puc ajudar-te amb qualsevol consulta sobre l'institut. "
                                 "En què et puc ajudar avui?"]
                    }
                ]
            )
            
            logger.info(f"✅ Chat inicializado con {len(self.file_contents)} archivos cargados")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando el chat: {str(e)}")
            self.model = None
            self.chat = None
    
    @retry_with_exponential_backoff(max_retries=1, initial_delay=3)
    def _send_to_gemini(self, message: str) -> str:
        """Envia missatge a Gemini amb gestió d'errors"""
        if not self.chat:
            raise Exception("Chat no inicialitzat")
        
        response = self.chat.send_message(message)
        return response.text
    
    def process_message(self, message: str, user_data: Dict) -> str:
        """Procesa un mensaje del usuario"""
        try:
            if not self.chat:
                return "Ho sento, hi ha hagut un problema tècnic. Si us plau, recarrega la pàgina."
            
            # Construir mensaje completo
            full_message = f"""IMPORTANT: Respon NOMÉS en català. Consulta la informació dels arxius per donar respostes precises.

Usuari: {user_data.get('nom', 'Desconegut')}
Pregunta: {message}

RECORDA: 
- Consulta SEMPRE la informació dels arxius abans de respondre
- Si la informació no està disponible, indica-ho clarament
- Respon sempre en CATALÀ
- Sigues amable i professional"""
            
            # Verificar si es un formulario
            if self._is_form_submission(message):
                return self._handle_form_submission(message, user_data)
            
            # Enviar a Gemini amb retry automàtic
            response_text = self._send_to_gemini(full_message)
            
            return self._format_response(response_text)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error procesando mensaje: {error_msg}")
            
            # Retornar missatge específic si és error de quota
            if "temporalment saturat" in error_msg.lower():
                return error_msg
            else:
                return "Ho sento, hi ha hagut un error processant la teva consulta. Si us plau, torna-ho a intentar en uns segons. 🙏"
    
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
Enviat automàticament des del sistema de l'Institut Alexandre de Riquer
{datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            # Intentar enviar email
            result = self.send_email(subject, body, ["abdellahbaghalbachiri@gmail.com"])
            
            if result["status"] == "success":
                return f"✅ Justificació enviada correctament!\n\nDestinatari: abdellahbaghalbachiri@gmail.com\n\nEn breu rebràs confirmació de recepció."
            else:
                return f"❌ Error al enviar la justificació.\n\nAlternatives:\n• Trucar al 93 868 04 14\n• Enviar email manualment a abdellahbaghalbachiri@gmail.com"
                
        except Exception as e:
            logger.error(f"Error en justificació: {str(e)}")
            return f"⚠️ Error al processar la justificació: {str(e)}"
    
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
            
            # Buscar email del professor a la llista
            teacher = next((t for t in self.get_teachers_list() if t['name'] == professor_name), None)
            
            if teacher:
                # Usar email de la llista (ja està sense accents)
                professor_email = teacher['email']
            else:
                # Generar email automàticament (eliminar accents)
                email_name = normalize_name_to_email(professor_name)
                professor_email = f"{email_name}@inscalaf.cat"
            
            logger.info(f"📧 Email generat: {professor_name} -> {professor_email}")
            
            # Construir email
            email_subject = f"{subject} - {user_data.get('nom', 'Família')}"
            email_body = f"""Benvolgut/da {professor_name},

{message_content}

Atentament,
{user_data.get('nom', 'Família')}
{user_data.get('contacte', '')}

---
Enviat automàticament des del sistema de l'Institut Alexandre de Riquer
{datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            # Intentar enviar email
            result = self.send_email(email_subject, email_body, [professor_email])
            
            if result["status"] == "success":
                return f"✅ Missatge enviat correctament!\n\nDestinatari: {professor_email}\n\nEl professor/a rebrà el teu missatge i et respondrà al teu correu."
            else:
                return f"❌ Error al enviar el missatge.\n\nAlternatives:\n• Trucar al 93 868 04 14\n• Enviar email directament a {professor_email}"
                
        except Exception as e:
            logger.error(f"Error contactando profesor: {str(e)}")
            return f"⚠️ Error al contactar amb el professor: {str(e)}"
    
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
            ]),
            'total_requests': self.request_count
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
        health_report += f"📊 Total peticions: {status['total_requests']}\n"
        
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

# Copyright (c) 2026 Abdellah Baghal. Todos los derechos reservados.
