@echo off
setlocal enabledelayedexpansion
title LifeLine launcher

REM ===========================================================================
REM  LifeLine - one-click dev launcher for Windows.
REM
REM  Just double-click run.cmd, or from any terminal:
REM     run.cmd            start backend (:8000) + frontend (:5173)
REM     run.cmd setup      build/install only - don't start the servers
REM     run.cmd fresh      wipe and reinstall all deps, then start
REM
REM  It auto-installs everything the first time: donor dataset, Python venv +
REM  backend deps, frontend npm deps. No admin and no PowerShell policy needed.
REM ===========================================================================

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "DATA=%ROOT%data"
set "VENV_PY=%BACKEND%\.venv\Scripts\python.exe"
set "MODE=%~1"

echo === LifeLine dev launcher ===

REM --- fresh: wipe deps so they get reinstalled ---
if /i "%MODE%"=="fresh" (
  echo [fresh] Removing backend\.venv and frontend\node_modules ...
  if exist "%BACKEND%\.venv" rmdir /s /q "%BACKEND%\.venv"
  if exist "%FRONTEND%\node_modules" rmdir /s /q "%FRONTEND%\node_modules"
)

REM --- locate a real Python only if we still need to build the venv ---
set "PY="
if not exist "%VENV_PY%" call :find_python
if not exist "%VENV_PY%" if not defined PY goto :no_python

REM --- 1. donor dataset (portable SQLite DB, committed to the repo) ---
if not exist "%DATA%\lifeline.db" (
  echo Seeding data\lifeline.db ...
  set "SEED_PY=%PY%"
  if exist "%VENV_PY%" set "SEED_PY=%VENV_PY%"
  pushd "%DATA%"
  "!SEED_PY!" generate_donors.py || ( popd & goto :fail )
  popd
) else (
  echo data\lifeline.db present.
)

REM --- 2. backend venv + requirements ---
if not exist "%VENV_PY%" (
  echo Creating backend\.venv ...
  "%PY%" -m venv "%BACKEND%\.venv" || goto :fail
  "%VENV_PY%" -m pip install --upgrade pip
  echo Installing backend requirements ...
  "%VENV_PY%" -m pip install -r "%BACKEND%\requirements.txt" || goto :fail
) else (
  echo backend\.venv present.
)

REM --- 3. backend .env (so the key is easy to find) ---
if not exist "%BACKEND%\.env" (
  copy /y "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
  echo Created backend\.env from template - add your GROQ_API_KEY to it.
)

REM --- 4. frontend deps ---
if not exist "%FRONTEND%\node_modules" (
  echo Installing frontend deps ^(npm install^) ...
  pushd "%FRONTEND%"
  call npm install || ( popd & goto :fail )
  popd
) else (
  echo frontend\node_modules present.
)

if /i "%MODE%"=="setup" (
  echo.
  echo Setup complete. Run run.cmd to start the servers.
  goto :end
)

REM --- 5. launch both servers, each in its own window ---
echo Starting servers ...
start "LifeLine Backend"  /d "%BACKEND%"  cmd /k .venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
start "LifeLine Frontend" /d "%FRONTEND%" cmd /k npm run dev

echo.
echo   App:      http://localhost:5173
echo   API docs: http://localhost:8000/docs
echo.
echo   Two windows opened (backend + frontend). Close them to stop the servers.
goto :end

REM ===========================================================================
:find_python
REM Try the py launcher / PATH; each candidate must actually report a version
REM (this rejects the Windows Store "python" stub, which exits non-zero).
for %%C in (py python python3) do (
  if not defined PY (
    %%C --version >nul 2>&1 && set "PY=%%C"
  )
)
REM Fallback: a per-user install (e.g. from `winget install Python.Python.3.12`).
if not defined PY (
  for /f "delims=" %%P in ('dir /b /s "%LOCALAPPDATA%\Programs\Python\Python3*\python.exe" 2^>nul') do set "PY=%%P"
)
exit /b

:no_python
echo.
echo ERROR: Python 3.10+ was not found.
echo   Install from https://python.org  (tick "Add python.exe to PATH"),
echo   or run:  winget install Python.Python.3.12
echo Then run this script again.
goto :end

:fail
echo.
echo Setup FAILED - see the error above.

:end
endlocal
echo.
pause
