# Galkin's Skills

Reusable Agent Skills.

## Install

```bash
npx skills add galkin/skills
```

## After changing a skill

Update it in every local project that installs it: [`AGENTS.md`](AGENTS.md) › After you change a skill.

## Development folders

`lorekeep/` is the source of the lorekeep CLI and its skill (tests, ADRs, issues); `skills/lorekeep/`
is built from it by `lorekeep skill --build` and released as the tag `lorekeep-v<version>`. See
[`lorekeep/README.md`](lorekeep/README.md).
