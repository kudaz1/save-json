from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from pathlib import Path
from datetime import datetime
import logging

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Port configuration for Railway
port = os.environ.get('PORT', '8080')

# Detectar si estamos en Railway - verificar múltiples variables
RAILWAY_PORT = os.environ.get('PORT')
IS_RAILWAY = bool(RAILWAY_PORT)

# Ruta donde guardar los archivos
if IS_RAILWAY:
    # En Railway, guardar en el filesystem del contenedor
    JIRA_FOLDER = Path('/app/storage')
else:
    # En local, guardar en el escritorio
    DESKTOP_PATH = Path.home() / "Desktop"
    JIRA_FOLDER = DESKTOP_PATH / "JiraControlM"

# Crear la carpeta si no existe al iniciar
JIRA_FOLDER.mkdir(parents=True, exist_ok=True)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "OK",
        "message": "API esta funcionando correctamente"
    }), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/save-json', methods=['GET', 'POST', 'PUT', 'OPTIONS'])
def save_json():
    try:
        # RAILWAY HACK: Railway está convirtiendo POST a GET, así que debemos detectar los datos en request.args
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request args: {dict(request.args)}")
        logger.info(f"Request form: {dict(request.form)}")
        
        # Para OPTIONS request (CORS preflight)
        if request.method == 'OPTIONS':
            return '', 200
        
        # Intentar obtener data del body RAW (para cuando Postman envía POST pero el proxy lo convierte a GET)
        data = None
        
        # Primero intentar JSON normal
        data = request.get_json(silent=True)
        logger.info(f"Request data from JSON: {data}")
        
        # Si es GET, intentar leer el body directamente
        if not data and request.method == 'GET':
            try:
                raw_data = request.get_data(as_text=True)
                logger.info(f"Raw body data: {raw_data}")
                if raw_data:
                    data = json.loads(raw_data)
                    logger.info(f"Parsed data from raw body: {data}")
            except Exception as e:
                logger.error(f"Error parsing raw body: {e}")
        
        # Si no hay data JSON, intentar obtener de query params (para Railway que convierte a GET)
        if not data and request.args:
            try:
                import urllib.parse
                data_str = request.args.get('data') or request.args.get('body')
                if data_str:
                    data = json.loads(urllib.parse.unquote(data_str))
                    logger.info(f"Data from query params: {data}")
            except Exception as e:
                logger.error(f"Error parsing query data: {e}")
        
        # Si no hay data en POST, intentar obtener de form data
        if not data and request.method in ['POST', 'PUT']:
            data = request.form.to_dict()
            if data and 'jsonData' in data:
                try:
                    data['jsonData'] = json.loads(data['jsonData'])
                except:
                    pass
        
        if not data or 'filename' not in data or 'jsonData' not in data:
            error_msg = "Faltan campos requeridos"
            logger.error(f"{error_msg} - Method: {request.method} - Data: {data}")
            return jsonify({"error": error_msg, "received_method": request.method}), 400
        
        filename = data['filename']
        if not filename.endswith('.json'):
            filename = filename + '.json'
        
        file_path = JIRA_FOLDER / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data['jsonData'], f, indent=2, ensure_ascii=False)
        
        logger.info(f"File saved successfully: {file_path}")
        
        return jsonify({
            "success": True,
            "message": "Archivo guardado exitosamente",
            "filename": filename,
            "path": str(file_path)
        }), 200
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        return jsonify({
            "error": "Error al guardar el archivo",
            "details": str(e)
        }), 500

@app.route('/api/save', methods=['POST', 'PUT'])
def api_save():
    """Endpoint alternativo para guardar archivos"""
    return save_json()

@app.route('/upload', methods=['POST', 'PUT', 'GET', 'OPTIONS'])
def upload():
    """Endpoint simple que fuerza el método POST"""
    try:
        logger.info(f"UPLOAD endpoint - Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Para OPTIONS request (CORS preflight)
        if request.method == 'OPTIONS':
            return '', 200
        
        # Intentar obtener data de múltiples formas
        data = None
        
        # 1. Intentar JSON normal
        data = request.get_json(silent=True)
        
        # 2. Si es GET, intentar leer el body raw
        if not data and request.method == 'GET':
            try:
                raw_data = request.get_data(as_text=True)
                logger.info(f"Raw body data: {raw_data}")
                if raw_data:
                    data = json.loads(raw_data)
                    logger.info(f"Parsed data from raw body: {data}")
            except Exception as e:
                logger.error(f"Error parsing raw body: {e}")
        
        # 3. Intentar form data (x-www-form-urlencoded o multipart)
        if not data:
            form_data = request.form.to_dict()
            if form_data:
                data = form_data
                # Si hay jsonData como string, parsearlo
                if 'jsonData' in data and isinstance(data['jsonData'], str):
                    try:
                        data['jsonData'] = json.loads(data['jsonData'])
                    except:
                        pass
        
        # 4. Intentar leer del body como texto plano y parsearlo como JSON
        if not data:
            try:
                body_text = request.get_data(as_text=True)
                if body_text and body_text.strip():
                    logger.info(f"Body text: {body_text[:200]}...")  # Log primeros 200 chars
                    data = json.loads(body_text)
                    logger.info(f"Parsed data from body text: {data}")
            except Exception as e:
                logger.error(f"Error parsing body text: {e}")
        
        # 5. Intentar query params
        if not data and request.args:
            data = dict(request.args)
        
        logger.info(f"Request data: {data}")
        
        if not data or 'filename' not in data:
            return jsonify({
                "error": "Faltan campos requeridos",
                "received_data": data,
                "method": request.method
            }), 400
        
        filename = data.get('filename')
        jsonData = data.get('jsonData')
        
        if not jsonData:
            return jsonify({
                "error": "Falta jsonData",
                "received_data": data
            }), 400
        
        if not filename.endswith('.json'):
            filename = filename + '.json'
        
        file_path = JIRA_FOLDER / filename
        
        # Si jsonData es string, parsearlo
        if isinstance(jsonData, str):
            jsonData = json.loads(jsonData)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(jsonData, f, indent=2, ensure_ascii=False)
        
        logger.info(f"File saved successfully: {file_path}")
        
        return jsonify({
            "success": True,
            "message": "Archivo guardado exitosamente",
            "filename": filename,
            "path": str(file_path)
        }), 200
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return jsonify({
            "error": "Error al guardar el archivo",
            "details": str(e)
        }), 500

@app.route('/list-files', methods=['GET'])
def list_files():
    """Endpoint adicional para listar los archivos guardados"""
    try:
        if not JIRA_FOLDER.exists():
            return jsonify({
                "files": [],
                "message": "La carpeta JiraControlM no existe aún"
            })
        
        files = []
        for file in JIRA_FOLDER.glob("*.json"):
            file_stat = file.stat()
            files.append({
                "filename": file.name,
                "size_bytes": file_stat.st_size,
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            })
        
        return jsonify({
            "files": files,
            "total": len(files),
            "folder_path": str(JIRA_FOLDER)
        })
        
    except Exception as e:
        return jsonify({
            "error": "Error al listar archivos",
            "details": str(e)
        }), 500

# Railway uses gunicorn, no need for if __name__ == '__main__' block
