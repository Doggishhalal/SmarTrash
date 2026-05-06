@echo off
setlocal
call "%~dp0..\START_SMARTRASH.bat" %*
exit /b %ERRORLEVEL%
