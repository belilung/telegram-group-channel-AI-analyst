# Skill Audit Scorecard

## Summary

- **Total skills audited:** 13
- **Folder distribution:** 13 global, 0 project
- **Frontmatter failures:** 0 (all 13 passed)
- **Run:** 2 (re-audit after fixes). See "Changes since run 1" below.

## Ranked Scorecard (Worst → Best)

| Rank | Skill | Folder | Clarity | Frontmatter | Trigger | Composite | Highest-value fix |
|------|-------|--------|---------|-------------|---------|-----------|-------------------|
| 1 | implement | global | 3 | pass | 2 | 5/10 | Add a concrete code example showing how to invoke a feature-implementer sub-agent via Task tool, including required prompt fields (task ID, files, acceptance criteria, plan context) and expected return states (DONE/BLOCKED/PARTIAL). |
| 2 | gsap | global | 4 | pass | 2 | 6/10 | Add a "When to reach for GSAP" section listing concrete triggers: animating many elements with transforms, chaining sequences, interactive motion; and when NOT to use it (single CSS transition). |
| 3 | brainstorm | global | 3 | pass | 3 | 6/10 | Translate the entire skill to English or provide an English version for global distribution, or add concrete trigger examples ("when user says 'I want to add', 'refactor', 'architectural change'") in the description field itself. |
| 4 | continuous-learning-v2 | global | 4 | pass | 3 | 7/10 | Replace the vague trigger description with a concrete decision tree showing exact user scenarios for each of the six commands. |
| 5 | video-use | global | 4 | pass | 3 | 7/10 | Add a TRIGGER section immediately after the frontmatter stating explicit conditions (video provided + edit/cut/grade/animate, or transcription/subtitle/color requests). |
| 6 | zelta-design | global | 5 | pass | 3 | 8/10 | Add explicit trigger examples to the description such as: "Invoke when designing Zelta home screen, balance card, payment UI, or any Zelta wallet component across platforms." |
| 7 | telethon-patterns | global | 4 | pass | 4 | 8/10 | Add a section on handling AuthKeyError and session invalidation recovery to make the skill more complete for production Telegram monitors. |
| 8 | hyperframes-registry | global | 4 | pass | 4 | 8/10 | Inline the full content of the referenced .md files (install-locations, wiring-blocks, wiring-components, discovery) directly into the skill. |
| 9 | hyperframes-cli | global | 5 | pass | 4 | 9/10 | Add a "When to use this skill vs hyperframes skill" section clarifying CLI operations vs composition authoring. |
| 10 | fastapi-patterns | global | 4 | pass | 5 | 9/10 | Add a section on request body validation and customizing 422 validation error responses. |
| 11 | hyperframes | global | 4 | pass | 5 | 9/10 | Add a single decision tree at the top ("New composition? Edit existing? Add captions? Route to section X"). |
| 12 | website-to-hyperframes | global | 4 | pass | 5 | 9/10 | Specify in Step 1 exactly which tool/skill captures the website (name the tool, or clarify if Playwright handles it). |
| 13 | claude-code-plugin-dev | global | 5 | pass | 5 | 10/10 | Add a SKIP clause ("SKIP when working on standalone skills outside a plugin distribution context"). |

## Changes since run 1 (after applying fixes)

| Skill | Run 1 | Run 2 | Δ | Note |
|-------|-------|-------|---|------|
| claude-code-plugin-dev | 8 | **10** | +2 | bad/good path example added → now top-ranked |
| continuous-learning-v2 | 5 | **7** | +2 | was worst skill; Command Decision Matrix + trigger in description |
| fastapi-patterns | 9 | 9 | 0 | already strong; Middleware/CORS added, fix request moved to 422 validation |
| zelta-design | 8 | 8 | 0 | "When NOT to use" added; residual ask is trigger examples in description |

**Evaluator noise (no edits, scores still moved — Haiku variance):** hyperframes-cli 6→9, telethon-patterns 7→8, hyperframes-registry 10→8. Treat ±1–2 as scoring jitter, not real change.

## Cross-cutting patterns

- **Frontmatter is universally healthy.** All 13 skills have valid YAML with both `name` and `description` — zero malformations.
- **Trigger quality remains the dominant weakness.** Lowest score on 9 of 13 skills and drives the entire bottom half. Recurring failure mode: describing *what the skill does* rather than *concrete user phrases/conditions* that signal activation.
- **Clarity is consistently solid (3–5, mostly 4).** No skill is hard to follow; the gap is missing concrete examples (Task-delegation syntax, gotchas sections, step-by-step agent guidance).
- **The HyperFrames family scores well** (composite 8–9); residual issues are navigational (decision trees, cross-skill disambiguation, inlining references), not fundamental.
- **Workflow/orchestration skills lag content skills.** implement, brainstorm, and continuous-learning-v2 cluster at the bottom — vague triggers, and for brainstorm a Russian-only body.
- **Several skills lack SKIP/negative-scope guidance.** Even top-rated claude-code-plugin-dev would benefit from an explicit SKIP clause.

## Quick wins (remaining)

1. **implement** — Add a concrete Task-tool invocation example with required prompt fields and expected return states (DONE/BLOCKED/PARTIAL). Fixes the lowest composite + weakest trigger.
2. **gsap** — Add a "When to reach for GSAP" section with concrete triggers and a when-NOT-to-use note. *(external symlink — edits `.agents/skills/gsap`.)*
3. **brainstorm** — Provide an English version, or add English trigger examples to the description.
4. **continuous-learning-v2** — Turn the command list into a decision tree mapping exact user scenarios to each command.
5. **video-use** — Add an explicit TRIGGER section after the frontmatter. *(external symlink — edits `hyperframes-video-redactor`.)*

---
*Run 2 generated 2026-06-01 by skill-audit workflow — 13 Haiku worker agents + 1 ranking agent. Project folder `.claude/skills/` contained no skills.*
