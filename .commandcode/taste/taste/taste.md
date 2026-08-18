# Taste
- Keeps agent skills in a repo-root `skills/` directory (standard Agent Skills format with `SKILL.md`) and expects them to be made available to Command Code rather than moving them into a default location like `.commandcode/skills/`. Confidence: 0.6
- Prefers the agent to commit and push to a new branch and open a PR, while the user performs the merge themselves. Confidence: 0.95
- Treats push/PR authorization as separate from review authorization; never pushes, commits, or opens PRs without explicit user instruction (and expects the user to explicitly authorize a push). Confidence: 0.9
- Keeps review findings in the working tree, uncommitted and unstaged for user review, after an approved change pass. Confidence: 0.6
- Prefers the full project gate (validators, tests, link checks, linters) to run green immediately before commit and again before push, and the branch to be reconciled with the latest `origin/main` before pushing. Confidence: 0.7
- Prefers a distinct descriptive `fix/...` branch name and staging exactly the task files, deliberately excluding unrelated untracked directories (e.g. `.commandcode/`) from the commit. Confidence: 0.7
- Prefers mandatory process steps (e.g. post-PR adversarial review) to be encoded into the repo's skills/guidance (AGENTS.md, skill SKILL.md definitions) so they persist as policy, rather than remaining implicit in the taste profile. Confidence: 0.7
