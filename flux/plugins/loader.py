"""Plugin Loader and Registry.

Scans the plugins directory, imports plugin modules dynamically,
and registers them in an in-memory dictionary.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path

import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flux.logger import get_logger
from flux.models import Plugin
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
        except Exception as e:
            logger.warning("Failed to import plugin module %s: %s", module_name, e)
            continue

        # Find classes in the module that subclass ContentPlugin
        found_plugin = False
        for name, obj in inspect.getmembers(plugin_module, inspect.isclass):
            if issubclass(obj, ContentPlugin) and obj is not ContentPlugin:
                try:
                    plugin_instance = obj()
                    plugin_id = plugin_instance.name
                    if plugin_id in PLUGIN_REGISTRY:
                        logger.error(
                            "Duplicate plugin ID '%s' from %s. Skipping.",
                            plugin_id, module_name,
                        )
                        continue
                    PLUGIN_REGISTRY[plugin_id] = plugin_instance
                    logger.info("Loaded plugin: %s (v%s)", plugin_instance.display_name, plugin_instance.version)
                    found_plugin = True
                except Exception as e:
                    logger.error("Failed to instantiate plugin %s: %s", name, e)

        if not found_plugin:
            logger.warning("No ContentPlugin implementation found in flux.plugins.%s", module_name)


async def sync_plugins_to_db(db: AsyncSession) -> None:
    """Synchronize the in-memory PLUGIN_REGISTRY with the database plugins table."""
    for plugin_id, instance in PLUGIN_REGISTRY.items():
        result = await db.execute(select(Plugin).where(Plugin.name == plugin_id))
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.display_name = instance.display_name
            existing.version = instance.version
            existing.config_schema = json.dumps(instance.get_config_schema())
            # module_path is tricky to get dynamically here but we can skip it or use __module__
            existing.module_path = instance.__class__.__module__
        else:
            # Create new record
            # We use the plugin name as the ID if it's short enough, or just let default _new_id handle it.
            # However, the user is expecting 'quran_shorts' to be the ID in their curl.
            # But in the DB, 'id' is String(32). 'quran_shorts' fits.
            new_plugin = Plugin(
                id=plugin_id,  # Use name as ID for easier manual CURLing/UI usage
                name=plugin_id,
                display_name=instance.display_name,
                version=instance.version,
                api_version="0.1.0",
                module_path=instance.__class__.__module__,
                config_schema=json.dumps(instance.get_config_schema())
            )
            db.add(new_plugin)
    
    await db.commit()
    logger.info("Synchronized %d plugins to database", len(PLUGIN_REGISTRY))


def get_plugin(plugin_id: str) -> ContentPlugin | None:
    """Retrieve a loaded plugin by its ID."""
    return PLUGIN_REGISTRY.get(plugin_id)
