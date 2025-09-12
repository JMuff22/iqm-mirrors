from typing import Any, Self

import pydantic
from pydantic import ConfigDict


class BaseModel(pydantic.BaseModel):
    """Pydantic base model to change the behaviour of pydantic globally.
    Note that setting model_config in child classes will merge the configs rather than override this one.
    https://docs.pydantic.dev/latest/concepts/config/#change-behaviour-globally
    """

    model_config = ConfigDict(
        # extra="forbid",  # Forbid any extra attributes
        # TODO (Marko): Use "ignore" at least temporarily
        #  Data sent by old server code might include extra attributes like "parent_name",
        #  which fails with a new client using extra="ignore".
        #  Before merging to master, consider if we want to be strict with extra="forbid",
        #  or would it be better to use extra="ignore" (shouldn't be needed if we update the server code anyway).
        extra="ignore",  # Ignore any extra attributes
        validate_assignment=True,  # Validate the data when the model is changed
        validate_default=True,  # Validate default values during validation
        ser_json_inf_nan="constants",  # Will serialize infinity and NaN values as Infinity and NaN
        frozen=True,  # This makes instances of the model potentially hashable if all the attributes are hashable
    )

    def model_copy(self, *, update: dict[str, Any] | None = None, deep: bool = True) -> Self:
        """Returns a copy of the model.

        Overrides the Pydantic default 'model_copy' to set 'deep=True' by default.
        """
        return super().model_copy(update=update, deep=deep)

    def copy(self, **kwargs) -> Self:
        """Returns a copy of the model.

        DEPRECATED: Use model_copy(update: dict[str, Any], deep: bool) instead.
        """
        # Call deprecated copy() here deliberately to trigger deprecation warning from Pydantic.
        return super().copy(update=kwargs, deep=True)
