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
import unicodedata  # <-- AFEGIT

# Configuració de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_email_name(name: str) -> str:
    """Normalitza un nom per convertir-lo en un correu sense accents ni caràcters especials"""
    nfkd = unicodedata.normalize('NFKD', name)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    clean = no_accents.lower().replace(" ", ".")
    clean = re.sub(r"[^a-z.]", "", clean)
    return clean
# -------------------------------------------------------

# Configuració de API
api_key = os.environ.get("API_GEMINI")
if not api_key:
    logger.warning("No se encontró API_GEMINI en las variables de entorno")

genai.configure(api_key=api_key)

class RiquerChatBot:
    def __init__(self):
        self.model = None
        self.chat = None
        self.file_contents = []
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
        
        successful_downloads = 0
        
        for i, url in enumerate(file_urls):
            try:
                logger.info(f"Descargando archivo {i+1} de {len(file_urls)}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                if response.content.startswith(b'<!DOCTYPE html>'):
                    logger.warning(f"Archivo {i+1}: Recibido HTML en lugar del archivo")
                    continue
                
                if len(response.content) < 100:
                    logger.warning(f"Archivo {i+1}: Tamaño muy pequeño ({len(response.content)} bytes)")
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
                logger.info(f"Archivo {i+1} cargado correctamente")
                
            except Exception as e:
                logger.error(f"Error cargando archivo {url}: {str(e)}")
                continue
        
        logger.info(f"Archivos cargados exitosamente: {successful_downloads}/{len(file_urls)}")
    
    def get_teachers_list(self) -> List[Dict]:
        teachers = [
            {'name': 'Jordi Pipó', 'email': 'jordi.pipo@inscalaf.cat'},
            {'name': 'Anna Bresolí', 'email': 'anna.bresoli@inscalaf.cat'},
            {'name': 'Gerard Corominas', 'email': 'gerard.corominas@inscalaf.cat'},
            {'name': 'Natàlia Muñoz', 'email': 'natalia.munoz@inscalaf.cat'}
        ]
        return teachers
    
    def send_email(self, subject: str, body: str, recipients: List[str]) -> Dict:
        try:
            mailgun_api_key = os.environ.get("MAILGUN_API_KEY")
            mailgun_domain = os.environ.get("MAILGUN_DOMAIN")
            
            if not mailgun_api_key or not mailgun_domain:
                logger.error("Faltan variables de Mailgun")
                return {
                    "status": "error",
                    "error": "Configuració de Mailgun no disponible"
                }
            
            is_sandbox = "sandbox" in mailgun_domain.lower()
            
            authorized_recipients = [
                "abdellahbaghalbachiri@gmail.com",
                "anna.bresoli@inscalaf.cat",
                "gerard.corominas@inscalaf.cat",
                "jordi.pipo@inscalaf.cat"
            ]
            
            if is_sandbox:
                valid_recipients = [r for r in recipients if r in authorized_recipients]
                if not valid_recipients:
                    return {
                        "status": "error",
                        "error": "Domini sandbox: el destinatari no està autoritzat",
                        "info": "Afegeix el destinatari a la llista d'autoritzats"
                    }
                recipients = valid_recipients
            
            data = {
                'from': f'Institut Alexandre de Riquer <noreply@{mailgun_domain}>',
                'to': recipients,
                'subject': subject,
                'text': body,
                'h:Reply-To': 'info@inscalaf.cat'
            }
            
            response = requests.post(
                f"https://api.mailgun.net/v3/{mailgun_domain}/messages",
                auth=("api", mailgun_api_key),
                data=data,
                timeout=15
            )
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "subject": subject,
                    "body": body,
                    "sender": f"noreply@{mailgun_domain}",
                    "recipients": recipients,
                }
            else:
                return {
                    "status": "error",
                    "error": f"Error enviant email ({response.status_code})"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def initialize_chat(self):
        try:
            self.model = genai.GenerativeModel(
                'gemini-2.0-flash-exp',
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
            )
            
            context = f"""
            Ets Riquer, l'assistent virtual de l'Institut Alexandre de Riquer de Calaf.
            ... (CONTINGUT DEL SISTEMA IGUAL)
            {"".join(self.file_contents) if self.file_contents else "No s'han pogut carregar els arxius"}
            """
            
            self.chat = self.model.start_chat(
                history=[
                    {
                        "role": "user", 
                        "parts": [context]
                    },
                    {
                        "role": "model", 
                        "parts": ["Entès! Sóc Riquer, l'assistent virtual..."]
                    }
                ]
            )
            
        except Exception as e:
            logger.error(f"Error inicializando el chat: {str(e)}")
            self.model = None
            self.chat = None
    
    def process_message(self, message: str, user_data: Dict) -> str:
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if not self.chat:
                    return "Ho sento, hi ha hagut un problema tècnic."
                
                full_message = f"""IMPORTANT: Respon NOMÉS en català...

Usuari: {user_data.get('nom', 'Desconegut')}
Pregunta: {message}
"""
                
                if self._is_form_submission(message):
                    return self._handle_form_submission(message, user_data)
                
                response = self.chat.send_message(full_message)
                return self._format_response(response.text)
                
            except Exception as e:
                if "429" in str(e):
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return "Ho sento, hi ha hagut un error processant la teva consulta."
        
        return "Ho sento, no he pogut processar la teva consulta."
    
    def _is_form_submission(self, message: str) -> bool:
        form_keywords = [
            "Justificar falta - Alumne:",
            "Contactar professor",
            "- Assumpte:",
            "Missatge:"
        ]
        return any(keyword in message for keyword in form_keywords)
    
    def _handle_form_submission(self, message: str, user_data: Dict) -> str:
        try:
            if "Justificar falta" in message:
                return self._handle_absence_form(message, user_data)
            elif "Contactar professor" in message:
                return self._handle_teacher_contact_form(message, user_data)
            else:
                return "No s'ha pogut processar el formulari."
        except Exception as e:
            return f"⚠️ Error al processar el formulari: {str(e)}"
    
    def _handle_absence_form(self, message: str, user_data: Dict) -> str:
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
                return "⚠️ Si us plau, completa tots els camps."
            
            subject = f"Justificació de falta - {alumne} ({curs})"
            body = f"""Benvolguts,

Sol·licito justificar la falta d'assistència:

Alumne/a: {alumne}
Curs: {curs}
Data: {data_falta}
Motiu: {motiu}

Atentament,
{user_data.get('nom', 'Família')}
{user_data.get('contacte', '')}
"""
            
            result = self.send_email(subject, body, ["abdellahbaghalbachiri@gmail.com"])
            
            if result["status"] == "success":
                return "✅ Justificació enviada correctament!"
            else:
                return f"❌ Error: {result['error']}"
                
        except Exception as e:
            return f"⚠️ Error al processar la justificació: {str(e)}"
    
    def _handle_teacher_contact_form(self, message: str, user_data: Dict) -> str:
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
                end = len(message)
                message_content = message[start:end].strip()
            
            if not all([professor_name, subject, message_content]):
                return "⚠️ Si us plau, completa tots els camps."
            
            # -------------------------------------------------------
            # ÚS DE LA FUNCIÓ QUE TREU ACCENTS
            # -------------------------------------------------------
            email_name = normalize_email_name(professor_name)
            professor_email = f"{email_name}@inscalaf.cat"
            # -------------------------------------------------------
            
            email_subject = f"{subject} - {user_data.get('nom', 'Família')}"
            email_body = f"""Benvolgut/da {professor_name},

{message_content}

Atentament,
{user_data.get('nom', 'Família')}
{user_data.get('contacte', '')}
"""
            
            result = self.send_email(email_subject, email_body, [professor_email])
            
            if result["status"] == "success":
                return f"✅ Missatge enviat correctament a {professor_email}!"
            else:
                return f"❌ Error: {result['error']}"
                
        except Exception as e:
            return f"⚠️ Error: {str(e)}"
    
    def _format_response(self, response: str) -> str:
        response = response.replace('**', '')
        response = response.replace('*', '')
        return response.strip()
    
    def get_system_status(self) -> Dict:
        return {
            'chat_initialized': self.chat is not None,
            'model_available': self.model is not None,
            'files_loaded': len(self.file_contents),
            'api_key_configured': bool(os.environ.get("API_GEMINI")),
            'mailgun_configured': all([
                os.environ.get("MAILGUN_API_KEY"),
                os.environ.get("MAILGUN_DOMAIN")
            ])
        }
    
    def health_check(self) -> str:
        status = self.get_system_status()
        health_report = "🔍 Estat del Sistema\n\n"
        health_report += f"Chat: {'OK' if status['chat_initialized'] else 'ERROR'}\n"
        health_report += f"Arxius: {status['files_loaded']}\n"
        return health_report

# Instància global
bot = RiquerChatBot()

# Funcions per Flask
def process_user_message(message: str, user_name: str, user_contact: str) -> str:
    user_data = {'nom': user_name, 'contacte': user_contact}
    return bot.process_message(message, user_data)

def get_system_health() -> str:
    return bot.health_check()

def get_teachers_for_form() -> List[Dict]:
    return bot.get_teachers_list()

def get_bot_status() -> Dict:
    return bot.get_system_status()
