@echo off
chcp 65001 >nul
title Painel Tributario - Empresas do RS
cd /d "%~dp0"
echo ============================================================
echo   PAINEL TRIBUTARIO - EMPRESAS DO RS
echo   Iniciando servidor local... (NAO feche esta janela)
echo ============================================================
start "" http://localhost:8777/painel_rs.html
python servidor.py 8777
