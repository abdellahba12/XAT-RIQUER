import google.generativeai as genai
import requests
import tempfile
import os
import json
import logging
from typing import Dict, List, Optional
import re
from datetime import datetime

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de API
api_key = os.environ.get("API_GEMINI")
if not api_key:
    logger.warning("No se encontró API_GEMINI en las variables de entorno")

genai.configure(api_key=api_key)

class RiquerChatBot:
    def __init__(self):
        self.model = None
        self.chat = None
        self.uploaded_files = []  # Ahora guardará objetos File de Gemini
        self.file_contents = []  # Para guardar contenido como texto de respaldo
        self.initialize_directories()
        self.initialize_files()
        self.initialize_chat()
    
    def initialize_directories(self):
        """Crear directorios necesarios"""
        os.makedirs('drive_files', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
    def initialize_files(self):
        """Descarga y SUBE los archivos CSV/TXT a Gemini API"""
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
                
                # Determinar tipo de archivo
                file_extension = ".txt"  # Por defecto
                if b',' in response.content[:1000] and b'\n' in response.content[:1000]:
                    file_extension = ".csv"
                
                # Guardar temporalmente y subir a Gemini
                with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp_file:
                    tmp_file.write(response.content)
                    tmp_file_path = tmp_file.name
                
                try:
                    # IMPORTANTE: Subir archivo a Gemini API
                    uploaded_file = genai.upload_file(tmp_file_path, mime_type="text/plain")
                    self.uploaded_files.append(uploaded_file)
                    logger.info(f"Archivo {i+1} subido a Gemini: {uploaded_file.name}")
                    
                    # También guardar contenido como texto para respaldo
                    try:
                        with open(tmp_file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            self.file_contents.append(f"\n--- Archivo {i+1} ---\n{content[:2000]}")
                    except UnicodeDecodeError:
                        with open(tmp_file_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                            self.file_contents.append(f"\n--- Archivo {i+1} ---\n{content[:2000]}")
                    
                    successful_uploads += 1
                    
                finally:
                    # Limpiar archivo temporal
                    os.remove(tmp_file_path)
                
            except Exception as e:
                logger.error(f"Error cargando archivo {url}: {str(e)}")
                continue
        
        logger.info(f"Archivos subidos exitosamente a Gemini: {successful_uploads}/{len(file_urls)}")
    
    def get_teachers_list(self) -> List[Dict]:
        """Obtiene la lista de profesores para el formulario"""
        # Lista estática de profesores (puedes expandirla o cargarla desde CSV)
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
        """Función de email usando Mailgun API"""
        try:
            mailgun_api_key = os.environ.get("MAILGUN_API_KEY")
            mailgun_domain = os.environ.get("MAILGUN_DOMAIN")
            
            if not mailgun_api_key or not mailgun_domain:
                logger.error("Faltan variables de Mailgun")
                return {
                    "status": "error",
                    "error": "Configuración de Mailgun no disponible"
                }
            
            # Preparar datos para Mailgun
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
                    "error": f"Error enviando email: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error enviando correo: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def detect_language(self, message: str) -> str:
        """Detecta el idioma del mensaje"""
        message_lower = message.lower()
        
        # Detectar árabe por caracteres árabes
        if any(ord(char) > 1536 and ord(char) < 1791 for char in message):
            return 'ar'
        
        # Palabras distintivas por idioma
        catalan_indicators = ['què', 'com', 'quan', 'on', 'amb', 'són', 'està', 'estan', 
                              'alumne', 'professor', 'institut', 'curs']
        spanish_indicators = ['qué', 'cómo', 'cuándo', 'dónde', 'con', 'son', 'está', 'están',
                              'alumno', 'profesor', 'instituto', 'curso']
        
        catalan_score = sum(1 for word in catalan_indicators if word in message_lower)
        spanish_score = sum(1 for word in spanish_indicators if word in message_lower)
        
        if spanish_score > catalan_score:
            return 'es'
        elif catalan_score > spanish_score:
            return 'ca'
        else:
            return 'ca'  # Por defecto catalán
    
    def initialize_chat(self):
        """Inicializa el chat con Gemini incluyendo los archivos subidos"""
        try:
            # Crear el modelo
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Contexto del sistema
            context = """
            Ets Riquer, l'assistent virtual de l'Institut Alexandre de Riquer de Calaf.
            Ets amable, professional i eficient.
            
            REGLA CRÍTICA D'IDIOMA:
            - Si algú escriu en català → respon en català
            - Si algú escriu en castellà → respon en castellà  
            - Si algú escriu en àrab → respon en àrab
            - SEMPRE detecta l'idioma d'entrada i respon en el MATEIX idioma
            
            REGLES IMPORTANTS:
            1. Auto-detecta l'idioma del missatge i respon en aquest idioma exacte
            2. Només respon preguntes relacionades amb l'institut
            3. Per contactar amb professors, ajuda a preparar un correu
            4. Per justificar absències, envia a 'abdellahbaghalbachiri@gmail.com'
            5. Sigues concís però complet
            6. Utilitza emojis moderadament
            7. NOMÉS utilitza informació dels arxius CSV de l'institut - NO inventis informació
            8. Si no trobes informació específica als arxius, explica que no està disponible
            
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
            
            # Si hay archivos subidos a Gemini, incluirlos en el chat
            if self.uploaded_files:
                # Iniciar chat con los archivos adjuntos
                self.chat = self.model.start_chat(
                    history=[
                        {
                            "role": "user", 
                            "parts": [
                                context,
                                "Aquí tens els arxius de l'institut amb tota la informació:",
                                *self.uploaded_files  # Incluir los archivos subidos
                            ]
                        },
                        {
                            "role": "model", 
                            "parts": ["Entès! Sóc Riquer, l'assistent virtual de l'Institut Alexandre de Riquer. "
                                     "He carregat i processat tots els arxius CSV amb la informació de l'institut. "
                                     "Puc ajudar-te en català, castellà i àrab basant-me exclusivament en la informació "
                                     "dels arxius de l'institut. En què et puc ajudar avui?"]
                        }
                    ]
                )
            else:
                # Si no hay archivos, usar solo el contexto de texto
                self.chat = self.model.start_chat(
                    history=[
                        {"role": "user", "parts": [context]},
                        {"role": "model", "parts": ["Entès! Sóc Riquer, l'assistent virtual de l'Institut Alexandre de Riquer."]}
                    ]
                )
            
            logger.info(f"Chat inicializado con {len(self.uploaded_files)} archivos adjuntos")
            
        except Exception as e:
            logger.error(f"Error inicializando el chat: {str(e)}")
            self.model = None
            self.chat = None
    
    def process_message(self, message: str, user_data: Dict) -> str:
        """Procesa un mensaje del usuario"""
        try:
            if not self.chat:
                return "Ho sento, hi ha hagut un problema tècnic. Si us plau, recarrega la pàgina."
            
            # Detectar idioma
            detected_language = 'ca'  # Por defecto
            
            if message.startswith('[ES] '):
                detected_language = 'es'
                message = message[5:].strip()
            elif message.startswith('[CA] '):
                detected_language = 'ca'
                message = message[5:].strip()
            elif message.startswith('[AR] '):
                detected_language = 'ar'
                message = message[5:].strip()
            else:
                detected_language = self.detect_language(message)
            
            logger.info(f"Idioma detectado: {detected_language} para mensaje: {message[:50]}...")
            
            # Instrucciones de idioma
            language_commands = {
                'ca': "IMPORTANT: Respon NOMÉS en català. Consulta els arxius CSV per donar informació precisa.",
                'es': "IMPORTANTE: Responde ÚNICAMENTE en español. Consulta los archivos CSV para dar información precisa.",
                'ar': "مهم: أجب فقط باللغة العربية. راجع ملفات CSV لتقديم معلومات دقيقة."
            }
            
            # Construir mensaje completo
            full_message = f"""{language_commands.get(detected_language, language_commands['ca'])}

Usuari: {user_data.get('nom', 'Desconegut')}
Pregunta: {message}

RECORDA: Consulta SEMPRE els arxius CSV adjunts abans de respondre. Si la informació no està als arxius, indica-ho clarament.
IDIOMA DE RESPOSTA OBLIGATORI: {detected_language.upper()}"""
            
            # Verificar si es formulario
            if self._is_form_submission(message):
                return self._handle_form_submission(message, user_data, detected_language)
            
            # Enviar a Gemini
            response = self.chat.send_message(full_message)
            response_text = response.text
            
            return self._format_response(response_text)
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            error_messages = {
                'ar': "عذراً، حدث خطأ في معالجة استفسارك. يرجى المحاولة مرة أخرى.",
                'es': "Lo siento, ha habido un error procesando tu consulta. Por favor, inténtalo de nuevo.",
                'ca': "Ho sento, hi ha hagut un error processant la teva consulta. Si us plau, torna-ho a intentar."
            }
            return error_messages.get(detected_language, error_messages['ca'])
    
    def _is_form_submission(self, message: str) -> bool:
        """Detecta si el mensaje es una sumisión de formulario"""
        form_keywords = [
            "Justificar falta - Alumne:",
            "Contactar professor",
            "- Assumpte:",
            "Missatge:"
        ]
        return any(keyword in message for keyword in form_keywords)
    
    def _handle_form_submission(self, message: str, user_data: Dict, language: str) -> str:
        """Maneja la sumisión de formularios y envía emails"""
        try:
            if "Justificar falta" in message:
                return self._handle_absence_form(message, user_data, language)
            elif "Contactar professor" in message:
                return self._handle_teacher_contact_form(message, user_data, language)
            else:
                error_messages = {
                    'ar': "لم يتم التمكن من معالجة النموذج. يرجى المحاولة مرة أخرى.",
                    'es': "No se ha podido procesar el formulario. Por favor, inténtalo de nuevo.",
                    'ca': "No s'ha pogut processar el formulari. Si us plau, torna-ho a intentar."
                }
                return error_messages.get(language, error_messages['ca'])
        except Exception as e:
            logger.error(f"Error manejando formulario: {str(e)}")
            return f"⚠️ Error al processar el formulari: {str(e)}"
    
    def _handle_absence_form(self, message: str, user_data: Dict, language: str) -> str:
        """Procesa el formulario de justificación de faltas"""
        try:
            # Parser para extraer datos
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
            
            # Validar datos
            if not all([alumne, curs, data_falta, motiu]):
                error_messages = {
                    'ar': "⚠️ يرجى ملء جميع الحقول المطلوبة",
                    'es': "⚠️ Por favor, completa todos los campos requeridos",
                    'ca': "⚠️ Si us plau, completa tots els camps requerits"
                }
                return error_messages.get(language, error_messages['ca'])
            
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
                success_messages = {
                    'ar': f"✅ تم إرسال التبرير بنجاح! المستلم: abdellahbaghalbachiri@gmail.com",
                    'es': f"✅ ¡Justificación enviada correctamente! Destinatario: abdellahbaghalbachiri@gmail.com",
                    'ca': f"✅ Justificació enviada correctament! Destinatari: abdellahbaghalbachiri@gmail.com"
                }
                return success_messages.get(language, success_messages['ca'])
            else:
                error_messages = {
                    'ar': f"❌ خطأ في إرسال التبرير. البدائل: الاتصال 93 868 04 14",
                    'es': f"❌ Error al enviar. Alternativas: Llamar 93 868 04 14",
                    'ca': f"❌ Error al enviar. Alternatives: Trucar 93 868 04 14"
                }
                return error_messages.get(language, error_messages['ca'])
                
        except Exception as e:
            logger.error(f"Error en justificación: {str(e)}")
            return f"⚠️ Error al processar la justificació: {str(e)}"
    
    def _handle_teacher_contact_form(self, message: str, user_data: Dict, language: str) -> str:
        """Procesa el formulario de contacto con profesor"""
        try:
            # Parser para extraer datos
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
            
            # Validar datos
            if not all([professor_name, subject, message_content]):
                error_messages = {
                    'ar': "⚠️ يرجى ملء جميع الحقول المطلوبة",
                    'es': "⚠️ Por favor, completa todos los campos requeridos",
                    'ca': "⚠️ Si us plau, completa tots els camps requerits"
                }
                return error_messages.get(language, error_messages['ca'])
            
            # Generar email del profesor
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
                success_messages = {
                    'ar': f"✅ تم إرسال الرسالة بنجاح! المستلم: {professor_email}",
                    'es': f"✅ ¡Mensaje enviado correctamente! Destinatario: {professor_email}",
                    'ca': f"✅ Missatge enviat correctament! Destinatari: {professor_email}"
                }
                return success_messages.get(language, success_messages['ca'])
            else:
                error_messages = {
                    'ar': f"❌ خطأ في الإرسال. البدائل: الاتصال 93 868 04 14",
                    'es': f"❌ Error al enviar. Alternativas: Llamar 93 868 04 14",
                    'ca': f"❌ Error al enviar. Alternatives: Trucar 93 868 04 14"
                }
                return error_messages.get(language, error_messages['ca'])
                
        except Exception as e:
            logger.error(f"Error contactando profesor: {str(e)}")
            return f"⚠️ Error al contactar amb el professor: {str(e)}"
    
    def _format_response(self, response: str) -> str:
        """Formatea la respuesta para mejorar la presentación"""
        # Limpiar posibles asteriscos de formato de Gemini
        response = response.replace('**', '')
        response = response.replace('*', '')
        
        # Asegurar salto de línea al final
        if not response.endswith('\n'):
            response += '\n'
        
        return response.strip()
    
    def get_system_status(self) -> Dict:
        """Obtiene el estado del sistema"""
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
        """Realiza un chequeo de salud del sistema"""
        status = self.get_system_status()
        
        health_report = "🔍 **Informe de Estado del Sistema**\n\n"
        
        # Estado del chat
        if status['chat_initialized'] and status['model_available']:
            health_report += "✅ Chat: Operativo\n"
        else:
            health_report += "❌ Chat: Error de inicialización\n"
        
        # Archivos
        health_report += f"📁 Archivos subidos a Gemini: {status['files_uploaded_to_gemini']}\n"
        health_report += f"📄 Respaldos de contenido: {status['file_contents_backup']}\n"
        
        # Configuración
        health_report += f"{'✅' if status['api_key_configured'] else '❌'} API Gemini: {'Configurada' if status['api_key_configured'] else 'No configurada'}\n"
        health_report += f"{'✅' if status['mailgun_configured'] else '❌'} Mailgun: {'Configurado' if status['mailgun_configured'] else 'No configurado'}\n"
        
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
