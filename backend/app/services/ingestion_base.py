import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

import httpx

logger = logging.getLogger("prithvinet.ingestion")
T = TypeVar("T")


class IngestionError(RuntimeError):
    pass


def with_retries(source: str, attempts: int = 3, backoff_seconds: float = 1.0) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(function: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(function)
        async def wrapped(*args: Any, **kwargs: Any) -> T:
            for attempt in range(1, attempts + 1):
                try:
                    return await function(*args, **kwargs)
                except Exception as exc:
                    if attempt == attempts:
                        logger.exception("source=%s action=%s status=failed attempts=%s error=%s", source, function.__name__, attempts, exc)
                        raise IngestionError(f"{source} ingestion failed after {attempts} attempts") from exc
                    delay = backoff_seconds * (2 ** (attempt - 1))
                    logger.warning("source=%s action=%s status=retry attempt=%s delay_seconds=%s error=%s", source, function.__name__, attempt, delay, exc)
                    await asyncio.sleep(delay)
            raise IngestionError(f"{source} ingestion failed")

        return wrapped

    return decorator


@with_retries("http", attempts=1)
async def fetch_json(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: float = 30) -> Any:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


@with_retries("http", attempts=1)
async def fetch_text(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: float = 30) -> str:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.text
