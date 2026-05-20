"""Compatibility helpers for optional third-party libraries.

This project is designed to run with the requested stack, but the local
execution environment used by Codex may not have every dependency installed.
The helpers in this module provide lightweight fallbacks so the codebase and
tests remain importable even when the external packages are unavailable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, get_type_hints


class ValidationError(ValueError):
    """Fallback validation error."""


class BaseModel:
    """Tiny pydantic-like model with dump/validate helpers."""

    def __init__(self, **data: Any) -> None:
        annotations = get_type_hints(self.__class__)
        for name, annotation in annotations.items():
            if name.startswith("_"):
                continue
            value = data.get(name, getattr(self.__class__, name, None))
            value = self._coerce_value(annotation, value)
            setattr(self, name, value)
        for name, value in data.items():
            if name not in annotations:
                setattr(self, name, value)

    @classmethod
    def model_validate(cls, value: Any) -> "BaseModel":
        """Create a model from a dict or another model instance."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            raise ValidationError(f"Expected dict for {cls.__name__}")
        return cls(**value)

    @classmethod
    def model_validate_json(cls, raw: str) -> "BaseModel":
        """Create a model from JSON text."""
        return cls.model_validate(json.loads(raw))

    def model_dump(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        result: dict[str, Any] = {}
        for name in get_type_hints(self.__class__):
            result[name] = self._dump_value(getattr(self, name, None))
        for name, value in self.__dict__.items():
            if name not in result:
                result[name] = self._dump_value(value)
        return result

    def model_dump_json(self, *, indent: int | None = None) -> str:
        """Serialize the model to JSON."""
        return json.dumps(self.model_dump(), default=str, indent=indent)

    def model_copy(self, *, update: dict[str, Any] | None = None) -> "BaseModel":
        """Create a shallow copy with optional overrides."""
        payload = self.model_dump()
        if update:
            payload.update(update)
        return self.__class__(**payload)

    @staticmethod
    def _dump_value(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, list):
            return [BaseModel._dump_value(item) for item in value]
        if isinstance(value, tuple):
            return [BaseModel._dump_value(item) for item in value]
        if isinstance(value, dict):
            return {k: BaseModel._dump_value(v) for k, v in value.items()}
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    @classmethod
    def _coerce_value(cls, annotation: Any, value: Any) -> Any:
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", ())
        if value is None:
            return None
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if isinstance(value, dict):
                return annotation.model_validate(value)
            return value
        if origin is list:
            item_type = args[0] if args else Any
            if isinstance(value, list):
                return [cls._coerce_value(item_type, item) for item in value]
            return value
        if annotation is int and isinstance(value, str) and value.isdigit():
            return int(value)
        if annotation is float and isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return value
        if annotation is bool and isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        if annotation is date and isinstance(value, str):
            return date.fromisoformat(value)
        return value

    def __repr__(self) -> str:
        payload = ", ".join(f"{k}={v!r}" for k, v in self.model_dump().items())
        return f"{self.__class__.__name__}({payload})"


def Field(default: Any = None, *, description: str | None = None) -> Any:
    """Fallback Field helper that preserves default values."""
    return default


class BaseSettings(BaseModel):
    """Simple environment-backed settings object."""

    def __init__(self, **data: Any) -> None:
        annotations = get_type_hints(self.__class__)
        payload = dict(data)
        for name, annotation in annotations.items():
            if name in payload:
                continue
            env_value = os.getenv(name.upper())
            if env_value is None:
                continue
            payload[name] = self._coerce_value(annotation, env_value)
        super().__init__(**payload)


class HTTPException(Exception):
    """Fallback HTTP exception."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def Body(default: Any = None, **_: Any) -> Any:
    """FastAPI Body fallback."""
    return default


def Query(default: Any = None, **_: Any) -> Any:
    """FastAPI Query fallback."""
    return default


def Depends(value: Any = None) -> Any:
    """FastAPI Depends fallback."""
    return value


class _Route:
    def __init__(self, method: str, path: str, func: Callable[..., Any]) -> None:
        self.method = method
        self.path = path
        self.func = func


class FastAPI:
    """Very small FastAPI-like container."""

    def __init__(self) -> None:
        self.routes: list[_Route] = []

    def _decorator(self, method: str, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(_Route(method, path, func))
            return func

        return wrapper

    def get(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._decorator("GET", path)

    def post(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._decorator("POST", path)

    def add_middleware(self, *_: Any, **__: Any) -> None:
        """Middleware is ignored in the fallback implementation."""


class APIRouter(FastAPI):
    """Alias for compatibility."""


class StreamingResponse:
    """Fallback streaming response container."""

    def __init__(self, content: Any, media_type: str = "text/plain") -> None:
        self.content = content
        self.media_type = media_type


status = SimpleNamespace(
    HTTP_200_OK=200,
    HTTP_400_BAD_REQUEST=400,
    HTTP_404_NOT_FOUND=404,
    HTTP_500_INTERNAL_SERVER_ERROR=500,
)


class Tool:
    """Minimal LangChain Tool stand-in."""

    def __init__(self, name: str, description: str, func: Callable[[str], Any]) -> None:
        self.name = name
        self.description = description
        self.func = func

    def run(self, input_value: str) -> Any:
        return self.func(input_value)


class ChatOpenAI:
    """Fallback OpenAI chat client placeholder."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def invoke(self, messages: Any) -> SimpleNamespace:
        return SimpleNamespace(content="{}")


def create_react_agent(llm: Any, tools: list[Tool], prompt: Any) -> dict[str, Any]:
    """Return a small agent configuration object."""
    return {"llm": llm, "tools": tools, "prompt": prompt}


class AgentExecutor:
    """Simple sequential executor that preserves tool order."""

    def __init__(self, agent: Any, tools: list[Tool], verbose: bool = False) -> None:
        self.agent = agent
        self.tools = tools
        self.verbose = verbose

    @classmethod
    def from_agent_and_tools(cls, agent: Any, tools: list[Tool], verbose: bool = False) -> "AgentExecutor":
        return cls(agent, tools, verbose=verbose)

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        username = inputs.get("github_username") or inputs.get("input") or ""
        results: dict[str, Any] = {}
        for tool in self.tools:
            results[tool.name] = tool.run(username)
        return {"output": results}


class _NullContext:
    def __enter__(self) -> "_NullContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _StatusContext(_NullContext):
    def update(self, *args: Any, **kwargs: Any) -> None:
        pass


class _Column(_NullContext):
    pass


class _StreamlitFallback:
    """No-op Streamlit fallback used only for local tests."""

    def set_page_config(self, **_: Any) -> None:
        pass

    def columns(self, count: int | Iterable[Any]) -> list[_Column]:
        if isinstance(count, int):
            total = count
        else:
            total = len(list(count))
        return [_Column() for _ in range(total)]

    def text_input(self, *_, **__) -> str:
        return ""

    def text_area(self, *_, **__) -> str:
        return ""

    def button(self, *_, **__) -> bool:
        return False

    def expander(self, *_: Any, **__: Any) -> _NullContext:
        return _NullContext()

    def status(self, *_: Any, **__: Any) -> _StatusContext:
        return _StatusContext()

    def metric(self, *_: Any, **__: Any) -> None:
        pass

    def dataframe(self, *_: Any, **__: Any) -> None:
        pass

    def line_chart(self, *_: Any, **__: Any) -> None:
        pass

    def write(self, *_: Any, **__: Any) -> None:
        pass

    def markdown(self, *_: Any, **__: Any) -> None:
        pass

    def error(self, *_: Any, **__: Any) -> None:
        pass

    def success(self, *_: Any, **__: Any) -> None:
        pass

    def warning(self, *_: Any, **__: Any) -> None:
        pass

    def subheader(self, *_: Any, **__: Any) -> None:
        pass

    def header(self, *_: Any, **__: Any) -> None:
        pass

    def caption(self, *_: Any, **__: Any) -> None:
        pass

    def spinner(self, *_: Any, **__: Any) -> _NullContext:
        return _NullContext()


def get_streamlit() -> Any:
    """Return real Streamlit when installed, otherwise a no-op fallback."""
    try:
        import streamlit as st  # type: ignore

        return st
    except Exception:
        return _StreamlitFallback()


def read_text(path: str | Path) -> str:
    """Read UTF-8 text from a file path."""
    return Path(path).read_text(encoding="utf-8")
