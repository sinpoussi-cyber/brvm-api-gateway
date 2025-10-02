# ==============================================================================
# BRVM API GATEWAY (V0.1 - DÉMARRAGE)
# ==============================================================================

from fastapi import FastAPI
import os

# Initialiser l'application FastAPI
app = FastAPI(
    title="BRVM Analysis API",
    description="API pour servir les données financières et les analyses de la BRVM.",
    version="0.1.0"
)

@app.get("/")
def read_root():
    """
    Endpoint racine pour vérifier que l'API est en ligne.
    """
    return {"status": "ok", "message": "Bienvenue sur l'API d'Analyse BRVM !"}

# La suite de notre code (connexion DB, endpoints, etc.) viendra ici.
