# ==============================================================================
# BRVM API GATEWAY (V0.2 - CONNEXION BASE DE DONNÉES & PREMIERS ENDPOINTS)
# ==============================================================================

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv

# Charger les variables d'environnement (utile pour un test local)
load_dotenv()

# --- Configuration de la Base de Données ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Vérifier que les variables d'environnement sont bien chargées
if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    print("ERREUR: Une ou plusieurs variables d'environnement de la base de données sont manquantes.")
    # Dans un contexte de production, vous pourriez vouloir arrêter le script ici
    # import sys
    # sys.exit(1)

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Créer le "moteur" de connexion à la base de données
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("✅ Connexion à la base de données configurée avec succès.")
except Exception as e:
    print(f"❌ Erreur lors de la configuration de la connexion à la base de données: {e}")
    engine = None
    SessionLocal = None

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
    if SessionLocal is None:
        raise HTTPException(status_code=500, detail="La connexion à la base de données n'a pas pu être initialisée.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints de l'API ---

@app.get("/")
def read_root():
    """
    Endpoint racine pour vérifier que l'API est en ligne.
    """
    return {"status": "ok", "message": "Bienvenue sur l'API d'Analyse BRVM !"}

@app.get("/health-check")
def health_check(db: Session = Depends(get_db)):
    """
    Vérifie la connectivité avec la base de données.
    """
    try:
        # Exécute une requête simple pour tester la connexion
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database_connection": "successful"}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=503, detail=f"Database connection error: {e}")

@app.get("/companies/")
def get_companies_list(db: Session = Depends(get_db)):
    """
    Retourne la liste de toutes les sociétés cotées avec leur symbole et leur nom.
    """
    try:
        query = text("SELECT symbol, name FROM companies ORDER BY symbol;")
        result = db.execute(query).fetchall()
        
        # Convertir le résultat en une liste de dictionnaires
        companies = [{"symbol": row[0], "name": row[1]} for row in result]
        
        return companies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

# Vous pouvez ajouter d'autres endpoints ici au fur et à mesure.
