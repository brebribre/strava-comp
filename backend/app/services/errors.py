"""Domain errors. Routes translate these into HTTP responses."""


class AthleteNotFound(LookupError):
    """No athlete row for the given ID."""


class ReauthorizationRequired(RuntimeError):
    """The stored refresh token no longer works — the athlete must reconnect Strava."""
