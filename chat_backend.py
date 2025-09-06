import google.generativeai as genai
import requests
import tempfile
import os
import json
import logging
from typing import Dict, List, Optional
import re
from datetime import datetime
import pandas as pd
from io import StringIO

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
        self.csv_data = {}  # Almacenar datos CSV parseados
        self.initialize_directories()
        self.initialize_files()
        self.initialize_chat()
    
    def initialize_directories(self):
        """Crear directorios necesarios"""
        os.makedirs('drive_files', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
    def download_file_with_retry(self, url: str, max_retries: int = 3) -> Optional[bytes]:
        """Descarga archivo con reintentos y mejor manejo de errores"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Intento {attempt + 1} descargando: {url}")
                
                # Headers para simular navegador
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
                
                response = requests.get(url, headers=headers, timeout=30, stream=True)
                response.raise_for_status()
                
                # Verificar content-type
                content_type = response.headers.get('content-type', '').lower()
                logger.info(f"Content-Type: {content_type}")
                
                # Leer contenido completo
                content = response.content
                
                # Validar que no sea una página de error de Google Drive
                if b'<!DOCTYPE html>' in content[:100] or b'<html' in content[:100]:
                    logger.warning(f"Recibido HTML en lugar del archivo. Posible problema con URL: {url}")
                    continue
                
                if len(content) < 50:  # Archivo muy pequeño, probablemente error
                    logger.warning(f"Archivo muy pequeño ({len(content)} bytes), posible error")
                    continue
                
                logger.info(f"Archivo descargado exitosamente: {len(content)} bytes")
                return content
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error descarga intento {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Falló descarga tras {max_retries} intentos: {url}")
                    return None
                
        return None
    
    def detect_file_type(self, content: bytes, url: str) -> str:
        """Detecta el tipo de archivo basado en contenido y URL"""
        # Verificar por contenido (más confiable)
        try:
            # Intentar decodificar como texto para ver si es CSV
            text_content = content.decode('utf-8')
            
            # Características de CSV
            lines = text_content.split('\n')[:5]  # Primeras 5 líneas
            has_separators = any(',' in line or ';' in line or '\t' in line for line in lines)
            
            if has_separators and not text_content.startswith('<!DOCTYPE'):
                return 'csv'
            else:
                return 'txt'
                
        except UnicodeDecodeError:
            # Si no se puede decodificar como UTF-8, probar otras codificaciones
            try:
                text_content = content.decode('latin-1')
                return 'csv' if ',' in text_content[:500] else 'txt'
            except:
                return 'unknown'
    
    def parse_csv_safely(self, content: bytes, file_id: str) -> Optional[pd.DataFrame]:
        """Parsea CSV de forma segura con múltiples intentos"""
        try:
            # Intentar diferentes codificaciones
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    text_content = content.decode(encoding)
                    logger.info(f"Archivo {file_id} decodificado con {encoding}")
                    
                    # Detectar separador
                    separators = [',', ';', '\t', '|']
                    best_separator = ','
                    max_columns = 0
                    
                    for sep in separators:
                        test_df = pd.read_csv(StringIO(text_content), sep=sep, nrows=5)
                        if len(test_df.columns) > max_columns:
                            max_columns = len(test_df.columns)
                            best_separator = sep
                    
                    # Parsear con el mejor separador
                    df = pd.read_csv(
                        StringIO(text_content), 
                        sep=best_separator,
                        encoding=None,  # Let pandas auto-detect
                        on_bad_lines='skip',  # Skip problematic lines
                        dtype=str  # Keep everything as string initially
                    )
                    
                    logger.info(f"CSV {file_id} parseado: {len(df)} filas, {len(df.columns)} columnas")
                    logger.info(f"Columnas: {list(df.columns)}")
                    
                    # Limpiar nombres de columnas
                    df.columns = df.columns.str.strip()
                    
                    return df
                    
                except Exception as e:
                    logger.warning(f"Error con encoding {encoding}: {str(e)}")
                    continue
            
            logger.error(f"No se pudo parsear CSV {file_id} con ninguna codificación")
            return None
            
        except Exception as e:
            logger.error(f"Error crítico parseando CSV {file_id}: {str(e)}")
            return None
    
    def initialize_files(self):
        """Descarga y carga los archivos CSV/TXT de Drive - VERSION MEJORADA"""
        file_urls = [
            "https://drive.google.com/uc?export=download&id=1neJFgTH0GWO5HbL64V6Fro0r1SKw8mFw",
            "https://drive.google.com/uc?export=download&id=1kOjm0jHpF-LqtXYC7uUC1HJAV7DQPBsy",
            "https://drive.google.com/uc?export=download&id=1iMfgjXLrn51EkYhCqMejJT7K5M5J5Ezy",
            "https://drive.google.com/uc?export=download&id=1N7Xpt9JSr1JPoIaju-ekIRW4NGVgPxMU",
            "https://drive.google.com/uc?export=download&id=1wRAoXk2vM0sZ8DmU-PiBJNiolHHMsAIJ",
        ]
        
        successful_downloads = 0
        
        for i, url in enumerate(file_urls):
            file_id = f"file_{i+1}"
            
            try:
                logger.info(f"Procesando archivo {i+1} de {len(file_urls)}")
                
                # Descargar archivo
                content = self.download_file_with_retry(url)
                if not content:
                    logger.error(f"No se pudo descargar {file_id}")
                    continue
                
                # Detectar tipo de archivo
                file_type = self.detect_file_type(content, url)
                file_extension = f".{file_type}"
                file_path = f"drive_files/{file_id}{file_extension}"
                
                # Guardar archivo localmente
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                logger.info(f"Archivo {file_id} guardado como {file_type}")
                
                # Procesar según tipo
                if file_type == 'csv':
                    # Parsear CSV
                    df = self.parse_csv_safely(content, file_id)
                    if df is not None:
                        self.csv_data[file_id] = df
                        
                        # Crear resumen para Gemini
                        summary = self.create_csv_summary(df, file_id)
                        self.uploaded_files.append(f"\n--- {file_id} (CSV) ---\n{summary}")
                        
                        successful_downloads += 1
                        logger.info(f"CSV {file_id} procesado exitosamente")
                    else:
                        logger.error(f"Error parseando CSV {file_id}")
                else:
                    # Procesar como texto
                    try:
                        text_content = content.decode('utf-8', errors='ignore')
                        self.uploaded_files.append(f"\n--- {file_id} (TXT) ---\n{text_content[:2000]}...")
                        successful_downloads += 1
                        logger.info(f"TXT {file_id} procesado exitosamente")
                    except Exception as e:
                        logger.error(f"Error procesando texto {file_id}: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error general procesando {file_id}: {str(e)}")
                continue
        
        logger.info(f"Archivos procesados exitosamente: {successful_downloads}/{len(file_urls)}")
        logger.info(f"CSVs cargados: {len(self.csv_data)}")
    
    def create_csv_summary(self, df: pd.DataFrame, file_id: str) -> str:
        """Crea un resumen del CSV para el contexto de Gemini"""
        try:
            summary = f"Archivo CSV: {file_id}\n"
            summary += f"Filas: {len(df)}, Columnas: {len(df.columns)}\n"
            summary += f"Columnas: {', '.join(df.columns.tolist())}\n\n"
            
            # Mostrar algunas filas de ejemplo
            summary += "Primeras filas:\n"
            summary += df.head(3).to_string(index=False, max_cols=8)
            
            # Si tiene muchas columnas, mostrar solo las primeras
            if len(df.columns) > 8:
                summary += f"\n... y {len(df.columns) - 8} columnas más"
            
            # Información adicional sobre contenido
            for col in df.columns[:5]:  # Solo primeras 5 columnas
                unique_values = df[col].dropna().unique()
                if len(unique_values) <= 10:
                    summary += f"\n{col}: {', '.join(map(str, unique_values[:5]))}"
                else:
                    summary += f"\n{col}: {len(unique_values)} valores únicos"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creando resumen CSV {file_id}: {str(e)}")
            return f"Error creando resumen del archivo {file_id}"
    
    def search_in_csvs(self, query: str) -> str:
        """Busca información en los CSVs cargados"""
        results = []
        
        if not self.csv_data:
            return "No hay archivos CSV disponibles para buscar."
        
        query_lower = query.lower()
        
        for file_id, df in self.csv_data.items():
            try:
                matches = []
                
                # Buscar en todas las columnas de texto
                for col in df.columns:
                    if df[col].dtype == 'object':  # Columnas de texto
                        mask = df[col].astype(str).str.lower().str.contains(query_lower, na=False)
                        matching_rows = df[mask]
                        
                        if not matching_rows.empty:
                            matches.extend(matching_rows.to_dict('records'))
                
                if matches:
                    results.append(f"\n=== {file_id} ===")
                    for match in matches[:3]:  # Limitar resultados
                        result_str = ", ".join([f"{k}: {v}" for k, v in match.items() if v and str(v).strip()])
                        results.append(result_str)
                
            except Exception as e:
                logger.error(f"Error buscando en {file_id}: {str(e)}")
                continue
        
        return "\n".join(results) if results else f"No se encontraron resultados para '{query}'"
    
    def get_teachers_list(self) -> List[Dict]:
        """Obtiene la lista de profesores desde los CSV para el formulario"""
        teachers = []
        
        # Buscar en CSVs cargados
        for file_id, df in self.csv_data.items():
            try:
                # Buscar columnas que puedan contener nombres de profesores
                name_columns = [col for col in df.columns if any(keyword in col.lower() 
                    for keyword in ['profesor', 'teacher', 'docent', 'name', 'nom'])]
                
                for col in name_columns:
                    names = df[col].dropna().unique()
                    for name in names:
                        if isinstance(name, str) and len(name.split()) >= 2:
                            # Generar email
                            email = name.lower().replace(' ', '.')
                            email = (email.replace('à', 'a').replace('è', 'e').replace('í', 'i')
                                    .replace('ò', 'o').replace('ú', 'u').replace('ç', 'c')
                                    .replace('ñ', 'n').replace('ü', 'u'))
                            email = f"{email}@inscalaf.cat"
                            
                            teachers.append({'name': name, 'email': email})
                
            except Exception as e:
                logger.error(f"Error extrayendo profesores de {file_id}: {str(e)}")
                continue
        
        # Añadir profesores fijos como fallback
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
        
        # Ordenar y limitar
        teachers.sort(key=lambda x: x['name'])
        return teachers[:20]  # Limitar a 20
    
    def get_csv_info(self, query: str) -> str:
        """Obtiene información específica de los archivos CSV"""
        csv_info = ""
        
        # Buscar en CSVs propios
        if self.csv_data:
            search_results = self.search_in_csvs(query)
            if search_results and "No se encontraron" not in search_results:
                csv_info += f"\n\nInformació dels arxius de l'institut:\n{search_results}"
        
        # Intentar usar CSV analyzer si está disponible
        if CSV_ANALYZER_AVAILABLE:
            try:
                # Buscar información en los CSV
                search_results = search_csv_info(query)
                if search_results:
                    csv_info += f"\n\nInformació adicional:\n{search_results}"
                
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
                logger.warning(f"Error obteniendo información CSV analyzer: {str(e)}")
        
        return csv_info
    
    # ... resto de métodos sin cambios ...
    
    def get_system_status(self) -> Dict:
        """Obtiene el estado del sistema"""
        status = {
            'chat_initialized': self.chat is not None,
            'model_available': self.model is not None,
            'files_loaded': len(self.uploaded_files),
            'csv_files_loaded': len(self.csv_data),
            'csv_analyzer_available': CSV_ANALYZER_AVAILABLE,
            'api_key_configured': bool(os.environ.get("API_GEMINI")),
            'mailgun_configured': all([
                os.environ.get("MAILGUN_API_KEY"),
                os.environ.get("MAILGUN_DOMAIN")
            ])
        }
        
        return status
