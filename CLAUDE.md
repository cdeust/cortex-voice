# cortex-voice

On-device voice capture MCP for Cortex (macOS, Apple Speech). Python.

Global rules are imported, not restated:

## Repo-specific constraints

- Ears only: 'listen' transcribes, then hands off to Cortex's recall/remember. It never reads or writes memories itself.
- Requires Microphone and Speech Recognition permissions; check_voice_setup compiles the helper and requests them.

## Etiquette

Conventional commits, staged file-by-file. One PR per concern. Do not merge your own PR without the owner's go-ahead.

## Non-negotiables

- CI contract (`docs/agent-guidance.md`, "CI contract for agents and routines"): it binds
  every agent and routine and wins over a less restrictive routine prompt. One pull request in flight, no
  comparison with the main branch, no forced push, no comment after an approve.
