# Local macOS AI-agent task: iOS Shortcut 闪念

You are an AI coding agent running locally on a Mac with repository file access and terminal tools.
Use the agent's configured model service. Runtime BYOK on iPhone is configured separately by the recipient.
Locate Shortcuts Playground's skill directory containing SKILL.md and scripts in an available plugin or reference checkout.
Read its action schemas and examples, build a real XML plist, validate it, and sign with Apple's native tool on a Mac.
Report missing dependencies and unverified behavior. Never upload Apple credentials or put real API keys in source.

Read fully:
1. `spec/闪念_Shortcuts_构建规格.md` (the complete requirements)
2. the installed `shortcuts-playground` plugin's `SKILL.md`, `PLIST_FORMAT.md`, `ACTIONS.md`, `APPINTENTS.md`, `VARIABLES.md`, `CONTROL_FLOW.md`, `FILTERS.md`, `DATE_TIME.md`, `BEST_PRACTICES.md` and directly relevant golden examples.
3. `LOCAL_BUILD.md` for deliverable expectations.

Build one iPhone/iOS Shortcut called **闪念**, using Apple native Notes, Calendar and Reminders and ONLY these six allowed operations:
- note.create / note.search
- calendar.create / calendar.search
- reminder.create / reminder.search

Invocation: iPhone Action Button launches Shortcut. Capture Dictate Text in Chinese (allow text fallback), ask AI to classify intent, identify necessary data and/or ask for clarification. BYOK must accept custom OpenAI-compatible base URL, model, and runtime API key, but NEVER hardcode a real secret in source or checked-in files. Use only native Shortcut actions for Apple Notes/Calendar/Reminders (no macOS-only scripting). No blanket sync or export of personal data. Queries must retrieve real matching app records before making an answer. Bound result counts. Handle date/time interpretation using device local timezone; don't invent dates, times, or reminders. Don't silently drop multiple requests. Preserve voice transcript on API or permission errors; offer to save original words as Note only after explicit confirmation. No delete/update/completion or other App access.

Plan the data flow and routing. Build real `dist/ShanNian.xml`, not fictitious shortcuts, Markdown steps, or placeholder action names. Generate uppercase UUIDs and correctly wire magic variables, conditional branches, dictionaries, and model JSON parsing. Model is only allowed to select among six actions and clarify. Validate returned JSON and fail safely if missing or malformed data.

Mandatory:
1. Resolve icon and colors using installed plugin resolver.
2. Run its validator in a targeted repair loop at most 5 fix attempts with `--target-platform ios`, and a macOS-target appropriate for installed OS; don't use OS 27-only actions unless necessary and supported by the target. Run `plutil -lint` and Python `plistlib` as an additional sanity check.
3. Write `dist/FEATURES.md` with an explicit table: implemented and statically validated / implemented unverified / missing for each six operations. Include unresolved issues, real-device test cases, and notable secrets/privacy implications. Do not claim iPhone tests.
4. Archive unsigned XML and use installed plugin's `sign_shortcut.sh` or macOS `shortcuts sign --mode anyone` to create **`dist/ShanNian.shortcut`**. Confirm output exists and size > 0 before declaring signing successful. If signing fails, leave XML and full error log for correction. No workaround that forges a fake .shortcut.
5. Keep secrets and personal notes/calendars/reminders OUT of the repository. Any on-device runtime key setup should be transparent; explicitly warn if key ends up in the Shortcut plist/Shortcuts-synced storage.
6. Prioritize a working, repairable native shortcut over fancy UI; no third-party apps.

User-facing progress should be brief. On completion provide exact output paths, validated aspects, gaps and the iPhone import steps. If any one of six operations remains unsupported, say so explicitly.
