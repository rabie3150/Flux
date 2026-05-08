import os
from pathlib import Path

import pytest

from flux.core.storage import get_storage_budget, get_system_disk_usage, _get_dir_size


def test_get_dir_size_empty_dir(tmp_path: Path):
    """Test getting size of an empty directory."""
    assert _get_dir_size(tmp_path) == 0


def test_get_dir_size_with_files(tmp_path: Path):
    """Test getting size of a directory with nested files."""
    file1 = tmp_path / "test1.txt"
    file1.write_text("hello")  # 5 bytes
    
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    file2 = sub_dir / "test2.txt"
    file2.write_text("hello world")  # 11 bytes
    
    assert _get_dir_size(tmp_path) == 16


def test_get_storage_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test the budget calculation logic."""
    # Mock settings
    class MockSettings:
        storage_budget_gb = 1
        storage_path = tmp_path / "flux"
        base_path = tmp_path / "flux_base"
        
    monkeypatch.setattr("flux.core.storage.settings", MockSettings())
    
    # Create the mocked storage directories and add files
    MockSettings.storage_path.mkdir(parents=True)
    (MockSettings.storage_path / "file.bin").write_bytes(b"0" * 1024 * 1024 * 100)  # 100 MB
    
    budget = get_storage_budget()
    
    expected_budget = 1024 * 1024 * 1024  # 1 GB
    assert budget.total_budget_bytes == expected_budget
    assert budget.used_bytes == 100 * 1024 * 1024
    assert budget.free_bytes == expected_budget - (100 * 1024 * 1024)
    assert 9.0 < budget.percent_used < 10.0
    assert not budget.is_warning
    assert not budget.is_critical


def test_get_storage_budget_over_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test budget calculation when usage exceeds budget."""
    class MockSettings:
        storage_budget_gb = 1
        storage_path = tmp_path / "flux"
        base_path = tmp_path / "flux_base"
        
    monkeypatch.setattr("flux.core.storage.settings", MockSettings())
    
    MockSettings.storage_path.mkdir(parents=True)
    # Write 1025 MB (over 1 GB limit)
    # We mock _get_dir_size to avoid actually writing 1GB to disk
    monkeypatch.setattr("flux.core.storage._get_dir_size", lambda path: 1025 * 1024 * 1024)
    
    budget = get_storage_budget()
    
    expected_budget = 1024 * 1024 * 1024  # 1 GB
    assert budget.total_budget_bytes == expected_budget
    assert budget.used_bytes == 1025 * 1024 * 1024
    assert budget.free_bytes == 0  # Should bottom out at 0, not go negative
    assert budget.percent_used > 100.0
    assert budget.is_warning
    assert budget.is_critical


def test_get_system_disk_usage(monkeypatch: pytest.MonkeyPatch):
    """Test system disk usage."""
    # Ensure it returns valid keys, even if we mock the values
    monkeypatch.setattr("shutil.disk_usage", lambda path: type("Usage", (), {"total": 100, "used": 50, "free": 50})())
    
    usage = get_system_disk_usage()
    assert usage["total_bytes"] == 100
    assert usage["used_bytes"] == 50
    assert usage["free_bytes"] == 50
    assert usage["percent_used"] == 50.0
