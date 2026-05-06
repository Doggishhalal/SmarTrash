@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================
rem SmarTrash robust one-click launcher
rem Usage:
rem   START_SMARTRASH.bat          -> run app
rem   START_SMARTRASH.bat --check  -> preflight only
rem ============================================================

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "CHECK_ONLY=0"

if /I "%~1"=="--check" set "CHECK_ONLY=1"

echo.
echo ==================================================
echo   SmarTrash Auto Start
echo ==================================================
echo.

if not exist "%BACKEND_DIR%\app.py" (
    echo [ERROR] app.py not found in backend folder:
    echo         %BACKEND_DIR%
    exit /b 1
)

set "PY_EXE="
if exist "%BACKEND_DIR%\venv\Scripts\python.exe" set "PY_EXE=%BACKEND_DIR%\venv\Scripts\python.exe"
if not defined PY_EXE if exist "%BACKEND_DIR%\.venv\Scripts\python.exe" set "PY_EXE=%BACKEND_DIR%\.venv\Scripts\python.exe"
if not defined PY_EXE if exist "%ROOT_DIR%\.venv\Scripts\python.exe" set "PY_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"

if not defined PY_EXE (
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%P in ('where python') do (
            if not defined PY_EXE set "PY_EXE=%%P"
        )
    )
)

if not defined PY_EXE (
    echo [ERROR] No Python executable found.
    echo         Create backend\venv or install Python and add it to PATH.
    exit /b 1
)

echo [OK] Python: %PY_EXE%

set "SELECTED_MODEL="
if defined YOLOX_CKPT if exist "%YOLOX_CKPT%" set "SELECTED_MODEL=%YOLOX_CKPT%"
if not defined SELECTED_MODEL if exist "C:\models\yolox_m.pth" set "SELECTED_MODEL=C:\models\yolox_m.pth"
if not defined SELECTED_MODEL if exist "C:\models\yolox_s.pth" set "SELECTED_MODEL=C:\models\yolox_s.pth"
if not defined SELECTED_MODEL set "SELECTED_MODEL=C:\models\yolox_s.pth"

set "YOLOX_CKPT=%SELECTED_MODEL%"
set "YOLOX_DEVICE=cpu"
set "KMP_DUPLICATE_LIB_OK=TRUE"
set "PYTHONPATH=%BACKEND_DIR%"

if exist "%YOLOX_CKPT%" (
    echo [OK] Model: %YOLOX_CKPT%
) else (
    echo [WARN] Model file not found: %YOLOX_CKPT%
    echo       App can start, but detection will fail until model exists.
)

echo [INFO] Running preflight checks...
pushd "%BACKEND_DIR%" >nul
"%PY_EXE%" -c "import tkinter, cv2, numpy, torch; import app; print('PRECHECK_OK')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Preflight failed.
    echo         Try: "%PY_EXE%" -m pip install -r requirements.txt
    popd >nul
    exit /b 1
)
popd >nul
echo [OK] Preflight passed.

if "%CHECK_ONLY%"=="1" (
    echo [OK] Check completed.
    exit /b 0
)

echo [INFO] Starting app...
pushd "%BACKEND_DIR%" >nul
"%PY_EXE%" app.py
set "APP_EXIT=%ERRORLEVEL%"
popd >nul

if not "%APP_EXIT%"=="0" (
    echo [ERROR] App exited with code %APP_EXIT%.
    exit /b %APP_EXIT%
)

echo [OK] App closed normally.
exit /b 0
