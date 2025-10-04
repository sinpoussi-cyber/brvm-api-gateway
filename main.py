# ==============================================================================
# BRVM API GATEWAY (V0.4 - AJOUT DE L'ENDPOINT SCREENER)
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

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    print("ERREUR: Une ou plusieurs variables d'environnement de la base de données sont manquantes.")
    
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

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
    version="0.4.0"
)

# --- Dépendance pour la gestion de la session DB ---
def get_db():
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
    return {"status": "ok", "message": "Bienvenue sur l'API d'Analyse BRVM !"}

@app.get("/health-check")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database_connection": "successful"}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=503, detail=f"Database connection error: {e}")

@app.get("/companies/")
def get_companies_list(db: Session = Depends(get_db)):
    try:
        query = text("SELECT symbol, name FROM companies ORDER BY symbol;")
        result = db.execute(query).fetchall()
        companies = [{"symbol": row[0], "name": row[1]} for row in result]
        return companies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@app.get("/analysis/{symbol}")
def get_full_analysis(symbol: str, db: Session = Depends(get_db)):
    symbol = symbol.upper()
    
    query = text("""
        WITH ranked_historical_data AS (
            SELECT *, ROW_NUMBER() OVER(PARTITION BY company_id ORDER BY trade_date DESC) as rn
            FROM historical_data
        )
        SELECT 
            c.symbol, c.name as company_name,
            rhd.trade_date, rhd.price,
            ta.mm_decision, ta.bollinger_decision, ta.macd_decision,
            ta.rsi_decision, ta.stochastic_decision,
            (SELECT STRING_AGG(fa.analysis_summary, E'\\n---\\n' ORDER BY fa.report_date DESC) 
             FROM fundamental_analysis fa 
             WHERE fa.company_id = c.id) as fundamental_summaries
        FROM companies c
        LEFT JOIN ranked_historical_data rhd ON c.id = rhd.company_id
        LEFT JOIN technical_analysis ta ON rhd.id = ta.historical_data_id
        WHERE c.symbol = :symbol AND (rhd.rn <= 50 OR rhd.rn IS NULL)
        ORDER BY rhd.trade_date ASC;
    """)
    
    try:
        result = db.execute(query, {"symbol": symbol}).fetchall()
        
        if not result:
            raise HTTPException(status_code=404, detail="Symbol not found or no recent data")
            
        price_history = [{"date": row.trade_date.strftime('%Y-%m-%d'), "price": row.price} for row in result if row.trade_date and row.price is not None]
        
        latest_data = result[-1]
        
        analysis_data = {
            "symbol": latest_data.symbol,
            "company_name": latest_data.company_name,
            "price_history": price_history,
            "last_trade_date": latest_data.trade_date.strftime('%Y-%m-%d') if latest_data.trade_date else None,
            "last_price": latest_data.price,
            "technical_analysis": {
                "moving_average_signal": latest_data.mm_decision,
                "bollinger_bands_signal": latest_data.bollinger_decision,
                "macd_signal": latest_data.macd_decision,
                "rsi_signal": latest_data.rsi_decision,
                "stochastic_signal": latest_data.stochastic_decision
            },
            "fundamental_analysis": latest_data.fundamental_summaries or "Aucune analyse fondamentale disponible."
        }
        
        return analysis_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching analysis: {e}")

# --- NOUVEL ENDPOINT ---
@app.get("/screener/")
def get_market_screener(db: Session = Depends(get_db)):
    """
    Retourne les derniers signaux techniques pour toutes les sociétés
    pour construire un tableau de bord de marché.
    """
    query = text("""
        WITH latest_data AS (
            SELECT
                company_id,
                MAX(trade_date) as last_date
            FROM historical_data
            GROUP BY company_id
        )
        SELECT
            c.symbol,
            c.name,
            hd.price as last_price,
            ta.mm_decision,
            ta.bollinger_decision,
            ta.macd_decision,
            ta.rsi_decision,
            ta.stochastic_decision
        FROM companies c
        JOIN latest_data ld ON c.id = ld.company_id
        JOIN historical_data hd ON ld.company_id = hd.company_id AND ld.last_date = hd.trade_date
        LEFT JOIN technical_analysis ta ON hd.id = ta.historical_data_id
        ORDER BY c.symbol;
    """)
    
    try:
        result = db.execute(query).fetchall()
        screener_data = [
            {
                "symbol": row[0],
                "name": row[1],
                "last_price": row[2],
                "signal_mm": row[3],
                "signal_bollinger": row[4],
                "signal_macd": row[5],
                "signal_rsi": row[6],
                "signal_stochastic": row[7]
            } for row in result
        ]
        return screener_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
