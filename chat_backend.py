import google.generativeai as genai
import requests
import os
import logging
from typing import Dict, List
import time
from functools import wraps
import unicodedata
from datetime import datetime

# Configuració de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuració de API
api_key = os.environ.get("API_GEMINI")
if not api_key:
    logger.error("❌ API_GEMINI no configurada")
else:
    logger.info("✅ API_GEMINI trobada")

genai.configure(api_key=api_key)

# MODEL ACTUALITZAT - Gemini 1.5 Flash (millor quota gratuïta)
MODEL_NAME = "gemini-1.5-flash"

def normalize_name_to_email(name: str) -> str:
    """Normalitza nom a email"""
    name = name.lower()
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    name = name.replace(' ', '.')
    name = ''.join(char for char in name if char.isalnum() or char == '.')
    return name

def retry_with_exponential_backoff(max_retries=2, initial_delay=3, exponential_base=2, max_delay=30):
    """Decorador retry amb backoff exponencial"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    if any(k in error_str for k in ["429", "resource exhausted", "quota", "rate limit"]):
                        if attempt < max_retries:
                            wait_time = delay + (attempt * 0.5)
                            logger.warning(f"⚠️ Límit. Reintent {attempt + 1}/{max_retries} en {wait_time:.1f}s")
                            time.sleep(wait_time)
                            delay = min(delay * exponential_base, max_delay)
                            continue
                        else:
                            logger.error(f"❌ Màxim reintents assolit")
                            return "Ho sento, sistema saturat. Espera uns segons i torna-ho a intentar. 🙏"
                    else:
                        logger.error(f"❌ Error: {e}")
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
        os.makedirs('drive_files', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
    def initialize_files(self):
        file_urls = [
            "https://drive.google.com/uc?export=download&id=1-Stsv68nDGxH2kDy_idcGM6FoXYMO3I8",
            "https://drive.google.com/uc?export=download&id=1kOjm0jHpF-LqtXYC7uUC1HJAV7DQPBsy",
            "https://drive.google.com/uc?export=download&id=1iMfgjXLrn51EkYhCqMejJT7K5M5J5Ezy",
            "https://drive.google.com/uc?export=download&id=1N7Xpt9JSr1JPoIaju-ekIRW4NGVgPxMU",
            "https://drive.google.com/uc?export=download&id=1neJFgTH0GWO5HbL64V6Fro0r1SKw8mFw",
        ]
        
        successful = 0
        for i, url in enumerate(file_urls):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                if response.content.startswith(b'<!DOCTYPE html>') or len(response.content) < 100:
                    continue
                
                try:
                    content = response.content.decode('utf-8')
                except:
                    try:
                        content = response.content.decode('latin-1')
                    except:
                        content = response.content.decode('utf-8', errors='ignore')
                
                self.file_contents.append(f"\n--- Archivo {i+1} ---\n{content}")
                successful += 1
            except Exception as e:
                logger.error(f"Error archivo {i+1}: {e}")
        
        logger.info(f"📁 Arxius carregats: {successful}/{len(file_urls)}")
    
    def get_teachers_list(self) -> List[Dict]:
        return [
            {'name': 'Jordi Pipó', 'email': 'jordi.pipo@inscalaf.cat'},
            {'name': 'Anna Bresolí', 'email': 'anna.bresoli@inscalaf.cat'},
            {'name': 'Gerard Corominas', 'email': 'gerard.corominas@inscalaf.cat'},
            {'name': 'Natàlia Muñoz', 'email': 'natalia.munoz@inscalaf.cat'}
        ]
    
    def send_email(self, subject: str, body: str, recipients: List[str]) -> Dict:
        try:
            mailgun_api_key = os.environ.get("MAILGUN_API_KEY")
            mailgun_domain = os.environ.get("MAILGUN_DOMAIN")
            
            if not mailgun_api_key or not mailgun_domain:
                return {"status": "error", "error": "Mailgun no disponible"}
            
            response = requests.post(
                f"https://api.mailgun.net/v3/{mailgun_domain}/messages",
                auth=("api", mailgun_api_key),
                data={
                    'from': 'Institut Alexandre de Riquer <riquer@inscalaf.cat>',
                    'to': recipients,
                    'subject': subject,
                    'text': body
                },
                timeout=15
            )
            
            if response.status_code == 200:
                return {"status": "success", "subject": subject, "recipients": recipients}
            else:
                return {"status": "error", "error": f"Error {response.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def initialize_chat(self):
        """Inicialitza el chat amb Gemini - MODEL ACTUALITZAT"""
        try:
            logger.info(f"🚀 Inicialitzant model: {MODEL_NAME}")
            
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
            
            # USAR MODEL FIX - sense buscar automàticament
            self.model = genai.GenerativeModel(
                MODEL_NAME,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Context del sistema
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
            
            # Iniciar chat amb historial
            self.chat = self.model.start_chat(
                history=[
                    {"role": "user", "parts": [context]},
                    {"role": "model", "parts": ["Entès! Sóc Riquer, l'assistent virtual de l'Institut Alexandre de Riquer. En què et puc ajudar?"]}
                ]
            )
            
            logger.info(f"✅ Chat inicialitzat correctament amb {MODEL_NAME}")
            
        except Exception as e:
            logger.error(f"❌ Error inicialitzant chat: {e}")
            self.model = None
            self.chat = None
    
    def _apply_rate_limit(self):
        """Rate limiting manual: mínim 2 segons entre peticions"""
        now = time.time()
        if now - self.last_request_time < 2.0:
            time.sleep(2.0 - (now - self.last_request_time))
        self.last_request_time = time.time()
        self.request_count += 1
    
    @retry_with_exponential_backoff(max_retries=2, initial_delay=3)
    def _send_to_gemini(self, message: str) -> str:
        """Envia missatge a Gemini"""
        if not self.chat:
            raise Exception("Chat no inicialitzat")
        
        self._apply_rate_limit()
        response = self.chat.send_message(message)
        return response.text
    
    def process_message(self, message: str, user_data: Dict) -> str:
        """Procesa un missatge de l'usuari"""
        try:
            if not self.chat:
                return "Ho sento, hi ha hagut un problema tècnic. Si us plau, recarrega la pàgina."
            
            # Verificar si és formulari
            if self._is_form_submission(message):
                return self._handle_form_submission(message, user_data)
            
            # Construir missatge
            full_message = f"""Usuari: {user_data.get('nom', 'Desconegut')}
Pregunta: {message}

Respon en CATALÀ, breu i directe."""
            
            response_text = self._send_to_gemini(full_message)
            
            if response_text:
                return self._format_response(response_text)
            else:
                return "Ho sento, no he pogut processar la teva consulta. Torna-ho a intentar."
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return "Ho sento, hi ha hagut un error. Torna-ho a intentar. 🙏"
    
    def _is_form_submission(self, message: str) -> bool:
        return any(k in message for k in ["Justificar falta", "Contactar professor"])
    
    def _handle_form_submission(self, message: str, user_data: Dict) -> str:
        if "Justificar falta" in message:
            return self._handle_absence_form(message, user_data)
        elif "Contactar professor" in message:
            return self._handle_teacher_contact_form(message, user_data)
        return "No processat"
    
    def _handle_absence_form(self, message: str, user_data: Dict) -> str:
        """Procesa formulari de faltes"""
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
                return "⚠️ Si us plau, completa tots els camps requerits"
            
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
            
            result = self.send_email(subject, body, ["abdellahbaghalbachiri@gmail.com"])
            
            if result["status"] == "success":
                return f"✅ Justificació enviada correctament!"
            else:
                return f"❌ Error al enviar. Truca al 93 868 04 14"
                
        except Exception as e:
            logger.error(f"Error en justificació: {e}")
            return f"⚠️ Error al processar la justificació"
    
    def _handle_teacher_contact_form(self, message: str, user_data: Dict) -> str:
        """Procesa formulari de contacte amb professor"""
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
            
            email_subject = f"{subject} - {user_data.get('nom', 'Família')}"
            email_body = f"""Benvolgut/da {professor_name},

{message_content}

Atentament,
{user_data.get('nom', 'Família')}
{user_data.get('contacte', '')}

---
Enviat automàticament des del sistema de l'Institut Alexandre de Riquer
{datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            result = self.send_email(email_subject, email_body, [professor_email])
            
            if result["status"] == "success":
                return f"✅ Missatge enviat a {professor_email}!"
            else:
                return f"❌ Error al enviar. Email directe: {professor_email}"
                
        except Exception as e:
            logger.error(f"Error contactant professor: {e}")
            return f"⚠️ Error al contactar amb el professor"
    
    def _format_response(self, response: str) -> str:
        response = response.replace('**', '').replace('*', '')
        return response.strip()
    
    def get_system_status(self) -> Dict:
        return {
            'chat_initialized': self.chat is not None,
            'model_available': self.model is not None,
            'model_name': MODEL_NAME,
            'files_loaded': len(self.file_contents),
            'total_requests': self.request_count
        }


# Crear instància global
bot = RiquerChatBot()
