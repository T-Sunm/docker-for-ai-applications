"""
Model registry — manages the MODEL LIFECYCLE: create, load (lazy), release resources.

Why a registry?
  - Models are heavy; we should not load everything at startup.
  - We must know which models sit in RAM/VRAM so we can free them on demand.
  - Several routers may share one model, so they must share ONE instance.

An instance is identified by `name::device`, so the same model can be loaded on both
CPU and GPU (or reloaded when the user switches device).
"""

from __future__ import annotations

from typing import Any, Callable


class ModelRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[str], Any]] = {}
        self._instances: dict[str, Any] = {}  # "name::device" -> model instance

    def register(self, name: str, factory: Callable[[str], Any]) -> None:
        """Register a factory that builds the model for a given device."""
        self._factories[name] = factory

    def has(self, name: str) -> bool:
        return name in self._factories

    def keys(self) -> list[str]:
        return list(self._factories.keys())

    @staticmethod
    def _key(name: str, device: str) -> str:
        return f"{name}::{device}"

    def is_loaded(self, name: str, device: str) -> bool:
        instance = self._instances.get(self._key(name, device))
        return bool(getattr(instance, "is_loaded", False)) if instance is not None else False

    def ensure_loaded(self, name: str, device: str) -> Any:
        """Return the model loaded on `device`, loading it on first use."""
        if name not in self._factories:
            raise KeyError(name)
        key = self._key(name, device)
        if key not in self._instances:
            self._instances[key] = self._factories[name](device)  # built but not loaded
        instance = self._instances[key]
        if hasattr(instance, "is_loaded") and not instance.is_loaded:
            instance.load()
        return instance

    def unload(self, name: str) -> int:
        """Unload every device instance of `name`. Returns how many were released."""
        released = 0
        for key in [k for k in self._instances if k.split("::")[0] == name]:
            instance = self._instances.pop(key)
            if hasattr(instance, "unload"):
                instance.unload()
            released += 1
        return released

    def unload_all(self) -> None:
        for key in list(self._instances.keys()):
            instance = self._instances.pop(key)
            if hasattr(instance, "unload"):
                instance.unload()

    def status(self) -> list[dict]:
        out = []
        for name in self._factories:
            loaded_devices = [
                key.split("::")[1]
                for key in self._instances
                if key.split("::")[0] == name and getattr(self._instances[key], "is_loaded", False)
            ]
            out.append({"name": name, "loaded_on": sorted(loaded_devices), "loaded": bool(loaded_devices)})
        return out
