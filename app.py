from flask import Flask, request, jsonify
import json
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# Detectar si estamos en Railway o en local
IS_RAILWAY = os.environ.get('PORT') is not None

# Ruta donde guardar los archivos
if IS_RAILWAY:
    # En Railway, guardar en el filesystem del contenedor
    JIRA_FOLDER = Path('/app/storage')
else:
    # En local, guardar en el escritorio
    DESKTOP_PATH = Path.home() / "Desktop"
    JIRA_FOLDER = DESKTOP_PATH / "JiraControlM"

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "OK",
        "message": "API está funcionando correctamente",
        "storage_folder": str(JIRA_FOLDER)
    })

@app.route('/save-json', methods=['POST'])
def save_json():
    try:
        # Obtener datos del request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
        
        # Validar que existan los campos requeridos
        if 'filename' not in data:
            return jsonify({"error": "Falta el campo 'filename'"}), 400
        
        if 'jsonData' not in data:
            return jsonify({"error": "Falta el campo 'jsonData'"}), 400
        
        filename = data['filename']
        json_data = data['jsonData']
        
        # Asegurarse de que el filename tenga extensión .json
        if not filename.endswith('.json'):
            filename = filename + '.json'
        
        # Crear la carpeta si no existe
        JIRA_FOLDER.mkdir(parents=True, exist_ok=True)
        
        # Ruta completa del archivo
        file_path = JIRA_FOLDER / filename
        
        # Guardar el archivo JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        # Información del archivo guardado
        file_stats = os.stat(file_path)
        
        return jsonify({
            "success": True,
            "message": "Archivo guardado exitosamente",
            "filename": filename,
            "path": str(file_path),
            "size_bytes": file_stats.st_size,
            "saved_at": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Error al procesar la solicitud",
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

if __name__ == '__main__':
    # Obtener el puerto de la variable de entorno o usar 5000 por defecto
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'  # Escuchar en todas las interfaces
    
    print(f"\n>>> API iniciada en http://{host}:{port}")
    print(f">>> Carpeta de guardado: {JIRA_FOLDER}")
    print(f">>> Entorno: {'Railway' if IS_RAILWAY else 'Local'}")
    print("\n>>> Endpoints disponibles:")
    print(f"   GET  /")
    print(f"   POST /save-json")
    print(f"   GET  /list-files")
    print("\n>>> Ejemplo de uso:")
    print(f'   curl -X POST /save-json')
    print(f'        -H "Content-Type: application/json"')
    print(f'        -d \'{{"filename":"mi_archivo","jsonData":{{"clave":"valor"}}}}\'')
    print()
    app.run(host=host, port=port, debug=False)

