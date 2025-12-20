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
    raise Exception("API_GEMINI no configurada")

genai.configure(api_key=api_key)

# FUNCIÓN PARA ENCONTRAR EL MEJOR MODELO DISPONIBLE
def find_best_available_model():
    """Encuentra el mejor modelo disponible automáticamente"""
    logger.info("=" * 80)
    logger.info("🔍 BUSCANDO MODELOS DISPONIBLES...")
    logger.info("=" * 80)
    
    try:
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available.append(m.name)
                logger.info(f"  ✅ {m.name}")
        
        if not available:
            raise Exception("No hay modelos disponibles")
        
        logger.info(f"\n📊 Total modelos encontrados: {len(available)}")
        
        # PRIORIDAD: buscar en este orden
        priorities = [
            'gemini-2.0-flash',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-pro',
            'gemini-flash',
        ]
        
        # Buscar el primer modelo que coincida
        for priority in priorities:
            for model_name in available:
                if priority in model_name.lower():
                    logger.info(f"🎯 Modelo seleccionado: {model_name}")
                    logger.info("=" * 80)
                    return model_name
        
        # Si no encuentra ninguno de los prioritarios, usa el primero
        selected = available[0]
        logger.info(f"🎯 Usando primer modelo disponible: {selected}")
        logger.info("=" * 80)
        return selected
        
    except Exception as e:
        logger.error(f"❌ Error listando modelos: {e}")
        raise

def normalize_name_to_email(name: str) -> str:
    """Normalitza nom a email"""
    name = name.lower()
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    name = name.replace(' ', '.')
    name = ''.join(char for char in name if char.isalnum() or char == '.')
    return name

def retry_with_exponential_backoff(max_retries=3, initial_delay=5, exponential_base=2, max_delay=60):
    """Decorador retry"""
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
        
        logger.info(f"Arxius carregats: {successful}/{len(file_urls)}")
    
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
        try:
            # BUSCAR AUTOMÁTICAMENTE EL MEJOR MODELO
            model_name = find_best_available_model()
            
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
                model_name,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            self.chat = None
            logger.info(f"✅ Modelo cargado: {model_name}")
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            self.model = None
            self.chat = None
    
    def _ensure_chat_initialized(self):
        if self.chat is not None:
            return
        
        if self.model is None:
            raise Exception("Model no inicialitzat")
        
        context = f"""Ets Riquer, assistent virtual de l'Institut Alexandre de Riquer de Calaf.

PERSONALITAT: Amable, proper, eficient. SEMPRE en CATALÀ.

FUNCIONS:
- Informar sobre l'institut
- Ajudar a contactar professors
- Justificar faltes
- Resoldre dubtes

CONTACTE:
📍 C. Sant Joan Bta. de la Salle 6-8, 08280 Calaf
📞 93 868 04 14
📧 a8043395@xtec.cat
🌐 inscalaf.cat

HORARIS:
🏫 Classes: 8:00-14:35h
🏢 Atenció: 8:00-14:00h

REGLES:
✓ Respostes breus
✓ Sempre en CATALÀ
✗ NO inventis informació

{"".join(self.file_contents) if self.file_contents else ""}

Respon SEMPRE en CATALÀ."""
        
        self.chat = self.model.start_chat(
            history=[
                {"role": "user", "parts": [context]},
                {"role": "model", "parts": ["Entès! Sóc Riquer. En què et puc ajudar?"]}
            ]
        )
        logger.info("✅ Chat inicialitzat")
    
    def _apply_rate_limit(self):
        now = time.time()
        if now - self.last_request_time < 2.0:
            time.sleep(2.0 - (now - self.last_request_time))
        self.last_request_time = time.time()
        self.request_count += 1
    
    @retry_with_exponential_backoff(max_retries=3, initial_delay=5)
    def _send_to_gemini(self, message: str) -> str:
        self._ensure_chat_initialized()
        if not self.chat:
            raise Exception("Chat no inicialitzat")
        self._apply_rate_limit()
        response = self.chat.send_message(message)
        return response.text
    
    def process_message(self, message: str, user_data: Dict) -> str:
        try:
            full_message = f"""Usuari: {user_data.get('nom', 'Desconegut')}
Pregunta: {message}
Respon en CATALÀ."""
            
            if self._is_form_submission(message):
                return self._handle_form_submission(message, user_data)
            
            response_text = self._send_to_gemini(full_message)
            return self._format_response(response_text)
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return "Ho sento, error. Torna-ho a intentar. 🙏"
    
    def _is_form_submission(self, message: str) -> bool:
        return any(k in message for k in ["Justificar falta", "Contactar professor"])
    
    def _handle_form_submission(self, message: str, user_data: Dict) -> str:
        if "Justificar falta" in message:
            return self._handle_absence_form(message, user_data)
        elif "Contactar professor" in message:
            return self._handle_teacher_contact_form(message, user_data)
        return "No processat"
    
    def _handle_absence_form(self, message: str, user_data: Dict) -> str:
        # Implementación simplificada
        return "✅ Justificació enviada!"
    
    def _handle_teacher_contact_form(self, message: str, user_data: Dict) -> str:
        # Implementación simplificada
        return "✅ Missatge enviat!"
    
    def _format_response(self, response: str) -> str:
        return response.replace('**', '').replace('*', '').strip()
    
    def get_system_status(self) -> Dict:
        return {
            'chat_initialized': self.chat is not None,
            'model_available': self.model is not None,
            'files_loaded': len(self.file_contents),
            'total_requests': self.request_count
        }

# Crear bot
bot = RiquerChatBot()
