@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if exist "runtime\python-path.txt" (
  set /p WORKBENCH_PYTHON=<"runtime\python-path.txt"
  call :configured
  if not errorlevel 1 exit /b
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
  if not errorlevel 1 (
    py -3 workbench.py serve
    exit /b
  )
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
  if not errorlevel 1 (
    python workbench.py serve
    exit /b
  )
)
for %%P in ("%USERPROFILE%\anaconda3\python.exe" "%USERPROFILE%\miniconda3\python.exe" "%ProgramData%\Anaconda3\python.exe") do (
  if exist %%P (
    %%P -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
    if not errorlevel 1 (
      %%P workbench.py serve
      exit /b
    )
  )
)
echo Python 3.10+ not found. Use an Anaconda Prompt: python workbench.py serve
echo Or save the absolute python.exe path in runtime\python-path.txt, then retry.
pause
exit /b 1
:configured
if not defined WORKBENCH_PYTHON exit /b 1
if not exist "%WORKBENCH_PYTHON%" exit /b 1
"%WORKBENCH_PYTHON%" -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
"%WORKBENCH_PYTHON%" workbench.py serve
exit /b 0
