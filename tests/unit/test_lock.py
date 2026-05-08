import asyncio
import pytest
from flux.core.lock import RenderLock, render_lock_ctx

@pytest.mark.asyncio
async def test_render_lock_acquire_release():
    lock = RenderLock()
    
    # First acquire should succeed
    acquired = await lock.acquire(timeout=0)
    assert acquired is True
    
    # Second acquire should fail without timeout
    lock2 = RenderLock()
    acquired2 = await lock2.acquire(timeout=0)
    assert acquired2 is False
    
    # Release first lock
    lock.release()
    
    # Now second acquire should succeed
    acquired3 = await lock2.acquire(timeout=0)
    assert acquired3 is True
    lock2.release()

@pytest.mark.asyncio
async def test_render_lock_context_manager(monkeypatch):
    # Mock thermal check to always return safe for testing lock logic
    def mock_thermal_safe():
        return True, 45.0
    
    import flux.core.hardening
    monkeypatch.setattr(flux.core.hardening, "check_thermal_safe", mock_thermal_safe)
    
    async with render_lock_ctx() as acquired:
        assert acquired is True
        
        # Nested try should fail because lock is held
        async with render_lock_ctx() as acquired2:
            assert acquired2 is False
