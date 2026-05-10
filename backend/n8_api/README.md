# API Orchestrator

Flask-based central hub for the travel planner pipeline.

## Endpoints
- `POST /recommend`: Full recommendation pipeline
- `POST /activities`: Activity generation for a single location
- `GET /health`: System health check

## Pipeline
N2 -> N1 -> N3 -> N4 -> N5 -> N6
