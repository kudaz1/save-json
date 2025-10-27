# API para Guardar Archivos JSON

API simple que recibe datos JSON y los guarda como archivos en una carpeta del escritorio.

## Instalación

1. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

## Uso

1. Iniciar el servidor:
```bash
python app.py
```

La API estará disponible en `http://localhost:5000`

## Endpoints

### 1. Guardar archivo JSON (POST)
**URL:** `http://localhost:5000/save-json`

**Body (JSON):**
```json
{
  "filename": "mi_archivo",
  "jsonData": {
    "clave1": "valor1",
    "clave2": "valor2"
  }
}
```

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "Archivo guardado exitosamente",
  "filename": "mi_archivo.json",
  "path": "C:\\Users\\Usuario\\Desktop\\JiraControlM\\mi_archivo.json",
  "size_bytes": 123,
  "saved_at": "2024-01-15T10:30:00"
}
```

### 2. Verificar estado (GET)
**URL:** `http://localhost:5000/`

Devuelve el estado de la API y la ruta donde se guardan los archivos.

### 3. Listar archivos (GET)
**URL:** `http://localhost:5000/list-files`

Lista todos los archivos JSON guardados en la carpeta JiraControlM.

## Ejemplo con cURL

```bash
curl -X POST http://localhost:5000/save-json \
     -H "Content-Type: application/json" \
     -d '{"filename":"test","jsonData":{"nombre":"Ejemplo","id":123}}'
```

## Ejemplo con PowerShell

```powershell
$body = @{
    filename = "mi_archivo"
    jsonData = @{
        clave1 = "valor1"
        clave2 = "valor2"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/save-json" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

## Notas

- La API crea automáticamente la carpeta `JiraControlM` en tu escritorio si no existe
- Si el nombre del archivo no termina en `.json`, se agrega automáticamente
- Los archivos se guardan con formato JSON con indentación de 2 espacios
- La API ejecuta en modo debug por defecto para facilitar el desarrollo


