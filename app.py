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
elif os.environ.get('RENDER'):
    # En Render, usar tmp para escritura
    JIRA_FOLDER = Path('/tmp/storage')
else:
    # En local, guardar en el escritorio
    DESKTOP_PATH = Path.home() / "Desktop"
    JIRA_FOLDER = DESKTOP_PATH / "JiraControlM"

# Crear la carpeta si no existe al iniciar
try:
    JIRA_FOLDER.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logger.error(f"Error creating directory {JIRA_FOLDER}: {e}")
    # En caso de error, intentar con una ruta alternativa
    JIRA_FOLDER = Path('.') / 'storage'
    JIRA_FOLDER.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using alternative path: {JIRA_FOLDER}")

def save_file_with_data(filename, jsonData):
    """Helper function to save file with data"""
    if not filename.endswith('.json'):
        filename = filename + '.json'
    
    file_path = JIRA_FOLDER / filename
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(jsonData, f, indent=2, ensure_ascii=False)
    
    logger.info(f"File saved successfully: {file_path}")
    return file_path

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "OK",
        "message": "API esta funcionando correctamente"
    }), 200

@app.route('/test', methods=['GET', 'POST'])
def test():
    """Endpoint de prueba para ver qué recibe Railway"""
    return jsonify({
        "method": request.method,
        "has_json": request.is_json,
        "headers": dict(request.headers),
        "args": dict(request.args),
        "form": dict(request.form),
        "json_data": request.get_json(silent=True),
        "raw_body": request.get_data(as_text=True)[:200] if request.get_data(as_text=True) else None
    }), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/save-json', methods=['GET', 'POST', 'PUT', 'OPTIONS'])
def save_json():
    """
    Endpoint principal para guardar archivos JSON.
    
    Body esperado (JSON):
    {
      "filename": "nombre_archivo",
      "token": "tu_token_controlm",     // OPCIONAL: Si se envía, automáticamente se envía a Control-M
      "controlm_api": "https://...",    // OPCIONAL: URL de Control-M (por defecto usa la de la imagen)
      "jsonData": {...}
    }
    """
    try:
        # Autenticación por token (si se envía)
        token = None
        controlm_api = 'https://controlms1de01:8446/automation-api/deploy'
        # RAILWAY HACK: Railway está convirtiendo POST a GET, así que debemos detectar los datos en request.args
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request args: {dict(request.args)}")
        logger.info(f"Request form: {dict(request.form)}")
        
        # Para OPTIONS request (CORS preflight)
        if request.method == 'OPTIONS':
            return '', 200
        
        # SOLUCION RAILWAY: Leer primero de query params ya que Railway convierte POST a GET
        # y elimina el body. Esta es la única forma de que funcione en Railway
        if request.args:
            logger.info(f"Reading from query params: {dict(request.args)}")
            filename = request.args.get('filename')
            jsonData_str = request.args.get('jsonData')
            
            if filename and jsonData_str:
                try:
                    jsonData = json.loads(jsonData_str)
                    return jsonify({
                        "success": True,
                        "message": "Archivo guardado exitosamente",
                        "filename": filename,
                        "path": str(save_file_with_data(filename, jsonData))
                    }), 200
                except Exception as e:
                    logger.error(f"Error parsing JSON from query params: {e}")
                    return jsonify({"error": "Error parsing JSON", "details": str(e)}), 400
        
        # Intentar obtener data del body RAW (para cuando Postman envía POST pero el proxy lo convierte a GET)
        data = None
        
        # Primero intentar JSON normal
        data = request.get_json(silent=True)
        logger.info(f"Request data from JSON: {data}")
        
        # Si es GET, intentar leer el body directamente - FORZAR lectura
        if not data:
            try:
                raw_data = request.get_data(as_text=True, cache=True)
                logger.info(f"Raw body data length: {len(raw_data) if raw_data else 0}")
                if raw_data and raw_data.strip():
                    logger.info(f"Raw body data: {raw_data[:500]}...")
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
        
        # Extraer token y controlm_api si se envían
        token = data.get('token')
        controlm_api_url = data.get('controlm_api', 'https://controlms1de01:8446/automation-api/deploy')
        
        filename = data['filename']
        if not filename.endswith('.json'):
            filename = filename + '.json'
        
        file_path = JIRA_FOLDER / filename
        
        # Guardar archivo
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data['jsonData'], f, indent=2, ensure_ascii=False)
        
        logger.info(f"File saved successfully: {file_path}")
        
        response_data = {
            "success": True,
            "message": "Archivo guardado exitosamente",
            "filename": filename,
            "path": str(file_path)
        }
        
        # Si se envió token, automáticamente enviar a Control-M
        if token:
            logger.info("="*80)
            logger.info("Enviando archivo a Control-M...")
            logger.info("="*80)
            logger.info(f"Control-M API URL: {controlm_api_url}")
            logger.info(f"Filename: {filename}")
            logger.info(f"Token: {token[:20]}..." if len(token) > 20 else f"Token: {token}")
            logger.info(f"Request format: form-data")
            logger.info(f"Field name: definitionsFile")
            logger.info(f"Content-Type: application/json")
            logger.info("="*80)
            
            try:
                import requests
                
                headers = {'Authorization': f'Bearer {token}'}
                logger.info(f"Headers: {headers}")
                
                # Leer archivo una vez para logging
                with open(file_path, 'rb') as file_content:
                    file_data = file_content.read()
                    logger.info(f"File size: {len(file_data)} bytes")
                
                # Enviar archivo
                with open(file_path, 'rb') as f:
                    files = {'definitionsFile': (filename, f, 'application/json')}
                    logger.info(f"Files payload key: definitionsFile")
                    logger.info(f"Files payload value: (filename={filename}, file=FILE, content_type=application/json)")
                    
                    logger.info(f"Sending POST to: {controlm_api_url}")
                    logger.info(f"Method: POST")
                    logger.info(f"Content-Type: multipart/form-data (automatically set by requests library)")
                    
                    controlm_response = requests.post(
                        controlm_api_url,
                        files=files,
                        headers=headers,
                        verify=False,
                        timeout=30
                    )
                
                logger.info("="*80)
                logger.info(f"Control-M response status: {controlm_response.status_code}")
                logger.info(f"Control-M response headers: {dict(controlm_response.headers)}")
                logger.info(f"Control-M response body: {controlm_response.text[:500]}")
                logger.info("="*80)
                
                if controlm_response.status_code in [200, 201]:
                    response_data['controlm_status'] = 'success'
                    response_data['controlm_response'] = controlm_response.text[:500]
                else:
                    response_data['controlm_status'] = 'error'
                    response_data['controlm_error'] = controlm_response.text[:500]
                    
            except Exception as e:
                logger.error(f"Error enviando a Control-M: {e}")
                response_data['controlm_status'] = 'error'
                response_data['controlm_error'] = str(e)
        
        return jsonify(response_data), 200
        
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

@app.route('/save', methods=['GET'])
def save_simple():
    """Endpoint simplificado SOLO con query params para Railway"""
    try:
        filename = request.args.get('filename')
        jsonData_str = request.args.get('jsonData')
        
        if not filename or not jsonData_str:
            return jsonify({
                "error": "Missing required parameters",
                "required": ["filename", "jsonData"]
            }), 400
        
        try:
            jsonData = json.loads(jsonData_str)
        except json.JSONDecodeError as e:
            return jsonify({
                "error": "Invalid JSON in jsonData parameter",
                "details": str(e)
            }), 400
        
        file_path = save_file_with_data(filename, jsonData)
        
        return jsonify({
            "success": True,
            "message": "Archivo guardado exitosamente",
            "filename": filename if filename.endswith('.json') else filename + '.json',
            "path": str(file_path)
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /save endpoint: {str(e)}")
        return jsonify({
            "error": "Error al guardar el archivo",
            "details": str(e)
        }), 500

@app.route('/upload', methods=['POST', 'PUT', 'GET', 'OPTIONS'])
def upload():
    """Endpoint simple que fuerza el método POST"""
    try:
        logger.info(f"UPLOAD endpoint - Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Para OPTIONS request (CORS preflight)
        if request.method == 'OPTIONS':
            return '', 200
        
        # SOLUCION: Leer de query params ya que Railway convierte POST a GET
        # Y elimina el body. Esta es la única forma de que funcione en Railway
        if request.args:
            logger.info(f"Reading from query params: {dict(request.args)}")
            filename = request.args.get('filename')
            jsonData_str = request.args.get('jsonData')
            
            if filename and jsonData_str:
                try:
                    jsonData = json.loads(jsonData_str)
                    return jsonify({
                        "success": True,
                        "message": "Archivo guardado exitosamente",
                        "filename": filename,
                        "path": str(save_file_with_data(filename, jsonData))
                    }), 200
                except Exception as e:
                    logger.error(f"Error parsing JSON from query params: {e}")
                    return jsonify({"error": "Error parsing JSON", "details": str(e)}), 400
            else:
                return jsonify({"error": "Missing filename or jsonData in query params"}), 400
        
        # Intentar obtener data de múltiples formas
        data = None
        
        # 1. Intentar JSON normal
        data = request.get_json(silent=True)
        
        # 2. Si es GET, intentar leer el body raw - FORZAR lectura del body
        if not data:
            try:
                # Leer el body directamente del request stream
                raw_data = request.get_data(as_text=True, cache=True)
                logger.info(f"Raw body data length: {len(raw_data) if raw_data else 0}")
                if raw_data and raw_data.strip():
                    logger.info(f"Raw body data: {raw_data[:500]}...")  # Primeros 500 chars
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

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Endpoint para descargar archivos guardados"""
    try:
        if not filename.endswith('.json'):
            filename = filename + '.json'
        
        file_path = JIRA_FOLDER / filename
        
        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404
        
        from flask import send_file
        return send_file(str(file_path), as_attachment=True)
        
    except Exception as e:
        return jsonify({
            "error": "Error downloading file",
            "details": str(e)
        }), 500

@app.route('/deploy-to-controlm/<filename>', methods=['POST'])
def deploy_to_controlm(filename):
    """Endpoint para enviar archivo a Control-M con token"""
    try:
        logger.info(f"Deploy to Control-M request for: {filename}")
        logger.info(f"Request data: {request.get_json()}")
        
        # Obtener token del body
        data = request.get_json()
        if not data or 'token' not in data:
            return jsonify({
                "error": "Token is required",
                "required_fields": ["token"]
            }), 400
        
        token = data['token']
        
        # Control-M API endpoint
        controlm_api = data.get('controlm_api', 'https://controlms1de01:8446/automation-api/deploy')
        
        # Verificar que el archivo existe
        if not filename.endswith('.json'):
            filename = filename + '.json'
        
        file_path = JIRA_FOLDER / filename
        
        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404
        
        logger.info(f"File found: {file_path}")
        logger.info(f"Sending to Control-M API: {controlm_api}")
        
        # Enviar archivo a Control-M usando form-data
        import requests
        
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        with open(file_path, 'rb') as f:
            files = {
                'definitionsFile': (filename, f, 'application/json')
            }
            
            try:
                controlm_response = requests.post(
                    controlm_api,
                    files=files,
                    headers=headers,
                    verify=False,
                    timeout=30
                )
                
                logger.info(f"Control-M response status: {controlm_response.status_code}")
                logger.info(f"Control-M response: {controlm_response.text[:500]}")
                
                if controlm_response.status_code in [200, 201]:
                    return jsonify({
                        "success": True,
                        "message": "File deployed successfully to Control-M",
                        "filename": filename,
                        "controlm_response": controlm_response.text[:500]
                    }), 200
                else:
                    return jsonify({
                        "error": "Control-M API error",
                        "status_code": controlm_response.status_code,
                        "response": controlm_response.text[:500]
                    }), controlm_response.status_code
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling Control-M API: {str(e)}")
                return jsonify({
                    "error": "Failed to connect to Control-M",
                    "details": str(e)
                }), 500
        
    except Exception as e:
        logger.error(f"Error in deploy_to_controlm: {str(e)}")
        return jsonify({
            "error": "Error sending to Control-M",
            "details": str(e)
        }), 500

# Railway uses gunicorn, no need for if __name__ == '__main__' block
