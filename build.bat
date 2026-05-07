@echo off
REM ============================================================
REM  SAP API Client - Script de compilación a .exe
REM  Ejecutar desde la carpeta raíz del proyecto
REM ============================================================

echo.
echo  =====================================================
echo   SAP API Client - Generando ejecutable (.exe)
echo  =====================================================
echo.

REM 1. Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.9+ desde python.org
    pause
    exit /b 1
)

REM 2. Crear entorno virtual (recomendado)
if not exist ".venv" (
    echo [*] Creando entorno virtual...
    python -m venv .venv
)

REM 3. Activar entorno virtual
call .venv\Scripts\activate.bat

REM 4. Instalar dependencias
echo [*] Instalando dependencias...
pip install -r requirements.txt --quiet

REM 5. Compilar con PyInstaller
echo [*] Compilando ejecutable...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "SAP_API_Client" ^
    --icon NONE ^
    --add-data "src;src" ^
    --hidden-import pandas ^
    --hidden-import openpyxl ^
    --hidden-import requests ^
    --hidden-import urllib3 ^
    src\app.py

REM 6. Verificar resultado
if exist "dist\SAP_API_Client.exe" (
    echo.
    echo  =====================================================
    echo   [OK] Ejecutable generado exitosamente:
    echo        dist\SAP_API_Client.exe
    echo  =====================================================
) else (
    echo.
    echo  [ERROR] No se pudo generar el ejecutable.
    echo  Revisa el log de PyInstaller arriba.
)

pause
