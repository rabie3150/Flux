# Plugin System Documentation

## Overview
Flux is built on a plugin-first architecture. All content generation logic is isolated in plugins, allowing the core engine to remain lightweight and extensible.

## Documentation Index
- [Plugin Interface](file:///D:/Projects/Flux/documents/plugins/plugin-interface.md) — How to build and integrate new content plugins.
- [Quran Plugin](file:///D:/Projects/Flux/documents/plugins/quran-plugin.md) — Technical details of the reference Quran shorts implementation.

## Core Plugin Components
- **Base Interface:** `flux/plugins/base.py`
- **Plugin Loader:** `flux/plugins/loader.py`
- **Built-in Plugins:** `flux/plugins/quran/`
