# Taste

## Review Protocol

- Prefers adversarial/diff reviews to be performed by a single fresh-context subagent rather than by the same context that made the changes, because reviewing in the same context makes the agent more likely to agree with itself. Confidence: 0.9
- Requires the review to converge — no additional validated findings — before proceeding with a push/PR. Confidence: 0.8
- Expects an adversarial/diff review to run as a mandatory step after creating a PR — the user explicitly asked for this to be encoded into the repo's skills/guidance so it no longer depends on the adversarial-pr-review skill's literal opt-in triggers or the stored taste profile; the taste profile should be checked before pushing. Confidence: 0.9
- Prefers a single fresh-context subagent reviewer over a scheme using two reviewers of different calibers/intelligence. Confidence: 0.8
- Prefers review verdicts to be compact and bounded: return only PASS or FINDINGS with at most three anchored repo-relative `path:line` findings (with severity and impact), and stop further inspection/commands once the verdict is reached. Confidence: 0.8
- After a review report, prefers to approve and apply the full batch of findings at once (e.g. "address all of your findings") rather than approving each finding individually, with application performed as a separate authorized pass after the read-only review. Confidence: 0.6
