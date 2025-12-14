@echo off
rem Windows equivalent of scripts/setup_venv.sh

rem Determine Python executable (use %PYTHON% if provided)
if defined PYTHON (
  set "PYTHON_CMD=%PYTHON%"
) else (
  set "PYTHON_CMD=python"
)

rem Resolve script directory
set "SCRIPT_DIR=%~dp0"

rem Default VENV_DIR to two levels up from the script directory
if defined VENV_DIR (
  set "VENV_DIR=%VENV_DIR%"
) else (
  pushd "%SCRIPT_DIR%..\.." >nul 2>&1
  call set "VENV_DIR=%%CD%%\venv_python_CodeneAria"
  popd >nul 2>&1
)

echo Creating virtual environment at "%VENV_DIR%" using "%PYTHON_CMD%"
"%PYTHON_CMD%" -m venv "%VENV_DIR%"
if errorlevel 1 (
  echo Failed to create virtual environment. Ensure Python is installed and on PATH.
  exit /b 1
)

echo Upgrading pip, setuptools, wheel in the virtual environment
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  echo Warning: pip upgrade failed or returned errors.
)

echo Installing runtime dependencies
"%VENV_DIR%\Scripts\python.exe" -m pip install --no-input requests Flask simpleaudio pytest pyyaml
if errorlevel 1 (
  echo Warning: some packages may have failed to install.
)

echo
echo Activating virtual environment
call "%VENV_DIR%\Scripts\activate.bat" 2>nul || echo Note: Activation in setup script skipped due to environment issue.

echo
echo Setup complete.
echo To activate later in CMD run:
echo    %VENV_DIR%\\Scripts\\activate.bat
echo To activate in PowerShell run:
echo    %VENV_DIR%\\Scripts\\Activate.ps1
echo If PowerShell execution policy prevents activation run PowerShell as admin and use:
echo    powershell -ExecutionPolicy Bypass -File "%VENV_DIR%\\Scripts\\Activate.ps1"
echo
exit /b 0
