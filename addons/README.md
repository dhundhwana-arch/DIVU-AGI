# Add-ons

First-party add-on examples for DIVU AI.

**Status: reserved for Phase 7.** The Add-on SDK, registry, validator, scanner and sandbox runner
are specified in [../docs/ADDON_SDK_GUIDE.md](../docs/ADDON_SDK_GUIDE.md) and are scheduled for
Phase 7 (Developer Studio and Dynamic Add-ons). This directory is part of the repository layout
from day one so the extension surface is visible and reserved.

Until Phase 7 lands, this directory contains no installable add-ons. Nothing here is trusted or
auto-loaded: when the registry ships, every add-on must pass

```
create → validate → scan → sandbox test → approve → install → register → activate
```

and AI-generated add-on code will require explicit human approval before activation.

See also:
* [../docs/ADDON_SDK_GUIDE.md](../docs/ADDON_SDK_GUIDE.md) — manifest, SDK surface, lifecycle
* [../docs/AGENT_DEVELOPMENT_GUIDE.md](../docs/AGENT_DEVELOPMENT_GUIDE.md) — agent contract (Phase 5)
* [../docs/DEVELOPMENT_ROADMAP.md](../docs/DEVELOPMENT_ROADMAP.md) — phase plan
