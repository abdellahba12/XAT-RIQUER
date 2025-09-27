import google.generativeai as genai
import requests
import tempfile
import os
import json
import logging
from typing import Dict, List, Optional
import re
from datetime import datetime

# Configuració de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuració de API
api_key = os.environ.get("API_GEMINI")
if not api_key:
    logger.warning("⚠️ No s'ha trobat API_GEMINI a les variables d'entorn")
else:
    logger.info("✅ API Gemini configurada correctament")

genai.configure(api_key=api_key)

class RiquerChatBot:
    def __init__(self):
        self.model = None
        self.chat = None
        self.uploaded_files = []  # Llista d'arxius pujats a l'API de Gemini
        self.file_contents = []  # Còpia de seguretat del contingut dels arxius
        self.initialize_directories()
        self.initialize_files()
        self.initialize_chat()
    
    def initialize_directories(self):
        """Crear directoris necessaris"""
        os.makedirs('drive_files', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
    def initialize_files(self):
        """Descarrega i puja els arxius CSV/TXT a Gemini API"""
        file_urls = [
            "https://drive.google.com/uc?export=download&id=1-Stsv68nDGxH2kDy_idcGM6FoXYMO3I8",
            "https://drive.google.com/uc?export=download&id=1kOjm0jHpF-LqtXYC7uUC1HJAV7DQPBsy",
            "https://drive.google.com/uc?export=download&id=1iMfgjXLrn51EkYhCqMejJT7K5M5J5Ezy",
            "https://drive.google.com/uc?export=download&id=1N7Xpt9JSr1JPoIaju-ekIRW4NGVgPxMU",
            "https://drive.google.com/uc?export=download&id=1neJFgTH0GWO5HbL64V6Fro0r1SKw8mFw",
        ]
        
        successful_uploads = 0
        
        for i, url in enumerate(file_urls):
            try:
                logger.info(f"📥 Descarregant arxiu {i+1} de {len(file_urls)}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                # Verificar si és una pàgina HTML d'error
                if response.content.startswith(b'<!DOCTYPE html>'):
                    logger.warning(f"⚠️ Arxiu {i+1}: Rebut HTML en lloc de l'arxiu")
                    continue
                
                # Verificar tamany mínim
                if len(response.content) < 100:
                    logger.warning(f"⚠️ Arxiu {i+1}: Tamany molt petit ({len(response.content)} bytes)")
                    continue
                
                # Determinar tipus d'arxiu
                file_extension = ".txt"  
                if b',' in response.content[:1000] and b'\n' in response.content[:1000]:
                    file_extension = ".csv"
                
                # Guardar i pujar a Gemini
                with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp_file:
                    tmp_file.write(response.content)
                    tmp_file_path = tmp_file.name
                
                try:
                    # Pujar arxius a Gemini
                    uploaded_file = genai.upload_file(tmp_file_path, mime_type="text/plain")
                    self.uploaded_files.append(uploaded_file)
                    logger.info(f"✅ Arxiu {i+1} pujat a Gemini: {uploaded_file.name}")
                    
                    # Guardar contingut dels arxius
                    try:
                        with open(tmp_file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            self.file_contents.append(f"\n--- Arxiu {i+1} ---\n{content[:2000]}")
                    except UnicodeDecodeError:
                        with open(tmp_file_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                            self.file_contents.append(f"\n--- Arxiu {i+1} ---\n{content[:2000]}")
                    
                    successful_uploads += 1
                    
                finally:
                    # Esborrar arxiu temporal
                    os.remove(tmp_file_path)
                
            except Exception as e:
                logger.error(f"❌ Error carregant arxiu {url}: {str(e)}")
                continue
        
        logger.info(f"📊 Arxius pujats correctament a Gemini: {successful_uploads}/{len(file_urls)}")
    
    def get_teachers_list(self) -> List[Dict]:
        """Obté la llista de professors per al formulari"""
        teachers = [
            {'name': 'Roger Codina', 'email': 'roger.codina@inscalaf.cat'},
            {'name': 'Abdellah Baghal', 'email': 'abdellah.baghal@inscalaf.cat'},
            {'name': 'Anna Puig', 'email': 'anna.puig@inscalaf.cat'},
            {'name': 'Carles Rovira', 'email': 'carles.rovira@inscalaf.cat'},
            {'name': 'Maria González', 'email': 'maria.gonzalez@inscalaf.cat'},
            {'name': 'Josep Martí', 'email': 'josep.marti@inscalaf.cat'},
            {'name': 'Laura Fernández', 'email': 'laura.fernandez@inscalaf.cat'},
            {'name': 'David López', 'email': 'david.lopez@inscalaf.cat'},
            {'name': 'Montserrat Vila', 'email': 'montserrat.vila@inscalaf.cat'},
            {'name': 'Jordi Pujol', 'email': 'jordi.pujol@inscalaf.cat'}
        ]
        
        return teachers
    
    def send_email(self, subject: str, body: str, recipients: List[str]) -> Dict:
        """Envia emails mitjançant Mailgun API"""
        try:
            mailgun_api_key = os.environ.get("MAILGUN_API_KEY")
            mailgun_domain = os.environ.get("MAILGUN_DOMAIN")
            
            if not mailgun_api_key or not mailgun_domain:
                logger.error("❌ Falten variables de Mailgun")
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
                logger.info(f"✅ Correu enviat correctament a: {recipients}")
                return {
                    "status": "success",
                    "subject": subject,
                    "body": body,
                    "sender": "riquer@inscalaf.cat",
                    "recipients": recipients,
                }
            else:
                logger.error(f"❌ Error Mailgun: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "error": f"Error enviant email: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"❌ Error enviant correu: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def initialize_chat(self):
        """Inicialitza el xat amb Gemini amb els arxius pujats"""
        try:
            # Crear model
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Context del sistema
            context = """
            Ets Riquer, l'assistent virtual de l'Institut Alexandre de Riquer de Calaf.
            Ets amable, professional i eficient.
            
            REGLES IMPORTANTS:
            1. SEMPRE respon en CATALÀ
            2. Només respon preguntes relacionades amb l'institut
            3. Per contactar amb professors, ajuda a preparar un correu
            4. Per justificar absències, envia a 'abdellahbaghalbachiri@gmail.com'
            5. Sigues concís però complet
            6. Utilitza emojis moderadament per ser més proper
            7. NOMÉS utilitza informació dels arxius CSV de l'institut - NO inventis informació
            8. Si no trobes informació específica als arxius, explica que no està disponible
            9. Si algú demana justificar una falta o demanar una reunió, suggereix usar els botons ràpids
            
            INFORMACIÓ DE L'INSTITUT:
            - Nom: Institut Alexandre de Riquer
            - Adreça: C. Sant Joan Bta. de la Salle 6-8, 08280 Calaf (Anoia)
            - Telèfon: 93 868 04 14
            - Email general: a8043395@xtec.cat
            - Web: http://www.inscalaf.cat
            - Consergeria: abdellahbaghalbachiri@gmail.com
            
            HORARIS:
            - Horari escolar: matins de 8:00 a 14:35
            - Atenció al públic: dilluns a divendres de 8:00 a 14:00h
            - Secretaria: dilluns a divendres de 9:00 a 13:00h
            
            CURSOS DISPONIBLES:
            - ESO (1r, 2n, 3r, 4t)
            - Batxillerat (1r, 2n)
            - Formació Professional (Grau Mitjà i Superior)
            
            Tens accés als següents arxius CSV amb informació de l'institut:
            - Horaris de classes
            - Llista de professors
            - Activitats extraescolars
            - Calendari escolar
            - Informació de contacte
            
            SEMPRE consulta aquests arxius abans de respondre preguntes específiques sobre horaris, professors o activitats.
            """
            
            # Si hi han arxius pujats, incloure'ls al context
            if self.uploaded_files:
                # Iniciar xat amb els arxius adjunts
                self.chat = self.model.start_chat(
                    history=[
                        {
                            "role": "user", 
                            "parts": [
                                context,
                                "Aquí tens els arxius de l'institut amb tota la informació:",
                                *self.uploaded_files  # Incloure els arxius pujats
                            ]
                        },
                        {
                            "role": "model", 
                            "parts": ["Entès! Sóc Riquer, l'assistent virtual de l'Institut Alexandre de Riquer. "
                                     "He carregat i processat tots els arxius CSV amb la informació de l'institut. "
                                     "Puc ajudar-te amb qualsevol consulta sobre l'institut basant-me exclusivament "
                                     "en la informació dels arxius. En què et puc ajudar avui? 😊"]
                        }
                    ]
                )
            else:
                self.chat = self.model.start_chat(
                    history=[
                        {"role": "user", "parts": [context]},
                        {"role": "model", "parts": ["Entès! Sóc Riquer, l'assistent virtual de l'Institut Alexandre de Riquer. "
                                                    "En què et puc ajudar avui? 😊"]}
                    ]
                )
            
            logger.info(f"✅ Xat inicialitzat amb {len(self.uploaded_files)} arxius adjunts")
            
        except Exception as e:
            logger.error(f"❌ Error inicialitzant el xat: {str(e)}")
            self.model = None
            self.chat = None
    
    def process_message(self, message: str, user_data: Dict) -> str:
        """Processa un missatge de l'usuari"""
        try:
            if not self.chat:
                return "Ho sento, hi ha hagut un problema tècnic. Si us plau, recarrega la pàgina. 😔"
            
            # Construir missatge complet
            full_message = f"""IMPORTANT: Respon NOMÉS en català. Consulta els arxius CSV per donar informació precisa.

Usuari: {user_data.get('nom', 'Desconegut')}
Pregunta: {message}

RECORDA: Consulta SEMPRE els arxius CSV adjunts abans de respondre. Si la informació no està als arxius, indica-ho clarament."""
            
            # Verificar si és un formulari
            if self._is_form_submission(message):
                return self._handle_form_submission(message, user_data)
            
            # Enviar a Gemini
            response = self.chat.send_message(full_message)
            response_text = response.text
            
            return self._format_response(response_text)
            
        except Exception as e:
            logger.error(f"❌ Error processant missatge: {str(e)}")
            return "Ho sento, hi ha hagut un error processant la teva consulta. Si us plau, torna-ho a intentar. 😔"
    
    def _is_form_submission(self, message: str) -> bool:
        """Detecta si el missatge és un formulari"""
        form_keywords = [
            "Justificar falta - Alumne:",
            "Contactar professor",
            "- Assumpte:",
            "Missatge:"
        ]
        return any(keyword in message for keyword in form_keywords)
    
    def _handle_form_submission(self, message: str, user_data: Dict) -> str:
        """Controla els formularis i envia emails"""
        try:
            if "Justificar falta" in message:
                return self._handle_absence_form(message, user_data)
            elif "Contactar professor" in message:
                return self._handle_teacher_contact_form(message, user_data)
            else:
                return "No s'ha pogut processar el formulari. Si us plau, torna-ho a intentar. 😔"
        except Exception as e:
            logger.error(f"❌ Error processant formulari: {str(e)}")
            return f"⚠️ Error al processar el formulari: {str(e)}"
    
    def _handle_absence_form(self, message: str, user_data: Dict) -> str:
        """Processa el formulari de justificació de faltes"""
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
            
            # Construir email
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
                return f"✅ Justificació enviada correctament! Destinatari: abdellahbaghalbachiri@gmail.com"
            else:
                return f"❌ Error al enviar. Alternatives: Trucar 93 868 04 14"
                
        except Exception as e:
            logger.error(f"❌ Error en justificació: {str(e)}")
            return f"⚠️ Error al processar la justificació: {str(e)}"
    
    def _handle_teacher_contact_form(self, message: str, user_data: Dict) -> str:
        """Processa el formulari de contacte amb professor"""
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
Enviat automàticament des del sistema de l'Institut Alexandre de Riquer
{datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            # Intentar enviar email
            result = self.send_email(email_subject, email_body, [professor_email])
            
            if result["status"] == "success":
                return f"✅ Missatge enviat correctament! Destinatari: {professor_email}"
            else:
                return f"❌ Error al enviar. Alternatives: Trucar 93 868 04 14"
                
        except Exception as e:
            logger.error(f"❌ Error contactant professor: {str(e)}")
            return f"⚠️ Error al contactar amb el professor: {str(e)}"
    
    def _format_response(self, response: str) -> str:
        """Formata la resposta per millorar la presentació"""
        # Treure caràcters estranys
        response = response.replace('**', '')
        response = response.replace('*', '')
        
        # Afegir salt de línia
        if not response.endswith('\n'):
            response += '\n'
        
        return response.strip()
    
    def get_system_status(self) -> Dict:
        """Estat del sistema"""
        status = {
            'chat_initialized': self.chat is not None,
            'model_available': self.model is not None,
            'files_uploaded_to_gemini': len(self.uploaded_files),
            'file_contents_backup': len(self.file_contents),
            'api_key_configured': bool(os.environ.get("API_GEMINI")),
            'mailgun_configured': all([
                os.environ.get("MAILGUN_API_KEY"),
                os.environ.get("MAILGUN_DOMAIN")
            ])
        }
        
        return status
    
    def health_check(self) -> str:
        """Comprova l'estat del sistema"""
        status = self.get_system_status()
        
        health_report = "🔍 **Informe d'Estat del Sistema**\n\n"
        
        # Estat del xat
        if status['chat_initialized'] and status['model_available']:
            health_report += "✅ Xat: Operatiu\n"
        else:
            health_report += "❌ Xat: Error d'inicialització\n"
        
        # Arxius
        health_report += f"📁 Arxius pujats a Gemini: {status['files_uploaded_to_gemini']}\n"
        health_report += f"📄 Còpies de seguretat: {status['file_contents_backup']}\n"
        
        # Configuració
        health_report += f"{'✅' if status['api_key_configured'] else '❌'} API Gemini: {'Configurada' if status['api_key_configured'] else 'No configurada'}\n"
        health_report += f"{'✅' if status['mailgun_configured'] else '❌'} Mailgun: {'Configurat' if status['mailgun_configured'] else 'No configurat'}\n"
        
        return health_report

# Crear instància global
bot = RiquerChatBot()

# Funcions d'utilitat per Flask
def process_user_message(message: str, user_name: str, user_contact: str) -> str:
    """Processa missatges per la interfície Flask"""
    user_data = {
        'nom': user_name,
        'contacte': user_contact
    }
    return bot.process_message(message, user_data)

def get_system_health() -> str:
    """Obté l'estat del sistema"""
    return bot.health_check()

def get_teachers_for_form() -> List[Dict]:
    """Obté la llista de professors per formularis"""
    return bot.get_teachers_list()

def get_bot_status() -> Dict:
    """Obté l'estat detallat del bot"""
    return bot.get_system_status()
