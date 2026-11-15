from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


# Reusable type for non-empty strings
NonEmptyStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1
    )
]


class AppBaseModel(BaseModel):
    """
    Common base class for application models.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True
    )