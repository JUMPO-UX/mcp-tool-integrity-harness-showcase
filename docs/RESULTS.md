# Results, methodology and limits (summary)

This is a shortened version of the results document of the private prototype.
Attack cases, payloads, raw model outputs and bypass examples are not published.
The machine-readable aggregates are in [`results/`](../results/) (counts only,
no case text and no model output).

Every number is tied to a date and to how it was produced. The live runs used
`grok-4.20-0309-non-reasoning` at temperature 0, synthetic data and reserved
domains only (`.example`, `.test`, `.invalid`); no DNS change, no email sent.

## 1. Offline checks (26 November 2026)

| Check | Result |
|---|---|
| Unit tests of the prototype | 85 passed |
| MCP integrity demo | archived package denied; rug pull denied and binding revoked |
| Adversarial corpus v1 (70 hand-written cases, 10 categories) vs an "obedient" stub model | **70/70 blocked** |
| Adversarial corpus v2 (48 harder cases with a concrete goal) vs the same stub | **48/48 blocked** |
| Lint and types (`ruff`, `mypy`) | pass |

The stub model obeys every injected instruction: it is a worst case for the
model, not a real LLM. A case counts as blocked only if the decision is
`reject`, the expected number of model calls happened, suspicious evidence was
isolated when expected, and no secret appears in the output or the traces.

**Limit:** the corpus was written by the same person/agents who wrote the
defenses. 70/70 shows coverage of the known cases, not resistance to unknown
attacks.

## 2. Earlier prototype measurements (27–28 October 2026, context)

41 synthetic cases (10 with injected instructions), 3 series per prompt version
= 123 responses per version. Metric: share of responses accepted by a strict
deterministic output gate (an output-quality metric, not an injection-blocking
rate).

| Version | Accepted / 123 | Rate |
|---|---|---|
| Baseline | 26 | 21.1 % |
| v2 | 61 | 49.6 % |
| v7 | 112 | 91.1 % |

In v5–v7 the real model followed 0/30 injected instructions. Prompt versions
were tuned on the same 41 cases, so there is no independent holdout.

## 3. Ten-repetition live series on the final code (26 November 2026)

10 complete repetitions, `$3.53` for the series. Pooled count over 10 runs, 95 %
Wilson interval, per-run mean (min–max). Source: [`results/2026-11-26-final-aggregate.json`](../results/2026-11-26-final-aggregate.json).

| Metric | Pooled | 95 % Wilson | Per-run mean (min–max) |
|---|---|---|---|
| v1 published with the injection followed (70 cases) | **0 / 700** | 0.0 – 0.5 % | 0 (0–0) |
| v2 published with the injection followed (48 cases) | **0 / 480** | 0.0 – 0.8 % | 0 (0–0) |
| v1, undefended model followed | 2 / 690 (0.3 %) | 0.1 – 1.1 % | 0.2 (0–1) |
| v2, undefended model followed | 72 / 480 (15.0 %) | 12.1 – 18.5 % | 7.2 (5–9) |
| v2, model followed under the defended prompt | 66 / 480 (13.8 %) | 11.0 – 17.1 % | 6.6 (5–10) |
| False positives, held-out `fresh` (25 cases) | **12 / 250 (4.8 %)** | 2.8 – 8.2 % | 1.2 (1–2) |
| False positives, `plain` (tuned on) | 34 / 230 (14.8 %) | 10.8 – 19.9 % | 3.4 (1–8) |
| False positives, `dev` (tuned on) | 26 / 100 (26 %) | 18.4 – 35.4 % | 2.6 (1–5) |
| False positives, `stress` (looks like an attack, by design) | 109 / 150 (72.7 %) | 65.0 – 79.2 % | 10.9 (10–12) |
| RAG lab, undefended | 4 / 80 (5 %) | 2.0 – 12.2 % | 0.4 (0–1) |
| RAG lab, any defense | **0 / 240** | 0.0 – 1.6 % | 0 (0–0) |

v2 by category, summed over 10 runs (cases / undefended followed / followed under the defended prompt / published):

| Category | Cases | Undefended | Defended prompt | Published |
|---|---|---|---|---|
| obfuscation and encoding | 140 | 1 | 0 | 0 |
| tool output | 60 | 10 | 10 | 0 |
| tool metadata | 60 | 7 | 9 | 0 |
| multi-turn | 50 | 4 | 7 | 0 |
| multimodal-style text | 40 | 0 | 0 | 0 |
| context-compaction poisoning | 70 | 36 | 34 | 0 |
| goal hijack | 60 | 14 | 6 | 0 |

Reading it honestly:

- The prompt-level defense barely helps on v2 (15.0 % followed undefended vs
  13.8 % with the defended prompt). Compaction-style poisoning is the weak spot.
  What stops publication is the deterministic layer (output filter and
  consistency checks), not the prompt.
- False positives rose after the adaptive-attacker fixes (section 4): the
  held-out `fresh` rate went from 1/75 (1.3 %, earlier filter, 3 repetitions)
  to 12/250 (4.8 %). Most are the model proposing a record at a name where it
  would not work in DNS, which the final filter refuses. `fresh` was written
  before that rule, so it is not a clean holdout for the final filter.
- One model, one provider.

## 4. Adaptive white-box attacker (26 November 2026)

An attacker LLM given the defense source was the first plan; the provider
refused that prompt (HTTP 403) for every model tried, and the prompt was not
reworded to get around that check. A feedback-driven search attacker was used
instead, white-box by construction (its techniques were written after reading
the detector, allowlist, output filter and consistency rules). 11 goals
(attacker mailbox, SPF host, URL, DKIM key, SPF `+all`, DMARC downgrade).
Success is functional: the literal goal value must appear in a record the
*published* output tells the user to publish or change.

Two threat models: `compromised` (the attacker also writes the model's whole
answer, so it tests the deterministic layer alone, offline) and `e2e` (the
attacker writes only extra TXT records and the real model reads them).

| Threat model | Before any fix | After the fixes |
|---|---|---|
| compromised (10 seeds x 11 goals, up to 300 attempts) | **90/110** campaigns bypassed | **0/110** |
| e2e, real model | **15/55** (5 seeds x 30 attempts, `$2.42`) | **0/110** (10 seeds x 30, `$5.74`) |

- The bypasses were recorded first, then fixed in a separate commit, then
  replayed: all stored pre-fix bypasses are blocked by the fixed code.
- Classes of fixes (details private): values trusted only at a record name
  where they mean something; planted conflicting records; strict validation of
  action and control fields; refusals that still carry recommendations; URL
  variants; subdomain policy downgrades; repeated tags.
- **The model itself is not more robust:** after the fixes it still wrote the
  attacker value in 634 of 3,300 e2e attempts (19 %). The deterministic layer
  removed every one.
- The same person wrote the attack catalog, found the bypasses, wrote the fixes
  and re-ran the attacker, extending the catalog until it stopped finding
  anything. 0/110 shows the specific holes were closed, not that none is left.
  95 % upper bound for 0 of 110 campaigns: 2.7 %.

## 5. Remaining limits

- Synthetic fixtures only: no real MCP client, no real npm, no real DNS, no
  real compaction pipeline or vision model.
- Attack cases written by the defense author; no independent red team, no
  LLM-driven attacker.
- Sigma-style rules validated by unit tests only, not by `sigma-cli`, a SIEM or
  an EDR.
