"""
Point d'entrée principal du Backend Python (FastAPI).
Expose les services REST conformes aux diagrammes UML :
- Catalogue d'exercices & règles de comptage
- Gestion des séances, répétitions et corrections de posture
- Suivi des objectifs et notifications
- Espace administration et statistiques
- Montage des fichiers statiques et vidéos de test
"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Assurer l'accès aux modules internes
sys.path.append(os.path.dirname(__file__))

from database.db import init_db
from api.auth import router as auth_router
from api.exercices import router as exercices_router
from api.seances import router as seances_router
from api.objectifs import router as objectifs_router
from api.notifications import router as notifications_router
from api.admin import router as admin_router
from api.vision import router as vision_router
from api.videos import router as videos_router, UPLOAD_DIR
from api.planning import router as planning_router

app = FastAPI(
    title="Real-Time AI Fitness Counter API",
    description="Backend Python conforme au dossier de conception UML (Use Case, Classes, Séquence, Activité)",
    version="1.0.0"
)

# Configuration CORS pour permettre les requêtes depuis Vue3
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation de la base SQLite et des tables au démarrage
@app.on_event("startup")
def on_startup():
    init_db()
    print("Base de données initialisée avec succès.")

# Enregistrement des routes API
app.include_router(auth_router)
app.include_router(exercices_router)
app.include_router(seances_router)
app.include_router(objectifs_router)
app.include_router(notifications_router)
app.include_router(admin_router)
app.include_router(vision_router)
app.include_router(videos_router)
app.include_router(planning_router)

# Health check
@app.get("/api/health")
def health_check():
    from database.db import get_connection
    conn = get_connection()
    is_mysql = conn.is_mysql
    conn.close()
    return {
        "status": "healthy",
        "service": "Fitness Counter Backend",
        "architecture": "UML Level 4 EADL Conforming",
        "database": "MySQL (fitness_counter_db)" if is_mysql else "SQLite Fallback",
        "theme": "Bleu nuit + Blanc + Violet électrique + Turquoise"
    }

# Montage du répertoire des échantillons vidéos
samples_path = os.path.join(os.path.dirname(__file__), "samples")
if os.path.exists(samples_path):
    app.mount("/samples", StaticFiles(directory=samples_path), name="samples")

# Vidéos ajoutées par l'administrateur
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads/videos", StaticFiles(directory=UPLOAD_DIR), name="uploads_videos")

# Montage de l'application frontend si elle est compilée / statique (en dernier pour ne pas intercepter /api)
frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
frontend_static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "public")

if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend_dist")
elif os.path.exists(frontend_static_path):
    app.mount("/", StaticFiles(directory=frontend_static_path, html=True), name="frontend_static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)