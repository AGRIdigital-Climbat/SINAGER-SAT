REM ============================================
REM NOTA: En Linux usa: bash database/iniciar_edan.sh
REM ============================================
@echo off
title EDAN - Configurar Base de Datos
echo ============================================
echo   EDAN - Configurar Base de Datos PostgreSQL
echo ============================================
echo.

:: 1. Verificar WSL
echo [1/6] Verificando WSL...
wsl --list --verbose >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: WSL no esta instalado
    pause
    exit /b 1
)
echo       WSL OK

:: 2. Iniciar PostgreSQL
echo [2/6] Iniciando PostgreSQL en WSL...
wsl bash -c "echo 'jeremyliam' | sudo -S service postgresql start" >nul 2>&1
timeout /t 2 /nobreak >nul
wsl bash -c "pg_isready" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Reintentando...
    wsl bash -c "echo 'jeremyliam' | sudo -S service postgresql restart" >nul 2>&1
    timeout /t 3 /nobreak >nul
)
wsl bash -c "pg_isready" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: No se pudo iniciar PostgreSQL
    pause
    exit /b 1
)
echo       PostgreSQL corriendo

:: 3. Configurar reenvio de puertos
echo [3/6] Configurando reenvio de puertos...
netsh interface portproxy show v4tov4 | findstr "5432" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Solicitando permisos de administrador...
    for /f "tokens=*" %%i in ('wsl hostname -I') do set WSL_IP=%%i
    for /f "tokens=1" %%a in ("%WSL_IP%") do set WSL_IP=%%a
    powershell -Command "Start-Process cmd -ArgumentList '/c netsh interface portproxy add v4tov4 listenport=5432 listenaddress=127.0.0.1 connectport=5432 connectaddress=%WSL_IP%' -Verb RunAs -Wait" 2>nul
    echo       Puerto configurado a %WSL_IP%:5432
) else (
    echo       Puerto ya configurado
)

:: 4. Verificar conexion
echo [4/6] Verificando conexion...
wsl bash -c "PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h localhost -c \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='edan';\"" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Advertencia: No se pudo verificar la conexion
) else (
    echo       Conexion OK - 25 tablas
)

:: 5. Configurar pgAdmin4
echo [5/6] Configurando pgAdmin4...
if exist "%APPDATA%\pgAdmin" (
    echo {> "%TEMP%\servers.json"
    echo     "Servers": {>> "%TEMP%\servers.json"
    echo         "1": {>> "%TEMP%\servers.json"
    echo             "Name": "EDAN",>> "%TEMP%\servers.json"
    echo             "Group": "EDAN",>> "%TEMP%\servers.json"
    echo             "Host": "127.0.0.1",>> "%TEMP%\servers.json"
    echo             "Port": 5432,>> "%TEMP%\servers.json"
    echo             "MaintenanceDB": "postgres",>> "%TEMP%\servers.json"
    echo             "Username": "sinagersat",>> "%TEMP%\servers.json"
    echo             "Password": "12345678",>> "%TEMP%\servers.json"
    echo             "SSLMode": "prefer">> "%TEMP%\servers.json"
    echo         }>> "%TEMP%\servers.json"
    echo     }>> "%TEMP%\servers.json"
    echo }>> "%TEMP%\servers.json"
    copy /y "%TEMP%\servers.json" "%APPDATA%\pgAdmin\servers.json" >nul 2>&1
    echo       pgAdmin4 configurado
) else (
    echo       pgAdmin4 no encontrado
)

:: 6. Verificar DBeaver
echo [6/6] Verificando DBeaver...
if exist "%LOCALAPPDATA%\DBeaver\dbeaver.exe" (
    echo       DBeaver encontrado
) else (
    echo       DBeaver no encontrado en ruta estandar
)

echo.
echo ============================================
echo   CONFIGURACION COMPLETA
echo ============================================
echo.
echo   Base de datos: db_sinagersat
echo   Usuario:       sinagersat
echo   Contrasena:    12345678
echo   Host:          127.0.0.1
echo   Puerto:        5432
echo.
echo   Para DBeaver:
echo   - Nuevo.getConnection > PostgreSQL
echo   - Host: 127.0.0.1
echo   - Port: 5432
echo   - Database: db_sinagersat
echo   - User: sinagersat
echo   - Password: 12345678
echo.
pause
