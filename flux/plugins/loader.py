"""Plugin Loader and Registry.

Scans the plugins directory, imports plugin modules dynamically,
and registers them in an in-memory dictionary.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path

from flux.logger import get_logger
from flux.plugins.base import ContentPlugin

logger = get_logger(__name__)

# Global in-memory mapping of plugin_id -> ContentPlugin instance
PLUGIN_REGISTRY: dict[str, ContentPlugin] = {}


def load_plugins() -> None:
    """Scan the flux.plugins package and load all available plugins."""
    import flux.plugins

    plugins_dir = Path(flux.plugins.__file__).parent
    logger.info("Scanning for plugins in %s", plugins_dir)

    for _, module_name, is_pkg in pkgutil.iter_modules([str(plugins_dir)]):
        if not is_pkg or module_name == "base":
            continue

        try:
            plugin_module = importlib.import_module(f"flux.plugins.{module_name}.plugin")
        except ImportError as e:
            logger.warning("Failed to import plugin module %s: %s", module_name, e)
            continue

        # Find classes in the module that subclass ContentPlugin
        found_plugin = False
        for name, obj in inspect.getmembers(plugin_module, inspect.isclass):
            if issubclass(obj, ContentPlugin) and obj is not ContentPlugin:
                try:
                    plugin_instance = obj()
                    plugin_id = plugin_instance.name
                    PLUGIN_REGISTRY[plugin_id] = plugin_instance
                    logger.info("Loaded plugin: %s (v%s)", plugin_instance.display_name, plugin_instance.version)
                    found_plugin = True
                except Exception as e:
                    logger.error("Failed to instantiate plugin %s: %s", name, e)

        if not found_plugin:
            logger.warning("No ContentPlugin implementation found in flux.plugins.%s", module_name)


def get_plugin(plugin_id: str) -> ContentPlugin | None:
    """Retrieve a loaded plugin by its ID."""
    return PLUGIN_REGISTRY.get(plugin_id)
