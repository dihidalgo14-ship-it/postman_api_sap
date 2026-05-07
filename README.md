# SAP API Client 🔷
> Herramienta de escritorio estilo Postman para consultar SAP S/4HANA Cloud OData APIs y exportar a Excel/CSV.

---

## 📦 Estructura del proyecto

```
sap_client/
├── src/
│   └── app.py              ← Aplicación principal
├── .vscode/
│   ├── launch.json         ← Configuración de ejecución y compilación
│   └── settings.json       ← Settings del workspace
├── requirements.txt        ← Dependencias Python
├── build.bat               ← Script para generar el .exe (doble clic)
├── SAP_API_Client.spec     ← Config avanzada de PyInstaller
└── README.md
```

---

## 🚀 Instalación rápida

### Requisitos previos
- **Python 3.9 o superior** → [python.org/downloads](https://python.org/downloads)
  - ⚠️ Marcar "Add Python to PATH" al instalar
- **VS Code** → [code.visualstudio.com](https://code.visualstudio.com)
  - Extensión recomendada: `ms-python.python`

### Paso 1 – Abrir en VS Code
```bash
cd sap_client
code .
```

### Paso 2 – Crear entorno virtual e instalar dependencias
En la terminal integrada de VS Code (`Ctrl+ñ`):
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Paso 3 – Ejecutar en modo desarrollo
Presiona `F5` o usa el menú Run → "▶ Ejecutar SAP Client"

---

## 🏗️ Generar el ejecutable (.exe)

### Opción A – Script automático (más fácil)
Doble clic en `build.bat`  
El ejecutable aparecerá en `dist\SAP_API_Client.exe`

### Opción B – Desde la terminal
```bash
.venv\Scripts\activate
pyinstaller SAP_API_Client.spec
```

### Opción C – Comando directo
```bash
pyinstaller --onefile --windowed --name SAP_API_Client src/app.py
```

---

## 🔧 Configuración SAP

Al abrir la app, haz clic en **⚙ Config** y completa:

| Campo      | Ejemplo                            |
|------------|------------------------------------|
| SAP Host   | `myxxxxxx-api.s4hana.cloud.sap`    |
| Usuario    | `TU_COMMUNICATION_USER`            |
| Contraseña | `TuPassword`                       |

La configuración se guarda automáticamente en `sap_client_config.json`  
(en la misma carpeta del .exe) para que no tengas que reingresarla.

---

## 📡 Uso básico

### GET – Obtener registros
1. Selecciona método **GET**
2. Pega la URL OData:  (ejemplo)
   `https://myxxxxxx-api.s4hana.cloud.sap/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_AddressIndependentEmailAddress`
3. En **Params**, configura `$select`, `$top`, `$filter`
4. Activa **Auto-paginación** para descargar todos los registros automáticamente
5. Haz clic en **ENVIAR**
6. Exporta con los botones **⬇ Excel** o **⬇ CSV**

### POST con CSV – Enviar datos masivos
1. Selecciona método **POST**
2. Ingresa la URL del endpoint
3. Ve a la pestaña **📦 Body** → selecciona **CSV → JSON**
4. Haz clic en **📂 Cargar CSV** y selecciona tu archivo
5. (Opcional) Configura el JSON wrapper key, ej: `value`
6. Haz clic en **ENVIAR**

---

## 🔗 Endpoints SAP comunes

| Recurso              | Path OData                                                              |
|----------------------|-------------------------------------------------------------------------|
| Business Partners    | `/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner`            |
| Emails BP            | `/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_AddressIndependentEmailAddress` |
| Sales Orders         | `/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder`                  |
| Purchase Orders      | `/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder`     |
| Materiales           | `/sap/opu/odata/sap/API_MATERIAL_DOCUMENT_SRV/A_MaterialDocumentHeader`|

---

## ⚠️ Solución de problemas

| Problema                        | Solución                                              |
|---------------------------------|-------------------------------------------------------|
| Error SSL                       | Desmarca "Verificar certificado SSL" en Auth         |
| Error 403 / CSRF                | Activa "Obtener CSRF Token automático"               |
| .exe no abre (Windows Defender) | Clic derecho → "Ejecutar de todos modos"             |
| Sin datos en tabla              | Verifica que el JSON tenga estructura `d.results`    |
| Error de módulo al compilar     | Agrega el módulo a `--hidden-import` en el .spec     |

---

## 📝 Notas de seguridad
- La contraseña se guarda en texto plano en `sap_client_config.json`.  
  En producción, considera usar variables de entorno o un vault de credenciales.
- El certificado SSL está habilitado por defecto; desactívalo solo en redes seguras.
