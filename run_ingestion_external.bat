@echo off
echo ===============================================
echo INICIANDO INGESTAO ENEM - EXECUCAO EXTERNA
echo ===============================================
echo.

cd /d "C:\Users\andhs\source\repos\enem-questions-rag"

echo Ativando ambiente virtual...
call .venv\Scripts\activate.bat

echo.
echo Executando ingestao completa...
python scripts\full_ingestion_report.py

echo.
echo ===============================================
echo INGESTAO CONCLUIDA
echo ===============================================
pause
