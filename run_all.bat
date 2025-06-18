@echo off
REM ----------------------------------------------------
REM run_all.bat - Regenera dados e carrega no banco
REM ----------------------------------------------------

REM Vai para a pasta ETL e gera o master.csv
cd /d "%~dp0etl"
python clean_data.py

REM Volta para raiz e carrega no banco
cd /d "%~dp0"
python -m etl.load_to_db

echo ETL concluído. Você pode agora iniciar o servidor manualmente.
pause
