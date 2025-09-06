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

# Intentar importar el analizador CSV
try:
    from csv_analyzer import search_csv_info, get_professors_from_csv, get_activities_from_csv, csv_analyzer
    CSV_ANALYZER_AVAILABLE = True
except ImportError:
    CSV_ANALYZER_AVAILABLE = False
    logger.warning("CSV Analyzer no disponible")

# Configuración de API
api_key = os.environ.get("API_GEMINI")
if not api_key:
    logger.warning("No se encontró API_GEMINI en las variables de entorno")

genai.configure(api_key=api_key)

class RiquerChatBot:
    def __init__(self):
        self.model = None
        self.chat = None
        self.uploaded_files = []
        self.initialize_directories()
        self.initialize_files()
        self.initialize_chat()
    
    def initialize_directories(self):
        """Crear directorios necesarios"""
        os.makedirs('drive_files', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
    def initialize_files(self):
        """Descarga y carga los archivos CSV/TXT de Drive"""
        file_urls = [
            "https://drive.google.com/uc?export=download&id=1neJFgTH0GWO5HbL64V6Fro0r1SKw8mFw",
            "https://drive.google.com/uc?export=download&id=1kOjm0jHpF-LqtXYC7uUC1HJAV7DQPBsy",
            "https://drive.google.com/uc?export=download&id=1iMfgjXLrn51EkYhCqMejJT7K5M5J5Ezy",
            "https://drive.google.com/uc?export=download&id=1N7Xpt9JSr1JPoIaju-ekIRW4NGVgPxMU",
        ]
        
        for i, url in enumerate(file_urls):
            try:
                logger.info(f"Descargando archivo {i+1} de {len(file_urls)}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                # Determinar extensión
                file_extension = ".csv" if "csv" in response.headers.get('content-type', '') else ".txt"
                file_path = f"drive_files/file_{i+1}{file_extension}"
                
                # Guardar archivo localmente
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # Para Gemini, leer el contenido
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    self.uploaded_files.append(f"\n--- Archivo {i+1} ---\n{content[:2000]}...")
                
                logger.info(f"Archivo {i+1} cargado correctamente")
                
            except Exception as e:
                logger.error(f"Error cargando archivo {url}: {str(e)}")
        
        logger.info(f"Total archivos cargados: {len(self.uploaded_files)}")
    
    def get_teachers_list(self) -> List[Dict]:
        """Obtiene la lista de profesores desde los CSV para el formulario"""
        teachers = []
        
        if CSV_ANALYZER_AVAILABLE:
            try:
                # Obtener lista de profesores del CSV analyzer
                professors = csv_analyzer.get_professors_list()
                
                for professor in professors[:20]:  # Limitar a 20 profesores
                    if professor and len(professor.split()) >= 2:  # Asegurar que tiene nombre y apellido
                        # Generar email formato: nombre.apellido@inscalaf.cat
                        email = professor.lower().replace(' ', '.')
                        # Limpiar caracteres especiales
                        email = (email.replace('à', 'a').replace('è', 'e').replace('í', 'i')
                                .replace('ò', 'o').replace('ú', 'u').replace('ç', 'c')
                                .replace('ñ', 'n').replace('ü', 'u'))
                        email = f"{email}@inscalaf.cat"
                        
                        teachers.append({
                            'name': professor,
                            'email': email
                        })
            except Exception as e:
                logger.warning(f"Error obteniendo profesores del CSV: {str(e)}")
        
        # Añadir algunos profesores fijos si no hay CSV o como fallback
        fallback_teachers = [
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
        
        # Si no hay profesores del CSV, usar los de fallback
        if not teachers:
            teachers = fallback_teachers
        else:
            # Combinar CSV + fallback sin duplicados
            existing_names = {t['name'].lower() for t in teachers}
            for teacher in fallback_teachers:
                if teacher['name'].lower() not in existing_names:
                    teachers.append(teacher)
        
        # Ordenar alfabéticamente
        teachers.sort(key=lambda x: x['name'])
        
        return teachers
    
    def send_email(self, subject: str, body: str, recipients: List[str]) -> Dict:
    """Función de email usando Mailgun API - funcionalidad idéntica al SMTP original"""
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
    def get_csv_info(self, query: str) -> str:
        """Obtiene información específica de los archivos CSV"""
        csv_info = ""
        if CSV_ANALYZER_AVAILABLE:
            try:
                # Buscar información en los CSV
                search_results = search_csv_info(query)
                if search_results:
                    csv_info += f"\n\nInformació dels arxius de l'institut:\n{search_results}"
                
                # Si pregunta por profesores
                if any(word in query.lower() for word in ['professor', 'docent', 'tutor', 'teacher']):
                    professors_info = get_professors_from_csv()
                    if professors_info:
                        csv_info += f"\n\nProfessors disponibles:\n{professors_info}"
                
                # Si pregunta por actividades
                if any(word in query.lower() for word in ['activitat', 'excursió', 'sortida', 'activity']):
                    activities_info = get_activities_from_csv()
                    if activities_info:
                        csv_info += f"\n\nActivitats programades:\n{activities_info}"
                        
            except Exception as e:
                logger.warning(f"Error obteniendo información CSV: {str(e)}")
        
        return csv_info
    
    def initialize_chat(self):
        """Inicializa el chat con Gemini"""
        try:
            # Crear el modelo
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Contexto del sistema
            context = """
            Ets un assistent multilingüe de l'Institut Alexandre de Riquer de Calaf.
            Et dius Riquer i ets amable, professional i eficient.
            
            IMPORTANT: Has de respondre SEMPRE en l'idioma en què et parlen:
            - Si et parlen en català, respon en català
            - Si et parlen en castellà/español, respon en castellà
            - Si et parlen en àrab (العربية), respon en àrab
            
            REGLES IMPORTANTS:
            1. Detecta automàticament l'idioma del missatge i respon en el mateix idioma
            2. Només has de respondre preguntes relacionades amb l'institut
            3. Quan algú vulgui contactar amb un professor, ajuda'l indicant que prepararàs un correu
            4. Per justificar faltes, indica que s'enviarà a 'abdellahbaghalbachiri@gmail.com'
            5. Per contactar professors, demana el nom del professor i el motiu
            6. Sigues concís però complet en les respostes
            7. Utilitza emojis moderadament per fer la conversa més amigable
            8. Si hi ha problemes tècnics amb emails, sempre ofereix alternatives
            9. NOMÉS utilitza la informació dels arxius CSV de l'institut - NO inventis informació
            10. Si no trobes informació específica als arxius, explica que no està disponible
            
            INFORMACIÓ DE L'INSTITUT:
            - Nom: Institut Alexandre de Riquer
            - Adreça: C. Sant Joan Bta. de la Salle 6-8, 08280 Calaf (Anoia)
            - Telèfon: 93 868 04 14
            - Email general: a8043395@xtec.cat
            - Web: http://www.inscalaf.cat
            - Consergeria: abdellahbaghalbachiri@gmail.com
            
            HORARIS:
            - Horari lectiu: matins de 8:00 a 14:35
            - Horari d'atenció al públic: dilluns a divendres de 8:00 a 14:00h
            - Secretaria: dilluns a divendres de 9:00 a 13:00h
            
            CURSOS DISPONIBLES:
            - ESO (1r, 2n, 3r, 4t)
            - Batxillerat (1r, 2n)
            - Cicles Formatius de Grau Mitjà i Superior
            
            INSTRUCCIONS PER CORREUS:
            - Si algú vol justificar una falta, demana: nom alumne, curs, data i motiu
            - Si algú vol contactar un professor, demana el nom del professor i el motiu
            - Sempre confirma abans d'indicar que s'enviarà un correu
            - Si hi ha problemes tècnics, ofereix alternatives: telèfon, email manual, presencial
            
            Recorda: SEMPRE respon en l'idioma del missatge rebut i NOMÉS amb informació dels arxius CSV.
            """
            
            # Iniciar chat con contexto y archivos
            initial_context = context + "\n\nInformació dels arxius de l'institut:"
            if self.uploaded_files:
                initial_context += "\n".join(self.uploaded_files[:3])
            
            self.chat = self.model.start_chat(history=[
                {"role": "user", "parts": [initial_context]},
                {"role": "model", "parts": ["Entès! Sóc en Riquer, l'assistent virtual multilingüe de l'Institut Alexandre de Riquer. Puc ajudar-vos en català, castellà i àrab basant-me exclusivament en la informació dels arxius de l'institut. Com puc ajudar-vos avui? 😊"]}
            ])
            
            logger.info("Chat inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando el chat: {str(e)}")
            self.model = None
            self.chat = None
    
    def detect_language(self, message: str) -> str:
        """Detecta el idioma del mensaje"""
        # Palabras clave por idioma
        catalan_words = ['què', 'com', 'quan', 'on', 'per', 'amb', 'que', 'és', 'són', 'està', 'estan', 'hem', 'han', 'tinc', 'tens']
        spanish_words = ['qué', 'cómo', 'cuándo', 'dónde', 'por', 'con', 'que', 'es', 'son', 'está', 'están', 'hemos', 'han', 'tengo', 'tienes']
        arabic_words = ['ما', 'كيف', 'متى', 'أين', 'في', 'مع', 'هو', 'هي', 'أن', 'من', 'إلى', 'على', 'لا', 'نعم']
        
        message_lower = message.lower()
        
        # Detectar árabe por caracteres
        if any(char in 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي' for char in message):
            return 'ar'
        
        # Contar coincidencias
        catalan_count = sum(1 for word in catalan_words if word in message_lower)
        spanish_count = sum(1 for word in spanish_words if word in message_lower)
        
        if catalan_count > spanish_count:
            return 'ca'
        elif spanish_count > catalan_count:
            return 'es'
        else:
            return 'ca'  # Por defecto catalán
    
    def process_message(self, message: str, user_data: Dict) -> str:
        """Procesa un mensaje del usuario"""
        try:
            # Si no hay chat inicializado, dar respuesta de error
            if not self.chat:
                return "Ho sento, hi ha hagut un problema tècnic. Si us plau, recarrega la pàgina."
            
            # Detectar idioma
            language = 'ca'  # Por defecto catalán
            if message.startswith('[AR] '):
                language = 'ar'
                message = message[5:]
            elif message.startswith('[ES] '):
                language = 'es'
                message = message[5:]
            else:
                language = self.detect_language(message)
            
            # Obtener información de los CSV
            csv_info = self.get_csv_info(message)
            
            # Construir el mensaje con contexto del usuario e idioma
            language_instruction = {
                'ca': "Respon en català.",
                'es': "Responde en español.",
                'ar': "أجب باللغة العربية."
            }
            
            full_message = f"{language_instruction.get(language, '')}\nUsuari: {user_data.get('nom', 'Desconegut')}\nPregunta: {message}{csv_info}"
            
            # Verificar si el mensaje contiene datos de formulario para email
            if self._is_form_submission(message):
                return self._handle_form_submission(message, user_data, language)
            
            # Enviar mensaje a Gemini
            response = self.chat.send_message(full_message)
            response_text = response.text
            
            return self._format_response(response_text)
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            # Respuesta de error en el idioma detectado
            error_messages = {
                'ar': "عذراً، حدث خطأ في معالجة استفسارك. يرجى المحاولة مرة أخرى.",
                'es': "Lo siento, ha habido un error procesando tu consulta. Por favor, inténtalo de nuevo.",
                'ca': "Ho sento, hi ha hagut un error processant la teva consulta. Si us plau, torna-ho a intentar."
            }
            return error_messages.get(language, error_messages['ca'])
    
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
            # Detectar tipo de formulario
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
            error_messages = {
                'ar': f"⚠️ خطأ في معالجة النموذج: {str(e)}",
                'es': f"⚠️ Error al procesar el formulario: {str(e)}",
                'ca': f"⚠️ Error al processar el formulari: {str(e)}"
            }
            return error_messages.get(language, error_messages['ca'])
    
    def _handle_absence_form(self, message: str, user_data: Dict, language: str) -> str:
        """Procesa el formulario de justificación de faltas"""
        try:
            # Parser mejorado para extraer datos
            lines = message.split('\n')
            data = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('Justificar falta - Alumne:'):
                    # Extraer todos los campos de la línea principal
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
            
            # Validar datos obligatorios
            if not all([alumne, curs, data_falta, motiu]):
                error_messages = {
                    'ar': "⚠️ يرجى ملء جميع الحقول المطلوبة (الطالب، الصف، التاريخ، السبب)",
                    'es': "⚠️ Por favor, completa todos los campos requeridos (alumno, curso, fecha, motivo)",
                    'ca': "⚠️ Si us plau, completa tots els camps requerits (alumne, curs, data, motiu)"
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
                    'ar': f"""✅ **تم إرسال التبرير بنجاح!**

📧 المستلم: abdellahbaghalbachiri@gmail.com
📋 الطالب: {alumne}
📚 الصف: {curs}
📅 التاريخ: {data_falta}

تم معالجة التبرير بنجاح.""",
                    'es': f"""✅ **¡Justificación enviada correctamente!**

📧 Destinatario: abdellahbaghalbachiri@gmail.com
📋 Alumno/a: {alumne}
📚 Curso: {curs}
📅 Fecha: {data_falta}

La justificación se ha procesado correctamente.""",
                    'ca': f"""✅ **Justificació enviada correctament!**

📧 Destinatari: abdellahbaghalbachiri@gmail.com
📋 Alumne/a: {alumne}
📚 Curs: {curs}
📅 Data: {data_falta}

La justificació s'ha processat correctament."""
                }
                return success_messages.get(language, success_messages['ca'])
            else:
                # Error simple
                error_messages = {
                    'ar': f"""❌ **خطأ في إرسال التبرير**

خطأ: {result.get('error', 'مشكلة في الاتصال')}

📄 **بدائل:**
1. **الاتصال**: 93 868 04 14
2. **بريد إلكتروني يدوي**: abdellahbaghalbachiri@gmail.com
3. **الحضور شخصياً**: من 8 صباحاً إلى 2 ظهراً""",
                    'es': f"""❌ **Error al enviar la justificación**

Error: {result.get('error', 'Problema de conexión')}

📄 **Alternativas:**
1. **Llamar**: 93 868 04 14
2. **Email manual**: abdellahbaghalbachiri@gmail.com
3. **Presentarse**: de 8h a 14h""",
                    'ca': f"""❌ **Error al enviar la justificació**

Error: {result.get('error', 'Problema de connexió')}

📄 **Alternatives:**
1. **Trucar**: 93 868 04 14
2. **Email manual**: abdellahbaghalbachiri@gmail.com
3. **Presentar-se**: de 8h a 14h"""
                }
                return error_messages.get(language, error_messages['ca'])
                
        except Exception as e:
            logger.error(f"Error en justificación: {str(e)}")
            error_messages = {
                'ar': f"""⚠️ **خطأ في معالجة التبرير**

📄 **بدائل لتبرير الغياب:**

1. **الاتصال مباشرة**: 93 868 04 14
2. **بريد إلكتروني يدوي**: abdellahbaghalbachiri@gmail.com  
3. **الحضور إلى المكتب**: من 8 صباحاً إلى 2 ظهراً

خطأ: {str(e)}""",
                'es': f"""⚠️ **Error al procesar la justificación**

📄 **Alternativas para justificar la falta:**

1. **Llamar directamente**: 93 868 04 14
2. **Email manual**: abdellahbaghalbachiri@gmail.com  
3. **Presentarse en conserjería**: de 8h a 14h

Error: {str(e)}""",
                'ca': f"""⚠️ **Error al processar la justificació**

📄 **Alternatives per justificar la falta:**

1. **Trucar directament**: 93 868 04 14
2. **Email manual**: abdellahbaghalbachiri@gmail.com  
3. **Presentar-se a consergeria**: de 8h a 14h

Error: {str(e)}"""
            }
            return error_messages.get(language, error_messages['ca'])
    
    def _handle_teacher_contact_form(self, message: str, user_data: Dict, language: str) -> str:
        """Procesa el formulario de contacto con profesor"""
        try:
            # Obtener lista de profesores para mapeo
            teachers_list = self.get_teachers_list()
            teachers_map = {teacher['name']: teacher['email'] for teacher in teachers_list}
            
            # Parser simple y directo para evitar duplicaciones
            professor_name = ""
            subject = ""
            message_content = ""
            availability = ""
            
            # Buscar el nombre del profesor
            if "Contactar professor " in message:
                start = message.find("Contactar professor ") + len("Contactar professor ")
                end = message.find(" - Assumpte:", start)
                if end > start:
                    professor_name = message[start:end].strip()
            
            # Buscar el asunto (primera ocurrencia)
            if "Assumpte: " in message:
                start = message.find("Assumpte: ") + len("Assumpte: ")
                end = message.find(",", start)
                if end == -1:
                    end = message.find("\n", start)
                if end == -1:
                    end = len(message)
                subject = message[start:end].strip()
            
            # Buscar el mensaje
            if "Missatge: " in message:
                start = message.find("Missatge: ") + len("Missatge: ")
                end = message.find(", Disponibilitat:", start)
                if end == -1:
                    end = len(message)
                message_content = message[start:end].strip()
            
            # Buscar disponibilidad (opcional)
            if "Disponibilitat: " in message:
                start = message.find("Disponibilitat: ") + len("Disponibilitat: ")
                availability = message[start:].strip()
            
            # Limpieza final
            professor_name = professor_name.strip()
            subject = subject.strip()
            message_content = message_content.strip()
            availability = availability.strip()
            
            # Validar datos obligatorios
            if not all([professor_name, subject, message_content]):
                error_messages = {
                    'ar': "⚠️ يرجى ملء جميع الحقول المطلوبة (الأستاذ، الموضوع، الرسالة)",
                    'es': "⚠️ Por favor, completa todos los campos requeridos (profesor, asunto, mensaje)",
                    'ca': "⚠️ Si us plau, completa tots els camps requerits (professor, assumpte, missatge)"
                }
                return error_messages.get(language, error_messages['ca'])
            
            # Mapear asuntos
            subject_map = {
                'reunio': {'ca': 'Sol·licitud de reunió', 'es': 'Solicitud de reunión', 'ar': 'طلب اجتماع'},
                'consulta': {'ca': 'Consulta acadèmica', 'es': 'Consulta académica', 'ar': 'استفسار أكاديمي'}, 
                'seguiment': {'ca': 'Seguiment de l\'alumne', 'es': 'Seguimiento del alumno', 'ar': 'متابعة الطالب'},
                'altre': {'ca': 'Consulta general', 'es': 'Consulta general', 'ar': 'استفسار عام'}
            }
            
            subject_text = subject_map.get(subject.lower(), {}).get(language, subject)
            
            # Buscar el email exacto desde el mapeo de profesores
            professor_email = teachers_map.get(professor_name)
            
            # Si no se encuentra, generar automáticamente (fallback)
            if not professor_email:
                email_name = professor_name.lower().replace(' ', '.')
                # Limpiar caracteres especiales
                email_name = (email_name.replace('à', 'a').replace('è', 'e').replace('í', 'i')
                            .replace('ò', 'o').replace('ú', 'u').replace('ç', 'c')
                            .replace('ñ', 'n').replace('ü', 'u'))
                professor_email = f"{email_name}@inscalaf.cat"
            
            # Construir email
            email_subject = f"{subject_text} - {user_data.get('nom', 'Família')}"
            email_body = f"""Benvolgut/da {professor_name},

{message_content}

{f'Disponibilitat: {availability}' if availability and availability != 'None' else ''}

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
                    'ar': f"""✅ **تم إرسال الرسالة بنجاح!**

📧 المستلم: {professor_email}
👨‍🏫 الأستاذ/ة: {professor_name}
📋 الموضوع: {subject_text}

سيرد الأستاذ/ة على بريدك الإلكتروني في غضون 24-48 ساعة.""",
                    'es': f"""✅ **¡Mensaje enviado correctamente!**

📧 Destinatario: {professor_email}
👨‍🏫 Profesor/a: {professor_name}
📋 Asunto: {subject_text}

El profesor/a responderá a tu correo en un plazo de 24-48 horas.""",
                    'ca': f"""✅ **Missatge enviat correctament!**

📧 Destinatari: {professor_email}
👨‍🏫 Professor/a: {professor_name}
📋 Assumpte: {subject_text}

El professor/a respondrà al teu correu en un termini de 24-48 hores."""
                }
                return success_messages.get(language, success_messages['ca'])
            else:
                # Error simple
                error_messages = {
                    'ar': f"""❌ **خطأ في إرسال الرسالة**

خطأ: {result.get('error', 'مشكلة في الاتصال')}

📄 **بدائل:**
1. **الاتصال**: 93 868 04 14
2. **بريد إلكتروني يدوي**: {professor_email}
3. **الحضور شخصياً**: من 8 صباحاً إلى 2 ظهراً""",
                    'es': f"""❌ **Error al enviar el mensaje**

Error: {result.get('error', 'Problema de conexión')}

📄 **Alternativas:**
1. **Llamar**: 93 868 04 14
2. **Email manual**: {professor_email}
3. **Presentarse**: de 8h a 14h""",
                    'ca': f"""❌ **Error al enviar el missatge**

Error: {result.get('error', 'Problema de connexió')}

📄 **Alternatives:**
1. **Trucar**: 93 868 04 14
2. **Email manual**: {professor_email}
3. **Presentar-se**: de 8h a 14h"""
                }
                return error_messages.get(language, error_messages['ca'])
                
        except Exception as e:
            logger.error(f"Error contactando profesor: {str(e)}")
            error_messages = {
                'ar': f"""⚠️ **خطأ في الاتصال بالأستاذ**

📄 **بدائل للاتصال:**

1. **الاتصال بالمعهد**: 93 868 04 14
2. **بريد إلكتروني عام**: a8043395@xtec.cat
3. **الحضور شخصياً**: من 8 صباحاً إلى 2 ظهراً

خطأ: {str(e)}""",
                'es': f"""⚠️ **Error al contactar con el profesor**

📄 **Alternativas de contacto:**

1. **Llamar al instituto**: 93 868 04 14
2. **Email general**: a8043395@xtec.cat
3. **Presentarse personalmente**: de 8h a 14h

Error: {str(e)}""",
                'ca': f"""⚠️ **Error al contactar amb el professor**

📄 **Alternatives de contacte:**

1. **Trucar a l'institut**: 93 868 04 14
2. **Email general**: a8043395@xtec.cat
3. **Presentar-se personalment**: de 8h a 14h

Error: {str(e)}"""
            }
            return error_messages.get(language, error_messages['ca'])
    
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
            'files_loaded': len(self.uploaded_files),
            'csv_analyzer_available': CSV_ANALYZER_AVAILABLE,
            'api_key_configured': bool(os.environ.get("API_GEMINI")),
            'emailjs_configured': all([
                os.environ.get("EMAILJS_SERVICE_ID"),
                os.environ.get("EMAILJS_TEMPLATE_ID"),
                os.environ.get("EMAILJS_USER_ID")
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
        
        # Configuración
        health_report += f"{'✅' if status['api_key_configured'] else '❌'} API Gemini: {'Configurada' if status['api_key_configured'] else 'No configurada'}\n"
        health_report += f"{'✅' if status['emailjs_configured'] else '❌'} EmailJS: {'Configurado' if status['emailjs_configured'] else 'No configurado'}\n"
        
        # Archivos
        health_report += f"📁 Archivos cargados: {status['files_loaded']}\n"
        health_report += f"{'✅' if status['csv_analyzer_available'] else '⚠️'} CSV Analyzer: {'Disponible' if status['csv_analyzer_available'] else 'No disponible'}\n"
        
        return health_report

# Instancia global del bot
bot = RiquerChatBot()

# Funciones para integración
def process_user_message(message: str, history: List, user_name: str, user_contact: str) -> str:
    """Procesa mensajes en la interfaz"""
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
