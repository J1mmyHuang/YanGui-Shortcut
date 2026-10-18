# Task: Build ShanNian (闪念) for iOS Shortcuts

You are an AI coding agent with repository file access and terminal tools. Use your configured model service. Produce an actual, portable XML Apple Shortcuts plist at **dist/ShanNian.xml**. Do not produce pseudocode, rename an unsigned XML to .shortcut, or claim real iPhone testing.

Read:
- spec/闪念_Shortcuts_构建规格.md (user requirements)
- Locate the Shortcuts Playground skill directory containing SKILL.md in the available plugin or reference checkout, and read that file (mandatory).
- Relevant docs and action schemas in that skill, especially PLIST_FORMAT.md, ACTIONS.md, APPINTENTS.md, VARIABLES.md, FILTERS.md, CONTROL_FLOW.md, DATE_TIME.md, and BEST_PRACTICES.md.
- Its golden-shortcuts/index.jsonl and any directly relevant example XMLs.

Goal:
- One iPhone Action Button compatible shortcut called 闪念.
- Start with Dictate Text (or accept text input) and parse Chinese natural language.
- BYOK OpenAI-compatible Chat Completions API: user-provided base URL, model name, runtime API key on their own iPhone. Never hardcode real credentials.
- Allow exactly six genuine native iOS operations, or clarification: note.create, note.search, calendar.create, calendar.search, reminder.create, reminder.search, clarify.
- Create/search Apple Notes, Calendar and Reminders using actual Shortcuts actions / supported iOS AppIntents. Do not use macOS AppleScript, fake generated answers, Google/Notion/Drafts, broad access to unrelated apps, or extra privileges.
- For searches, retrieve real native app data before answering. Bound candidate counts and only send necessary snippets to the selected AI endpoint.
- Parse dates from the device's current local date and timezone. Ask if important details are missing; do not invent times.
- Preserve original dictated text. If API fails, offer optional save-as-Apple-Note with explicit confirmation.
- Notifications must describe real successes, not a guessed success.
- For multi-intent utterances either implement operations[] and execute all, or clearly reject and request separate utterances, never silently drop actions.
- Do not allow updates, deletes, completion changes, untrusted arbitrary actions or network URLs.
- Only send data to the configured model provider.

API schema example:
{
  "operations": [{
    "action":"note.create|note.search|calendar.create|calendar.search|reminder.create|reminder.search|clarify",
    "title":"","body":"","query":"","start":"","end":"","due":"","all_day":false,"include_completed":false,"question":""
  }]
}
Ensure parsing, expected field type checks, and routing are robust.

Build verification:
1. Resolve icon/color via the plugin helper. Generate fresh uppercase UUIDs and correct magic variables; avoid Unknown Actions.
2. Run the Shortcuts Playground validate_shortcut.py in a targeted fix loop (max 5 actual fixes), **with --target-platform ios**. Also run Python plistlib and macOS plutil.
3. Write **dist/FEATURES.md** with an explicit table of each of the six operations: implemented and preflight-verified / implemented but not verified / not implemented. Include static validator output, any unresolved errors, and required on-device checks. Be truthful: never mark something working merely because a syntactically valid plist exists.
4. Generate **dist/ShanNian.xml**. On a Mac, archive and sign the XML using the native shortcuts tool. In an environment without Apple signing support, report unsigned-only output and leave signing instructions. Never export Apple Account credentials.
5. Avoid downloading arbitrary dependencies; use the checked-out repo and the available Shortcuts Playground reference.

Remember: user wants a minimal personal assistant, not a generic agent. Full native read and write of those three Apple apps is the acceptance target.
