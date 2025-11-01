"""Minimal FastAPI app to manage an in-memory AWS services list.

Endpoints:
- GET /services       -> return list of services
- POST /services      -> add a service (JSON: {"service": "name"})
- DELETE /services/{name} -> remove a service by name

This file is intentionally simple and stores data in-memory. Use uvicorn to run:
    uvicorn api:app --reload --host 127.0.0.1 --port 8000
"""
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from errors import not_found, bad_request, conflict
import logging
from pydantic import BaseModel

app = FastAPI(title="AWS Services API")

# configure a simple logger for this module
logger = logging.getLogger("aws_services_api")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# In-memory list of services as objects with name and category
aws_services = [
    {'name': 'S3', 'category': 'Storage'},
    {'name': 'Lambda', 'category': 'Compute'},
    {'name': 'EC2', 'category': 'Compute'},
    {'name': 'RDS', 'category': 'Database'},
    {'name': 'DynamoDB', 'category': 'Database'},
]


class Service(BaseModel):
    name: str
    category: str


class ServiceCreate(BaseModel):
    name: str
    category: str


@app.get('/services', response_model=List[Service])
def get_services(name: str = None, category: str = None) -> List[Dict[str, str]]:
    """Return services as a JSON array. Optional query params:
    - name: filter by service name (case-insensitive)
    - category: filter by category (case-insensitive)
    """
    results = aws_services
    if name:
        results = [s for s in results if s['name'].lower() == name.lower()]
    if category:
        results = [s for s in results if s['category'].lower() == category.lower()]
    return results


@app.post('/services', status_code=201, response_model=List[Service])
def add_service(payload: ServiceCreate) -> List[Dict[str, str]]:
    name = payload.name
    category = payload.category
    if not name or not isinstance(name, str) or not category or not isinstance(category, str):
        raise bad_request('Missing or invalid "name" or "category" field')
    # Prevent duplicates of (name, category) pair, case-insensitive
    existing_pairs = {(s['name'].lower(), s['category'].lower()) for s in aws_services}
    if (name.lower(), category.lower()) in existing_pairs:
        raise conflict('Service with same name and category already exists (case-insensitive)')
    # Reject names that are only digits
    if name.isdigit():
        raise bad_request('Service name must not be numeric only')
    aws_services.append({'name': name, 'category': category})
    return aws_services


@app.delete('/services/{name}', response_model=List[Service])
def delete_service(name: str) -> List[Dict[str, str]]:
    # Perform case-insensitive match on the 'name' field
    match_idx = None
    for idx, s in enumerate(aws_services):
        if s['name'].lower() == name.lower():
            match_idx = idx
            break
    if match_idx is None:
        raise not_found('Service not found')
    # Log the deletion index and service
    logger.info(f"Deleting service at index={match_idx}: {aws_services[match_idx]}")
    aws_services.pop(match_idx)
    return aws_services


@app.delete('/services/{name}/{category}', response_model=List[Service])
def delete_service_exact(name: str, category: str) -> List[Dict[str, str]]:
    """Delete a specific (name, category) pair (case-insensitive)."""
    match_idx = None
    for idx, s in enumerate(aws_services):
        if s['name'].lower() == name.lower() and s['category'].lower() == category.lower():
            match_idx = idx
            break
    if match_idx is None:
        raise not_found('Service with specified name and category not found')
    logger.info(f"Deleting service at index={match_idx}: {aws_services[match_idx]}")
    aws_services.pop(match_idx)
    return aws_services
