---
name: flux-debug
description: >
  Debug and fix bugs in the Flux content automation app.
  Use when asked to fix, debug, investigate, or resolve errors, crashes,
  test failures, or unexpected behavior in any part of the Flux codebase.
  Follows evidence-first root cause analysis with minimal invasive fixes.
---

# Flux Debug Skill

## Philosophy

Never assume. Gather runtime evidence first. Fix at the right layer. Test on device.

## Debug Protocol

### Step 1: Reproduce
- Get the exact error message, traceback, or log line.
- Identify the smallest input/action that triggers the bug.
- If it only happens on Termux, do not fix on laptop and hope.

### Step 2: Read All Relevant Code
- Read the failing function.
- Read every caller of that function (use grep).
- Read related config/schema if data is involved.
- Check recent git commits that touched this code.

### Step 3: Bisect
- If it used to work, find the last known good commit.
- If it never worked, find where the logic was introduced.
- Check if the bug is in the caller (wrong arguments) or callee (wrong handling).

### Step 4: Root Cause (5 Whys)
- Why did it fail? → Surface cause.
- Why did that happen? → Deeper cause.
- Keep asking until you hit: missing validation, wrong assumption, or env mismatch.

### Step 5: Fix at the Right Layer
- Symptom in API but root cause in DB schema? Fix schema + migration.
- Symptom in render but root cause in ingredient metadata? Fix fetch.
- Never patch 5 call sites when fixing 1 callee is correct.

### Step 6: Test
- Write a test that FAILS before the fix and PASSES after.
- If the bug is Termux-specific, add a `@pytest.mark.device` test.
- Run the full test suite to ensure no regressions.

## Common Flux-Specific Traps

### SQLite & APScheduler
- Job stuck in "executing" after crash? Startup recovery must reset it.
- Duplicate posts? Check `(produced_content_id, worker_id)` unique constraint.
- Scheduler not firing? Verify `misfire_grace_time` and timezone.

### FFmpeg on ARM
- Filtergraph errors are almost always syntax issues, not performance.
- `colorkey` values need tuning per source clip quality.
- Test FFmpeg commands in isolation before embedding in Python.

### Platform Workers
- Instagrapi session expired? Check session file age and refresh logic.
- YouTube quota exceeded? Check `quota` table before every upload.
- Telegram fails silently? Verify bot token and chat ID.

### Termux Specific
- Path issues? Check `termux-setup-storage` was run.
- Permission denied? External storage paths need Android scoped storage.
- Process killed? Check `termux-wake-lock` and battery optimization.

## Forbidden Fixes

- `except Exception: pass` → Always log or re-raise.
- `time.sleep()` in async code → Use `await asyncio.sleep()`.
- Monkey-patching library internals → Fix upstream or vendor properly.
- Adding a guard at 5 call sites → Fix the function that should guarantee the invariant.

## Post-Fix Checklist

- [ ] Test fails before fix, passes after.
- [ ] No `print()` debugging left behind.
- [ ] No broad `except Exception` added.
- [ ] If schema changed: migration exists.
- [ ] If config changed: `.env.example` updated.
- [ ] Audit script re-run and passing.
