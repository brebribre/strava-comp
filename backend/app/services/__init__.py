"""Business logic.

Services take a Session (or a client) and plain arguments, and return plain data.
They raise domain errors rather than HTTPException — routes translate those into
HTTP responses.
"""
