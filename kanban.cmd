@echo off
setlocal

set SCRIPT_DIR=%~dp0
set PLANS_DIR=%SCRIPT_DIR%plans
set CENTRAL_PLANS=D:\plans
set SERVER=%SCRIPT_DIR%.claude\skills\plans-kanban\scripts\server.cjs

if "%1"=="--stop" (
    node "%SERVER%" --stop
    goto :eof
)

:: Stop any existing instance before starting
node "%SERVER%" --stop 2>nul

:: Start with D:\plans hub (primary) + local project plans (fallback, auto-deduplicated)
:: Extra dirs: kanban.cmd --dir "D:\Projects\Other\plans"
node "%SERVER%" --dir "%CENTRAL_PLANS%" --dir "%PLANS_DIR%" %* --host 0.0.0.0 --open --foreground

endlocal
