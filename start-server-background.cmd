@echo off
cd /d "%~dp0"
node server\server.mjs > server-run.log 2> server-run.err.log
