@echo off
title AI Fitness Counter - Vue3 & Python
echo ==============================================================
echo     LANCEMENT DE L'APPLICATION AI FITNESS COUNTER
echo     Backend : Python / FastAPI
echo     Frontend : Vue 3 JS / Vision artificielle temps reel
echo ==============================================================

cd /d "%~dp0"

echo Verification et initialisation de la base de donnees MySQL (fitness_counter_db)...
python -c "import sys; sys.path.append('backend'); from database.db import init_db; init_db()"

echo Demarrage du serveur sur http://localhost:8000 ...
start http://localhost:8000
python run_server.py

pause
