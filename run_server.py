"""
Script d'exécution rapide du serveur complet (Backend API + Frontend Vue3).
Lance FastAPI sur le port 8000 et sert à la fois les API REST et le frontend Vue3.
"""
import uvicorn
import os
import sys

# Ajouter le dossier backend au path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    print("=" * 70)
    print(" DÉMARRAGE DU SERVEUR AI FITNESS COUNTER")
    print(" Application disponible sur : http://localhost:8000")
    print(" Documentation Swagger : http://localhost:8000/docs")
    print("=" * 70)
    uvicorn.run("main:app", app_dir=backend_dir, host="0.0.0.0", port=8000, reload=True)
