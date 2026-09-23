## Decision

**The live demo uses `openai/gpt-oss-120b` with prompt v2, reasoning effort `low`.**

- It is the only model that returned a valid plan for every case: 24 of 24 on the first
  attempt, and 21 of 24 with no quality warnings at all. Three of the remaining warnings are
  "weak unit started late" in `chem-all-weak`, where all nine units are marked weak and can't
  all start in the first half.
- `gpt-oss-20b` is about three times faster (median 1.4 s against 4.0 s) but returned a valid
  plan only 71% of the time with prompt v2. Most of its failures were schema rejections that
  persisted through the retry. A study plan is generated once and read for weeks, so a few
  extra seconds are worth a plan that works.
- Cost: nothing, on Groq's free tier. A plan is about 2,700 tokens including the retry when
  there is one, so the free allowance (200K tokens a day per model) covers roughly 70 plans a
  day. That's the reason for the app's own daily token budget of 150K: it stays under the
  provider's quota, and the planner says "try again tomorrow" instead of failing mid-request.

The `fake` row is a baseline, not a model: code that follows the rules by construction
(weak units first, then units in order, last week for review). It scores well on the rule
checks but plans mechanically and uses only about a fifth of the available classes, where
`gpt-oss-120b` uses nearly all of them. A model has to beat it on judgement, not on rules.

## What the evals changed

- **Prompt v1 → v2.** With v1, `gpt-oss-120b` produced a valid plan every time but only 62%
  were clean; 14 of its 19 warnings were "unit never covered", concentrated in short plans.
  The cause was the prompt, not the model: one rule said review weeks shouldn't introduce new
  material, so the model listed no topics for them, while another required every unit to be
  covered. v2 says review weeks list the topics they review and short plans combine units.
  Clean plans went from 62% to 88%, "unit never covered" from 14 to 0, and first-attempt
  success from 88% to 100%.
- **Strict mode isn't a guarantee.** Groq's `json_schema` strict mode validates the output
  after generation and returns HTTP 400 `json_validate_failed` rather than constraining
  decoding. The client treats that as a schema error, and the planner gives the model its one
  corrective retry with the validation message, the same path as any other rule break.
- **Provider defaults matter.** `qwen/qwen3.8-27b` first ran with every response cut off at
  exactly 2,048 tokens: the provider's default output limit, eaten by the model's reasoning.
  Requests now set `max_completion_tokens` explicitly, and Qwen is evaluated with reasoning
  off.
- **Infrastructure isn't a model failure.** One v2 case failed on a dropped connection; the
  rerun replayed the other 23 from their recordings and passed. Rate-limit responses (429) are
  waited out, not scored.
