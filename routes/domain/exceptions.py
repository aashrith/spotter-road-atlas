"""Domain and integration errors surfaced by the planning use case."""


class DomainError(Exception):
    """Base class for expected, user-facing failures."""


class GeocodingError(DomainError):
    """A location query could not be resolved to US coordinates."""


class RoutingError(DomainError):
    """The external routing provider failed or returned no route."""


class RouteNotServiceableError(DomainError):
    """No combination of known fuel stations can cover the route."""

    def __init__(
        self,
        message: str,
        *,
        start=None,
        finish=None,
        route=None,
    ) -> None:
        super().__init__(message)
        self.start = start
        self.finish = finish
        self.route = route
