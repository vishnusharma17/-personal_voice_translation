# Efficiency Rules

Goal: maximum useful work per token without sacrificing correctness.

## Context loading

Always:
- `AGENTS.md`
- `STATUS/CURRENT.md`

Normally:
- relevant parts of `BRAIN/PRODUCT.md`
- relevant parts of `BRAIN/ARCHITECTURE.md`

Only when relevant:
- other brain/rule/workflow files.

Do not reread the entire project knowledge base on every task.

## File inspection

- Search for the relevant file/symbol first.
- Read the smallest useful scope.
- Inspect dependencies only when required.
- Do not open unrelated directories for background.

## Task size

Tiny:
- inspect → fix → targeted verification.

Normal:
- inspect → short plan → implement → targeted tests.

Large:
- plan → specialist review → implement in slices → verify each slice.

## Output

Do not narrate every thought.
Do not repeat known context.
Do not produce long explanations for simple changes.
Report concise results and blockers.

## No repeated work

Before editing:
- check `STATUS/CURRENT.md`;
- inspect git status/diff;
- check whether the requested feature already exists.

Never rebuild completed functionality without evidence of a problem.

## Verification

Token optimization must never remove required tests or safety checks.

## Failure

After three materially different failed fixes for the same blocker:
- stop;
- document the evidence in `STATUS/CURRENT.md`;
- ask/report only what is necessary.
