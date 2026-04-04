# @.codex AGENTS Reference

Skills live under `.agents/skills/<skill-name>/SKILL.md`, and the CLI exposes them via the same names. Use the skill name exactly as listed below whenever you need that workflow.

| Skill Directory | Purpose |
|-----------------|---------|
| `speckit-analyze` | Entry point for surveying specifications, code, and tasks to scope a feature. |
| `speckit-checklist` | Guidance to verify checklist completion and gate entry into implementation. |
| `speckit-clarify` | Used when unanswered questions must be resolved before design or coding. |
| `speckit-constitution` | Encodes the constitutional rules, quality gates, and non-functional requirements for the feature set. |
| `speckit-implement` | Instructions for executing the implementation phase once design and planning are solid. |
| `speckit-plan` | Template for generating and updating the overall implementation plan (phases, docs, output). |
| `speckit-specify` | Used to craft or refine the feature specification when requirements change. |
| `speckit-tasks` | Task-generation template for turning specs into executable steps with dependencies. |
| `speckit-taskstoissues` | Translates task lists into issue tracker-friendly formats for follow-up work. |
| `imagegen` | Generate or edit raster images when bitmap assets are needed. |
| `openai-docs` | Official OpenAI docs-guided prompts for building with OpenAI APIs or products. |
| `plugin-creator` | Scaffold or update Codex plugins with the required manifest and placeholders. |
| `skill-creator` | Guide for creating or updating skills; expands the set of documented workflows. |
| `skill-installer` | Install new skills from curated git sources or listings into the local Codex runtime. |
