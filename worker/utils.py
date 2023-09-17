from logging import getLogger
from signal import SIGTERM, signal
from typing import Any, Protocol, TypeVar, cast
from sys import exit

from pydantic import ConfigDict

LOGGER = getLogger(__name__)

T = TypeVar("T", bound=type[Any])


class PydanticConfig(Protocol):
    __pydantic_config__: ConfigDict


def no_extra(cls: T) -> T:
    cast(PydanticConfig, cls).__pydantic_config__ = ConfigDict(extra="forbid")
    return cls


def add_sigterm():
    LOGGER.debug("Registering SIGTERM signal")
    _ = signal(SIGTERM, lambda _, __: exit())
