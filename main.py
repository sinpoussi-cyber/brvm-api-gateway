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
# (à ajouter à la fin de main.py)

@app.get("/analysis/{symbol}")
def get_full_analysis(symbol: str, db: Session = Depends(get_db)):
    """
    Retourne la dernière analyse complète (cours, technique, fondamentale)
    pour un symbole donné.
    """
    # Normaliser le symbole en majuscules
    symbol = symbol.upper()
    
    query = text("""
        SELECT 
            c.symbol, c.name as company_name,
            hd.trade_date, hd.price,
            ta.*, -- Sélectionne toutes les colonnes de l'analyse technique
            (SELECT STRING_AGG(fa.analysis_summary, E'\\n---\\n' ORDER BY fa.report_date DESC) 
             FROM fundamental_analysis fa 
             WHERE fa.company_id = c.id) as fundamental_summaries
        FROM companies c
        LEFT JOIN historical_data hd ON c.id = hd.company_id
        LEFT JOIN technical_analysis ta ON hd.id = ta.historical_data_id
        WHERE c.symbol = :symbol
        ORDER BY hd.trade_date DESC
        LIMIT 1;
    """)
    
    try:
        result = db.execute(query, {"symbol": symbol}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Symbol not found")
        
        # Convertir le résultat en un dictionnaire lisible
        analysis_data = {
            "symbol": result.symbol,
            "company_name": result.company_name,
            "last_trade_date": result.trade_date,
            "last_price": result.price,
            "technical_analysis": {
                "moving_average_signal": result.mm_decision,
                "bollinger_bands_signal": result.bollinger_decision,
                "macd_signal": result.macd_decision,
                "rsi_signal": result.rsi_decision,
                "stochastic_signal": result.stochastic_decision
            },
            "fundamental_analysis": result.fundamental_summaries or "Aucune analyse fondamentale disponible."
        }
        
        return analysis_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
