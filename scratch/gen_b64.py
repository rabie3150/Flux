import base64
s = '{"name": "Quran Daily", "plugin_id": "quran_shorts", "config": {"source_channels": ["https://www.youtube.com/@Am9li9/shorts"], "max_clips_per_fetch": 5}}'
print(base64.b64encode(s.encode()).decode())
