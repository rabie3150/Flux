# Flux — User Personas & Journey Maps

## 1. Primary Persona: The Operator (Omar)

> **"I built this because I got tired of manual posting. Now I want it to run forever and grow with me."**

| Attribute | Detail |
|-----------|--------|
| **Name** | Omar (archetype) |
| **Age** | 25–40 |
| **Role** | Solo creator, developer, or community manager |
| **Technical Level** | High — writes Python, uses Linux daily, comfortable with SSH and APIs |
| **Hardware** | Old Android phone (2019–2021) running Termux; laptop for admin access |
| **Motivation** | Automate repetitive content tasks; maintain consistent social presence for Islamic and future niche accounts |
| **Frustration** | SaaS tools are expensive and lack deep automation; existing self-hosted tools assume a server |
| **Goals** | 1) Set up once, run for months. 2) Add new content types without rewriting. 3) Monitor remotely with minimal friction. |

### Behaviours
- Checks Telegram bot notifications rather than logging into the admin panel proactively.
- Prefers editing JSON/config files over clicking through wizards.
- Wants to SSH in and read logs when something breaks.
- Values being able to explain exactly how the system works to others (transparency).

---

## 2. Secondary Persona: The Future Collaborator (Aisha)

> **"Omar showed me his setup. I want to run a similar pipeline for my own content without learning his entire stack."**

| Attribute | Detail |
|-----------|--------|
| **Name** | Aisha (archetype) |
| **Age** | 22–35 |
| **Role** | Content creator, non-developer but tech-curious |
| **Technical Level** | Medium — can edit YAML, use a terminal, but does not write Python from scratch |
| **Motivation** | Wants the same automation power without building it herself |
| **Frustration** | Documentation assumes deep Linux knowledge; plugin development looks intimidating |
| **Goals** | 1) Install Flux on her own phone with a clear guide. 2) Enable/disable existing plugins via UI. 3) Configure schedules and sources without coding. |

### Design Implication
- The admin panel must expose plugin configuration in a structured form (not raw JSON).
- Setup documentation must include a "non-developer quickstart" path.
- Plugin marketplace / registry should allow one-click installation of community plugins.

---

## 3. Journey Map: Setting Up the First Pipeline (Quran)

### Phase 1: Installation (Day 1)
| Step | Action | Omar's Emotional State | Pain Point | Opportunity |
|------|--------|------------------------|------------|-------------|
| 1 | Installs Termux from F-Droid | Curious | Finding the right Termux version (F-Droid vs Play Store) | One-command bootstrap script detects environment |
| 2 | Runs bootstrap: `curl ... | bash` | Hopeful | Package install takes time on slow phone | Progress bar + estimated time |
| 3 | Configures `.env` with API keys | Focused | Scattered docs for Pexels, YouTube API | Single-page setup checklist in admin panel |
| 4 | Starts daemon with `~/flux/start.sh` | Excited | Port 8000 is localhost-only; needs SSH port-forward | Bootstrap script prints access instructions |
| 5 | Opens admin panel via `ssh -L` | Satisfied | — | First-run wizard highlights next steps |

### Phase 2: First Content Cycle (Days 2–3)
| Step | Action | Emotional State | Pain Point | Opportunity |
|------|--------|-----------------|------------|-------------|
| 1 | Adds whitelisted YouTube channel | Confident | Copy-pasting channel URLs is tedious | Bookmarklet to paste channel from browser |
| 2 | First fetch job runs; clips appear as "pending" | Anticipating | Waiting for downloads | Real-time download progress in admin panel |
| 3 | Reviews and approves 10 clips | Judgmental | Thumbnails load slowly on LAN | Pre-generated low-res thumbnails |
| 4 | First render job runs overnight | Patient | Phone gets warm | Thermal-aware scheduling (pause if > 45 degrees C) |
| 5 | Wakes up to "1 video ready" Telegram message | Delighted | — | Deep link to preview and one-click post |

### Phase 3: Steady State (Week 2+)
| Step | Action | Emotional State | Pain Point | Opportunity |
|------|--------|-----------------|------------|-------------|
| 1 | Checks Telegram — "Posted to YouTube + Telegram" | Relaxed | Occasionally wants to tweak caption | Inline "Edit next caption" reply to bot |
| 2 | Storage alert at 80% | Mild concern | Manually deciding what to delete | Smart cleanup suggestions (oldest published) |
| 3 | Wants to add Instagram account | Ambitious | Instagrapi session setup is cryptic | Guided session login via admin panel QR code |
| 4 | Phone reboots after update | Anxious | "Did it come back?" | Boot notification + self-health check report |
| 5 | Considers adding a new content type | Visionary | "How hard is it to build a plugin?" | Plugin template generator in CLI |

---

## 4. Journey Map: Adding a Future Content Pipeline (Month 6)

This journey validates the future-proofing requirement.

| Step | Action | Emotional State | Pain Point | Opportunity |
|------|--------|-----------------|------------|-------------|
| 1 | Decides to add "Daily Hadith" images | Inspired | No existing plugin | Downloads community plugin or writes own |
| 2 | Places plugin in `./plugins/hadith/` | Hopeful | Unclear interface contract | Plugin linting/validation command |
| 3 | Restarts daemon; plugin auto-registers | Surprised | — | Restart required to load new plugins |
| 4 | Configures sources (hadith API, image template) | Focused | Different data model than Quran | Generic "source" abstraction in admin UI |
| 5 | Pipeline runs first cycle | Proud | — | "New pipeline active" celebration notification |

---

## 5. Emotional Journey Summary

```
Excitement          |  ####
                    |      ####
Confidence          |        ########
                    |              ################
Relaxation          |                             ############################
                    |
Anxiety (spikes)    |              ##                    ##        ##
                    +--------------------------------------------------------->
                     Install   First fetch   First post   Steady state   Future plugin
```

**Key insight:** The system must minimize anxiety spikes. Every unexpected state (reboot, error, full storage) should be met with automatic recovery + a clear, actionable notification.
