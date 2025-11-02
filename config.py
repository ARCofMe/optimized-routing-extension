from pydantic import BaseModel
from typing import Optional


class RouteConfig(BaseModel):
    """
    Configuration model for customizing the route's origin and destination.

    This model is used to override the default behavior of the routing engine,
    which typically uses the first and last addresses as the origin and
    destination, respectively. When specified, `start_location` and/or
    `end_location` take precedence.

    Attributes:
        start_location (Optional[str]):
            Custom starting point for the route. If not provided,
            the first address in the list is used as the origin.

        end_location (Optional[str]):
            Custom ending point for the route. If not provided,
            the last address in the list is used as the destination.
    """

    start_location: Optional[str] = None
    end_location: Optional[str] = None
