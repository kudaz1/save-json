# API para Guardar Archivos JSON - Deploy en Render

## Instrucciones para deploy en Render

1. Ve a https://render.com y crea una cuenta (gratis)
2. Conecta tu repositorio de GitHub
3. Selecciona "New Web Service"
4. Configuración:
   - **Name:** save-json-api
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 4`
   - **Plan:** Free

5. Click en "Create Web Service"

## Uso de la API

Una vez desplegado, tu URL será: `https://save-json-api.onrender.com`

### Endpoint principal: POST con Body

**URL:** `https://save-json-api.onrender.com/save-json`

**Método:** `POST`

**Content-Type:** `application/json`

**Body:**
```json
{
  "filename": "mi_archivo",
  "jsonData": {
    "key": "value"
  }
}
```

## Nota importante

Render respeta el método POST y el body JSON, a diferencia de Railway que los convierte a GET.

