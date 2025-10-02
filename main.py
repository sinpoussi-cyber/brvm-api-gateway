# ==============================================================================
# BRVM API GATEWAY (V0.2 - CONNEXION BASE DE DONNÉES)
# ==============================================================================

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv

# Charger les variables d'environnement (pour un test local facile)
load_dotenv()

# --- Configuration de la Base de Données ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Créer le "moteur" de connexion à la base de données
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialiser l'application FastAPI
app = FastAPI(
    title="BRVM Analysis API",
    description="API pour servir les données financières et les analyses de la BRVM.",
    version="0.2.0"
)

# --- Dépendance pour la gestion de la session DB ---
def get_db():
    """
    Cette fonction s'exécute à chaque requête. Elle ouvre une session
    de base de données, la fournit à l'endpoint, puis la ferme à la fin.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    """
    Endpoint racine pour vérifier que l'API est en ligne.
    """
    return {"status": "ok", "message": "Bienvenue sur l'API d'Analyse BRVM !"}

@app.get("/health-check")
def health_check(db: SessionLocal = Depends(get_db)):
    """
    Vérifie la connectivité avec la base de données.
    """
    try:
        # Exécute une requête simple pour tester la connexion
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database_connection": "successful"}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=503, detail=f"Database connection error: {e}")

# La suite de notre code (endpoints, etc.) viendra ici.
