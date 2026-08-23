"""Pydantic models for request bodies and API responses.

Deliberately separate from app.models: what the API accepts and returns is not
the same shape as what is stored (tokens, raw payloads etc. never go out).
"""
