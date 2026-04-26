# Production Readiness Checklist

This document tracks items that must be addressed or verified before Flux is considered production-ready.

## Foundation & Security
- [ ] **Master Key Security**: Ensure `FLUX_MASTER_KEY` is generated securely and stored in a persistent environment variable (not hardcoded or lost on restart).
- [ ] **Credential Migration**: Verify that all platform worker credentials stored in the database are encrypted using the Fernet service.
- [ ] **Database WAL Mode**: Confirm that WAL mode is active on the physical Termux device to prevent SQLite locking issues during concurrent renders/API calls.

## Hardware & Environment
- [ ] **Termux Storage Permission**: Ensure `termux-setup-storage` has been run and the app can write to `/storage/emulated/0/Flux`.
- [ ] **FFmpeg Performance**: Validate that FFmpeg renders on the device do not cause thermal throttling or system kills.
- [ ] **Wake Lock**: Confirm `termux-wake-lock` prevents Android from sleeping during renders.

## Content & Plugins
- [ ] **Real Quran Plugin**: Replace the Phase 0 dummy Quran plugin with the real implementation (Surah/Ayah selection, actual API integration).
- [ ] **Plugin Manifests**: Implement a manifest-based validation for plugins in `loader.py` (e.g., `manifest.json` check).

## Observability
- [ ] **Log Rotation**: Verify that `FileHandler` rotation in `flux/logger.py` is working as expected on the device.
- [ ] **Activity Log**: Monitor the `activity_log` table for any persistent errors during background jobs.
