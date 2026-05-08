import pytest
from flux.plugins.base import ContentPlugin, RenderResult
from typing import Any

def test_render_result_defaults():
    res = RenderResult()
    assert res.file_path is None
    assert res.thumbnail_path is None
    assert res.caption == ""
    assert isinstance(res.metadata, dict)
    assert len(res.metadata) == 0
    assert isinstance(res.attachments, list)
    assert len(res.attachments) == 0

def test_render_result_instantiation():
    res = RenderResult(
        file_path="video.mp4",
        caption="Hello",
        metadata={"a": 1},
        attachments=["file1.png"]
    )
    assert res.file_path == "video.mp4"
    assert res.caption == "Hello"
    assert res.metadata == {"a": 1}
    assert res.attachments == ["file1.png"]

def test_content_plugin_abstract():
    with pytest.raises(TypeError):
        # Cannot instantiate abstract class
        ContentPlugin()

class DummyPlugin(ContentPlugin):
    @property
    def name(self) -> str: return "dummy"
    @property
    def display_name(self) -> str: return "Dummy Plugin"
    @property
    def version(self) -> str: return "1.0"
    @property
    def ingredient_types(self) -> list[str]: return ["dummy_type"]
    async def fetch(self, pipeline_id, config, known_items=None): return []
    async def render(self, pipeline_id, ingredient_ids, config): return RenderResult()
    async def identify_content(self, pipeline_id, produced_content_id, config): return None
    async def build_caption(self, pipeline_id, produced_content_id, config, worker_config): return "Caption"
    def get_config_schema(self) -> dict[str, Any]: return {}

def test_dummy_plugin_implementation():
    plugin = DummyPlugin()
    assert plugin.name == "dummy"
    assert plugin.version == "1.0"
