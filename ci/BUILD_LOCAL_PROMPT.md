# Local macOS AI-agent task: iOS Shortcut 闪念

You are an AI coding agent running **locally on the user's Mac**, with permission to read/write this repository and execute terminal commands. Use the agent's existing configured model and authentication. Do not request or create a GitHub Actions API secret. Runtime BYOK on iPhone is configured separately by the recipient. The user wants a real iOS shortcut, not an implementation plan.

Locate the Shortcuts Playground skill directory containing `SKILL.md` and `scripts/` through the agent's available plugin or a checkout under `.ci-tools/shortcuts-playground/`. Read its reference files and execute its scripts directly. If the reference is unavailable, report that missing dependency. Start from `preview/`'s existing generator, tests, and recorded Notes compatibility failures when practical; do not claim these are already resolved.

Read fully:
1. `spec/闪念_Shortcuts_构建规格.md` (the complete requirements)
2. the available Shortcuts Playground reference's `SKILL.md`, `PLIST_FORMAT.md`, `ACTIONS.md`, `APPINTENTS.md`, `VARIABLES.md`, `CONTROL_FLOW.md`, `FILTERS.md`, `DATE_TIME.md`, `BEST_PRACTICES.md` and directly relevant golden examples. Record the reference version used.
3. `LOCAL_BUILD.md` for deliverable expectations.

Build one iPhone/iOS Shortcut called **闪念**, using Apple native Notes, Calendar and Reminders and ONLY these six allowed operations:
- note.create / note.search
- calendar.create / calendar.search
- reminder.create / reminder.search

Invocation: one press of the iPhone Action Button starts Chinese Dictate Text immediately; finishing the dictation runs the rest automatically. The AI splits the speech into independent items and classifies each into Notes, Reminders or Calendar (or a native query); the shortcut writes them all in order and reports with one notification. BYOK: the API protocol (openai or anthropic), base URL, API key and model are asked as import questions and live in four Text actions at the very top of the shortcut so the user can edit them; a blank model lists the service's /models and lets the user pick; the checked-in XML keeps them blank and never contains a real secret. Use only native Shortcut actions for Apple Notes/Calendar/Reminders (no macOS-only scripting). No blanket sync or export of personal data. Queries must retrieve real matching app records before making an answer. Bound result counts. Handle date/time interpretation using device local timezone; don't invent dates, times, or reminders. Never drop an item of a multi-item dictation. Preserve the voice transcript on API errors by saving it as a Note automatically, and provide a backup switch that saves it before every request. No delete/update/completion or other App access.

Plan the data flow and routing. Build real `dist/ShanNian.xml`, not fictitious shortcuts, Markdown steps, or placeholder action names. Generate uppercase UUIDs and correctly wire magic variables, conditional branches, dictionaries, and model JSON parsing. Model is only allowed to select among six actions and clarify. Validate returned JSON and fail safely if missing or malformed data.

Mandatory:
1. Resolve icon and colors using installed plugin resolver.
2. Run its validator in a targeted repair loop at most 5 fix attempts with `--target-platform ios`, and a macOS-target appropriate for installed OS; don't use OS 27-only actions unless necessary and supported by the target. Run `plutil -lint` and Python `plistlib` as an additional sanity check.
3. Write `dist/FEATURES.md` with an explicit table: implemented and statically validated / implemented unverified / missing for each six operations. Include unresolved issues, real-device test cases, and notable secrets/privacy implications. Do not claim iPhone tests.
4. Archive unsigned XML and use installed plugin's `sign_shortcut.sh` or macOS `shortcuts sign --mode anyone` to create **`dist/ShanNian.shortcut`**. Confirm output exists and size > 0 before declaring signing successful. If signing fails, leave XML and full error log for correction. No workaround that forges a fake .shortcut.
5. Keep secrets and personal notes/calendars/reminders OUT of the repository. Any on-device runtime key setup should be transparent; explicitly warn if key ends up in the Shortcut plist/Shortcuts-synced storage.
6. Prioritize a working, repairable native shortcut over fancy UI; no third-party apps.
7. Preserve the top Comment identifying the project as free open-source software and linking to `https://github.com/J1mmyHuang/ShanNian-Shortcut`. This notice belongs in a non-executing Comment, not a runtime alert or model prompt. Preserve the project's AGPL-3.0-or-later license and third-party attribution.

User-facing progress should be brief. On completion provide exact output paths, validated aspects, gaps and the iPhone import steps. If any one of six operations remains unsupported, say so explicitly.
