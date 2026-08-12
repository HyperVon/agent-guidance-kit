# Harness compatibility

This is an evidence snapshot, not a product allowlist. The bootstrap workflow
profiles the active harness at adoption time, so an unknown or changed harness
can still use native discovery, a thin pointer, a narrow projection, or a manual
entrypoint.

Snapshot date: 2026-08-12. `DOCUMENTED` means current primary documentation
supports the route but this project has not yet exercised it in that harness.
`BEST_EFFORT` marks an explicit discovery gap. No row is claimed `VERIFIED`
until a fresh harness task demonstrates it.

## Primary targets

| Harness | Repository instructions | Skills from `.agents/skills/` | Kit route | Status |
| :--- | :--- | :--- | :--- | :--- |
| OpenAI Codex | `AGENTS.md` hierarchy | Native | canonical files directly | DOCUMENTED |
| Claude Code | `CLAUDE.md` and imports | Not a documented native path | thin `CLAUDE.md`; skills read from canonical index or projected during adoption | DOCUMENTED instructions; BEST_EFFORT skill routing |
| Cursor | root `AGENTS.md` and `.cursor/rules/` | Native | canonical files directly; no duplicate Cursor rule | DOCUMENTED |
| OpenCode | `AGENTS.md`; `CLAUDE.md` fallback | Native | canonical files directly | DOCUMENTED |
| Kilo Code | `AGENTS.md` and configured instructions | Native | canonical files directly | DOCUMENTED |
| Pi | `AGENTS.md` and `CLAUDE.md` context | Native | canonical files directly | DOCUMENTED |
| Muse Code | `AGENTS.md` hierarchy | Native (`.agents/skills/`) | canonical files directly | DOCUMENTED |

Primary evidence:

- [OpenAI Codex `AGENTS.md`](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
  and [skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code instructions](https://code.claude.com/docs/en/memory) and
  [skills](https://code.claude.com/docs/en/skills)
- [Cursor rules](https://cursor.com/docs/rules),
  [skills](https://cursor.com/docs/skills), and
  [CLI rules](https://cursor.com/docs/cli/using)
- [OpenCode rules](https://opencode.ai/docs/rules/) and
  [skills](https://opencode.ai/docs/skills/)
- [Kilo Code instructions](https://kilo.ai/docs/customize/custom-instructions),
  [`AGENTS.md`](https://kilo.ai/docs/customize/agents-md), and
  [skills](https://kilo.ai/docs/customize/skills)
- [Pi usage](https://pi.dev/docs/latest/usage) and
  [skills](https://pi.dev/docs/latest/skills)
- [Muse Code product page](https://developer.meta.com/ai/products/muse-code/)

## Additional popular harnesses

| Harness | Repository instructions | Skills from `.agents/skills/` | Kit route | Status |
| :--- | :--- | :--- | :--- | :--- |
| GitHub Copilot | `.github/copilot-instructions.md` and `AGENTS.md` | Native | checked-in thin Copilot entrypoint plus canonical skills | DOCUMENTED |
| Gemini CLI | `GEMINI.md`; configurable context filenames | Native | checked-in thin `GEMINI.md` imports plus canonical skills | DOCUMENTED |
| Windsurf Cascade | `AGENTS.md` and Windsurf rule files | Documented compatibility path | canonical files directly | DOCUMENTED, medium confidence |
| Cline | `AGENTS.md` and `.clinerules/` | no documented `.agents/skills/` project path | canonical instructions; manual or approved skill projection | DOCUMENTED instructions; BEST_EFFORT skill routing |
| Roo Code | root `AGENTS.md` and `.roo/rules/` | Native compatibility path | canonical files directly | DOCUMENTED |
| Aider | explicit `--read`, `/read`, or configured read-only files | no documented native Agent Skills support | manual entrypoint or explicit read configuration | BEST_EFFORT |

Primary evidence:

- [GitHub Copilot repository instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions-in-your-ide/add-repository-instructions-in-your-ide)
  and [agent skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills)
- [Gemini CLI context files](https://geminicli.com/docs/cli/gemini-md/) and
  [skills](https://geminicli.com/docs/cli/using-agent-skills/)
- [Windsurf rules](https://docs.windsurf.com/windsurf/cascade/memories),
  [skills](https://docs.windsurf.com/windsurf/cascade/skills), and
  [`AGENTS.md`](https://docs.windsurf.com/windsurf/cascade/agents-md)
- [Cline rules](https://docs.cline.bot/customization/cline-rules) and
  [skills](https://docs.cline.bot/customization/skills)
- [Roo Code instructions](https://roocodeinc.github.io/Roo-Code/features/custom-instructions/)
  and [skills](https://roocodeinc.github.io/Roo-Code/features/skills/)
- [Aider conventions](https://aider.chat/docs/usage/conventions.html) and
  [configuration](https://aider.chat/docs/config/aider_conf.html)

## Reload and verification

Reload behavior is a capability, not a kit-wide command. Examples include a
new Codex task or restart when discovery is stale, Claude Code live skill
watching with a restart when a top-level skill directory is newly created,
Gemini CLI `/memory reload` and `/skills reload`, Kilo `/reload`, and Pi
`/reload`. For harnesses without a documented reload contract, start a fresh
task or session.

After adapting a target, use a harmless prompt whose wording clearly matches
one selected skill. Ask the harness to identify the repository instruction and
skill files it used when it can expose that evidence. File presence alone earns
at most `DOCUMENTED`, never `VERIFIED`.
