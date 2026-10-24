# Task: Build YanGui (言归) for iOS Shortcuts

You are an AI coding agent with repository file access and terminal tools. Use your configured model service. Produce an actual, portable XML Apple Shortcuts plist at **dist/YanGui.xml**. Do not produce pseudocode, rename an unsigned XML to .shortcut, or claim real iPhone testing.

Read:
- spec/言归_Shortcuts_构建规格.md (user requirements)
- Locate the Shortcuts Playground skill directory containing SKILL.md in the available plugin or reference checkout, and read that file (mandatory).
- Relevant docs and action schemas in that skill, especially PLIST_FORMAT.md, ACTIONS.md, APPINTENTS.md, VARIABLES.md, FILTERS.md, CONTROL_FLOW.md, DATE_TIME.md, and BEST_PRACTICES.md.
- Its golden-shortcuts/index.jsonl and any directly relevant example XMLs.

Goal:
- One iPhone Action Button compatible shortcut called 言归.
- One press of the Action Button starts Dictate Text (Chinese) directly; parse the Chinese natural language and split it into independent items.
- BYOK with a user-selected protocol, OpenAI-compatible Chat Completions or Anthropic-compatible Messages: protocol, base URL, API key and model name asked as import questions and held in four Text actions at the top of the shortcut; a blank model is chosen from the service's /models list. Encode request bodies with the WFItemType codes of real exports (0 text, 1 dictionary, 2 array, 3 number, 4 boolean). Keep them blank in the repository; never hardcode real credentials.
- Allow exactly six genuine native iOS operations: note.create, note.search, calendar.create, calendar.search, reminder.create, reminder.search. The AI classifies each item into Notes, Reminders or Calendar.
- Create/search Apple Notes, Calendar and Reminders using actual Shortcuts actions / supported iOS AppIntents. Do not use macOS AppleScript, fake generated answers, Google/Notion/Drafts, broad access to unrelated apps, or extra privileges.
- For searches, retrieve real native app data before answering. Bound candidate counts and only send necessary snippets to the selected AI endpoint.
- Parse dates from the device's current local date and timezone. Do not invent times; uncertain dates become notes that keep the original wording.
- Preserve original dictated text. If the API fails, save it automatically as an Apple Note; offer a backup switch that saves it before every request.
- Notifications must describe real successes, not a guessed success.
- For multi-intent utterances implement operations[] and execute every item in order; a failing item falls back to a note without blocking the others.
- Do not allow updates, deletes, completion changes, untrusted arbitrary actions or network URLs.
- Only send data to the configured model provider.

API schema example:
{
  "operations": [{
    "action":"note.create|note.search|calendar.create|calendar.search|reminder.create|reminder.search",
    "title":"","body":"","query":"","start":"","end":"","due":"","all_day":false,"include_completed":false,"checklist":false
  }]
}
Ensure parsing, expected field type checks, and routing are robust.

Build verification:
1. Resolve icon/color via the plugin helper. Generate fresh uppercase UUIDs and correct magic variables; avoid Unknown Actions.
2. Run the Shortcuts Playground validate_shortcut.py in a targeted fix loop (max 5 actual fixes), **with --target-platform ios**. Also run Python plistlib and macOS plutil.
3. Write **dist/FEATURES.md** with an explicit table of each of the six operations: implemented and preflight-verified / implemented but not verified / not implemented. Include static validator output, any unresolved errors, and required on-device checks. Be truthful: never mark something working merely because a syntactically valid plist exists.
4. Generate **dist/YanGui.xml**. On a Mac, archive and sign the XML using the native shortcuts tool. In an environment without Apple signing support, report unsigned-only output and leave signing instructions. Never export Apple Account credentials.
5. Avoid downloading arbitrary dependencies; use the checked-out repo and the available Shortcuts Playground reference.

Remember: user wants a minimal personal assistant, not a generic agent. Full native read and write of those three Apple apps is the acceptance target.
