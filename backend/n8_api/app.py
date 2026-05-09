"""
n8_api/app.py
=============
N8 – API Orchestrator (Flask)
"""

from __future__ import annotations
import os
from flask import Flask, request, jsonify, abort
from flask_cors import CORS

# Import config first to handle path setup
from .n8_config import logger, INTERNAL_KEY, ALLOWED_ORIGINS, PROTECTED_ROUTES, HOST, PORT, DEBUG
from .utils import err, get_json
from .logic import run_recommendation_pipeline, run_activities_pipeline

app = Flask(__name__)
CORS(app, origins=ALLOWED_ORIGINS)

@app.before_request
def _check_internal_key():
    if request.path in PROTECTED_ROUTES:
        if not INTERNAL_KEY or request.headers.get("X-Internal-Key") != INTERNAL_KEY:
            abort(401)

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "pipeline": ["n1", "n2", "n3", "n4", "n5", "n6"]
    })

@app.post("/recommend")
def recommend():
    body, error_res = get_json()
    if error_res:
        return error_res
    
    try:
        result = run_recommendation_pipeline(body)
        return jsonify(result)
    except Exception as e:
        logger.exception("Error in recommendation pipeline")
        return err(str(e), 500)

@app.post("/activities")
def activities():
    body, error_res = get_json()
    if error_res:
        return error_res
    
    try:
        result = run_activities_pipeline(body)
        return jsonify(result)
    except Exception as e:
        logger.exception("Error in activities pipeline")
        return err(str(e), 500)

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)