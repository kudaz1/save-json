from flask import Flask, request, jsonify
import json
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

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

@app.route('/save-json', methods=['POST'])
def save_json():
    data = request.get_json()
    
    if not data or 'filename' not in data or 'jsonData' not in data:
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    filename = data['filename']
    if not filename.endswith('.json'):
        filename = filename + '.json'
    
    file_path = JIRA_FOLDER / filename
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data['jsonData'], f, indent=2, ensure_ascii=False)
    
    return jsonify({
        "success": True,
        "message": "Archivo guardado exitosamente",
        "filename": filename
    }), 200

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

