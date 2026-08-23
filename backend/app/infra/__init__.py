"""Outbound connections: the database engine and third-party API clients.

Nothing in here knows about FastAPI. Services depend on this layer; it never
depends on services or routes.
"""
