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
            "https://drive.google.com/uc?export=download&id=1wRAoXk2vM0sZ8DmU-PiBJNiolHHMsAIJ",
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
                
                # Para Gemini, leer el contenido (manejo de errores de encoding)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Si falla UTF-8, probar con latin-1
                    with open(file_path, 'r', encoding='latin-1') as f:
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
    
    def detect_language(self, message: str) -> str:
        """Detecta el idioma del mensaje de forma más precisa"""
        message_lower = message.lower()
        
        # Detectar árabe por caracteres árabes
        arabic_chars = 'أبتثجحخدذرزسشصضطظعغفقكلمنهويةآإؤئـ'
        if any(char in arabic_chars for char in message):
            return 'ar'
        
        # Palabras distintivas por idioma (más específicas)
        catalan_indicators = [
            # Palabras muy características del catalán
            'què', 'com', 'quan', 'on', 'per què', 'amb', 'són', 'està', 'estan', 
            'hem', 'han', 'tinc', 'tens', 'som', 'sou', 'volem', 'voleu',
            'alumne', 'professor', 'institut', 'curs', 'hora', 'dia',
            'matí', 'tarda', 'nit', 'any', 'mes', 'setmana',
            'català', 'castellà', 'anglès', 'francès',
            'bon', 'bona', 'bones', 'bons', 'molt', 'molta', 'molts', 'moltes'
        ]
        
        spanish_indicators = [
            # Palabras muy características del español
            'qué', 'cómo', 'cuándo', 'dónde', 'por qué', 'con', 'son', 'está', 'están',
            'hemos', 'han', 'tengo', 'tienes', 'somos', 'sois', 'queremos', 'queréis',
            'alumno', 'profesor', 'instituto', 'curso', 'hora', 'día',
            'mañana', 'tarde', 'noche', 'año', 'mes', 'semana',
            'español', 'catalán', 'inglés', 'francés',
            'buen', 'buena', 'buenas', 'buenos', 'mucho', 'mucha', 'muchos', 'muchas'
        ]
        
        # Contar indicadores con peso
        catalan_score = 0
        spanish_score = 0
        
        for indicator in catalan_indicators:
            if indicator in message_lower:
                catalan_score += 2  # Peso mayor para palabras distintivas
        
        for indicator in spanish_indicators:
            if indicator in message_lower:
                spanish_score += 2
        
        # Patrones adicionales
        if any(pattern in message_lower for pattern in ['qué tal', 'buenos días', 'buenas tardes', 'buenas noches']):
            spanish_score += 3
        
        if any(pattern in message_lower for pattern in ['com va', 'bon dia', 'bona tarda', 'bona nit']):
            catalan_score += 3
        
        # Decidir idioma
        if spanish_score > catalan_score:
            return 'es'
        elif catalan_score > spanish_score:
            return 'ca'
        else:
            # Si no hay indicadores claros, mantener el idioma anterior o usar catalán por defecto
            return 'ca'
    
    def initialize_chat(self):
        """Inicializa el chat con Gemini - VERSIÓN MULTILINGÜE CORREGIDA"""
        try:
            # Crear el modelo
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Contexto NEUTRAL y multilingüe
            context = """
            You are Riquer, a multilingual assistant for Institut Alexandre de Riquer in Calaf.
            You are friendly, professional and efficient.
            
            CRITICAL LANGUAGE RULE:
            - If someone writes in Catalan → respond in Catalan
            - If someone writes in Spanish → respond in Spanish  
            - If someone writes in Arabic → respond in Arabic
            - ALWAYS detect the input language and respond in the SAME language
            
            IMPORTANT RULES:
            1. Auto-detect message language and respond in that exact language
            2. Only answer questions related to the institute
            3. For teacher contact, help prepare an email
            4. For absence justification, send to 'abdellahbaghalbachiri@gmail.com'
            5. For teacher contact, ask for teacher name and reason
            6. Be concise but complete
            7. Use emojis moderately
            8. If email issues, always offer alternatives
            9. ONLY use information from institute CSV files - DO NOT invent information
            10. If specific info not found in files, explain it's not available
            
            INSTITUTE INFO:
            - Name: Institut Alexandre de Riquer
            - Address: C. Sant Joan Bta. de la Salle 6-8, 08280 Calaf (Anoia)
            - Phone: 93 868 04 14
            - General email: a8043395@xtec.cat
            - Web: http://www.inscalaf.cat
            - Reception: abdellahbaghalbachiri@gmail.com
            
            SCHEDULES:
            - School hours: mornings 8:00 to 14:35
            - Public attention: Monday to Friday 8:00 to 14:00h
            - Secretary: Monday to Friday 9:00 to 13:00h
            
            AVAILABLE COURSES:
            - ESO (1st, 2nd, 3rd, 4th)
            - Bachillerato (1st, 2nd)
            - Vocational Training (Medium and Higher Level)
            
            EMAIL INSTRUCTIONS:
            - For absence justification, ask: student name, course, date and reason
            - For teacher contact, ask teacher name and reason
            - Always confirm before indicating an email will be sent
            - If technical issues, offer alternatives: phone, manual email, in-person
            
            Remember: ALWAYS respond in the input message language and ONLY with CSV file information.
            """
            
            # Iniciar chat con contexto neutral
            initial_context = context + "\n\nInstitute file information:"
            if self.uploaded_files:
                initial_context += "\n".join(self.uploaded_files[:3])
            
            # Respuesta inicial NEUTRAL
            self.chat = self.model.start_chat(history=[
                {"role": "user", "parts": [initial_context]},
                {"role": "model", "parts": ["Understood! I'm Riquer, the multilingual virtual assistant of Institut Alexandre de Riquer. I can help you in Catalan, Spanish and Arabic based exclusively on institute file information. How can I help you today?"]}
            ])
            
            logger.info("Chat inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando el chat: {str(e)}")
            self.model = None
            self.chat = None
    
    def _verify_response_language(self, response: str, expected_language: str) -> bool:
        """Verifica si la respuesta está en el idioma esperado"""
        response_lower = response.lower()
        
        # Palabras indicadoras por idioma
        language_indicators = {
            'ca': ['com', 'què', 'som', 'està', 'són', 'molt', 'bon', 'professor', 'alumne', 'institut', 'puc', 'ajudar'],
            'es': ['cómo', 'qué', 'somos', 'está', 'son', 'mucho', 'buen', 'profesor', 'alumno', 'instituto', 'puedo', 'ayudar'], 
            'ar': ['كيف', 'ما', 'نحن', 'هو', 'هي', 'كثير', 'جيد', 'أستاذ', 'طالب', 'معهد', 'يمكنني', 'مساعدة']
        }
        
        if expected_language not in language_indicators:
            return True  # Si no podemos verificar, asumimos que está bien
        
        expected_words = language_indicators[expected_language]
        found_count = sum(1 for word in expected_words if word in response_lower)
        
        # Si encuentra al menos 1 palabra del idioma esperado, consideramos que está bien
        return found_count > 0
    
    def process_message(self, message: str, user_data: Dict) -> str:
        """Procesa un mensaje del usuario - VERSIÓN CORREGIDA FINAL"""
        try:
            if not self.chat:
                return "Ho sento, hi ha hagut un problema tècnic. Si us plau, recarrega la pàgina."
            
            # PASO 1: Detectar idioma por prefijo (PRIORIDAD MÁXIMA)
            detected_language = 'ca'  # Por defecto
            original_message = message
            
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
                # Si no hay prefijo, detectar automáticamente
                detected_language = self.detect_language(message)
            
            # PASO 2: Logging para debug
            logger.info(f"Idioma detectado: {detected_language} para mensaje: {message[:50]}...")
            
            # PASO 3: Instrucciones SÚPER CLARAS por idioma
            language_commands = {
                'ca': """
ORDRE ABSOLUTA: Respon NOMÉS en idioma CATALÀ.
Utilitza paraules catalanes, gramàtica catalana, expressions catalanes.
Exemples correctes: "Com puc ajudar-te?", "Quin professor vols contactar?", "Perfecte!", "Molt bé!"
PROHIBIT respondre en espanyol o altres idiomes.
""",
                'es': """
ORDEN ABSOLUTA: Responde ÚNICAMENTE en idioma ESPAÑOL.
Utiliza palabras españolas, gramática española, expresiones españolas.
Ejemplos correctos: "¿Cómo puedo ayudarte?", "¿Qué profesor quieres contactar?", "¡Perfecto!", "¡Muy bien!"
PROHIBIDO responder en catalán o otros idiomas.
""",
                'ar': """
أمر مطلق: أجب فقط باللغة العربية.
استخدم كلمات عربية، قواعد عربية، تعبيرات عربية.
أمثلة صحيحة: "كيف يمكنني مساعدتك؟"، "أي أستاذ تريد التواصل معه؟"، "ممتاز!"، "جيد جداً!"
ممنوع الرد بالكتالانية أو الإسبانية أو لغات أخرى.
"""
            }
            
            # PASO 4: Obtener información CSV
            csv_info = self.get_csv_info(message)
            
            # PASO 5: Construir mensaje con comando de idioma MUY CLARO
            full_message = f"""{language_commands.get(detected_language, language_commands['ca'])}

Usuario: {user_data.get('nom', 'Desconocido')}
Pregunta: {message}{csv_info}

IDIOMA DE RESPUESTA OBLIGATORIO: {detected_language.upper()}
RESPONDE SOLO EN {detected_language.upper()}."""
            
            # PASO 6: Verificar si es formulario
            if self._is_form_submission(message):
                return self._handle_form_submission(message, user_data, detected_language)
            
            # PASO 7: Enviar a Gemini
            response = self.chat.send_message(full_message)
            response_text = response.text
            
            # PASO 8: Verificar idioma de respuesta (failsafe)
            if not self._verify_response_language(response_text, detected_language):
                logger.warning(f"Respuesta en idioma incorrecto. Reintentando...")
                # Reintento con instrucción aún más fuerte
                force_message = f"""
¡ATENCIÓN! Tu respuesta anterior NO estaba en {detected_language.upper()}.
{language_commands.get(detected_language)}

REESCRIBE tu respuesta anterior COMPLETAMENTE en {detected_language.upper()}.
Usuario: {user_data.get('nom', 'Desconocido')}
Pregunta original: {message}

RESPUESTA OBLIGATORIA EN {detected_language.upper()}:
"""
                response = self.chat.send_message(force_message)
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
                # Error con alternativas
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

{f'Disponibilitat: {availability}' if availability and availability != 'None' and availability != 'No especificada' else ''}

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
                # Error con alternativas
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
        
        # Configuración
        health_report += f"{'✅' if status['api_key_configured'] else '❌'} API Gemini: {'Configurada' if status['api_key_configured'] else 'No configurada'}\n"
        health_report += f"{'✅' if status['mailgun_configured'] else '❌'} Mailgun: {'Configurado' if status['mailgun_configured'] else 'No configurado'}\n"
        
        # Archivos
        health_report += f"📁 Archivos cargados: {status['files_loaded']}\n"
        health_report += f"{'✅' if status['csv_analyzer_available'] else '⚠️'} CSV Analyzer: {'Disponible' if status['csv_analyzer_available'] else 'No disponible'}\n"
        
        return health_report

# Instancia global del bot
bot = RiquerChatBot()

# Funciones para integración con Flask/FastAPI
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

# =============================================
# ENDPOINT FLASK MEJORADO
# =============================================

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Cambiar por una clave segura
CORS(app)

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint principal del chat con soporte multilingüe mejorado"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Obtener datos del request
        message = data.get('message', '').strip()
        user_name = data.get('user_name', 'Usuario')
        user_contact = data.get('user_contact', '')
        language = data.get('language', 'ca')  # Idioma del frontend
        
        if not message:
            return jsonify({'error': 'Empty message'}), 400
        
        # Si no hay prefijo de idioma pero sí idioma del frontend, agregarlo
        language_prefixes = ['[CA] ', '[ES] ', '[AR] ']
        if not any(message.startswith(prefix) for prefix in language_prefixes):
            prefix_map = {'ca': '[CA] ', 'es': '[ES] ', 'ar': '[AR] '}
            message = prefix_map.get(language, '[CA] ') + message
        
        # Preparar datos del usuario
        user_data = {
            'nom': user_name,
            'contacte': user_contact
        }
        
        # Logging para debug
        logger.info(f"Procesando mensaje: {message[:50]}... | Usuario: {user_name} | Idioma: {language}")
        
        # Procesar mensaje
        response = bot.process_message(message, user_data)
        
        # Logging de respuesta
        logger.info(f"Respuesta generada: {response[:100]}...")
        
        return jsonify({
            'response': response,
            'language': language,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error en /chat: {str(e)}")
        
        # Respuesta de error en el idioma solicitado si está disponible
        error_messages = {
            'ar': "عذراً، حدث خطأ في الخادم. يرجى المحاولة مرة أخرى.",
            'es': "Lo siento, ha ocurrido un error en el servidor. Por favor, inténtalo de nuevo.",
            'ca': "Ho sento, hi ha hagut un error al servidor. Si us plau, torna-ho a intentar."
        }
        
        language = data.get('language', 'ca') if data else 'ca'
        error_msg = error_messages.get(language, error_messages['ca'])
        
        return jsonify({
            'error': error_msg,
            'technical_error': str(e),
            'language': language
        }), 500

@app.route('/teachers', methods=['GET'])
def get_teachers():
    """Endpoint para obtener la lista de profesores"""
    try:
        teachers = bot.get_teachers_list()
        return jsonify({'teachers': teachers})
    except Exception as e:
        logger.error(f"Error obteniendo profesores: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check"""
    try:
        status = bot.get_system_status()
        health_report = bot.health_check()
        
        return jsonify({
            'status': 'healthy' if status['chat_initialized'] else 'unhealthy',
            'details': status,
            'report': health_report,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/status', methods=['GET'])
def status():
    """Endpoint de estado detallado del sistema"""
    try:
        status = bot.get_system_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error obteniendo status: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Manejo de errores globales
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Configuración para desarrollo
    app.run(debug=True, host='0.0.0.0', port=5000)
