# mcp-tool-integrity-harness (showcase)

Test-driven defenses for two AI-agent risks:

1. **MCP tool integrity**: an agent installing an archived/deprecated MCP
   server, and a tool whose metadata changes after a human approved it
   ("rug pull").
2. **Indirect prompt injection**: untrusted evidence (here, DNS TXT records)
   that tries to hijack a model, leak secrets or exfiltrate data.

Plus a hands-on lab on indirect prompt injection in a RAG pipeline.

> **Portfolio extracted from a larger private prototype; full code available on
> request for evaluation.** This repository shows the problem, the threat model,
> the architecture, aggregated results and a few short code excerpts. The
> defense engine, attack corpora, payloads, tests, evaluation scripts and lab
> solutions are kept private. It is **not** a product, has **not** been
> deployed, and the detection rules are **not** connected to any EDR or SIEM.

## Problem

Coding and ops agents now pick tools and read untrusted content on their own.
Two failure modes are cheap to trigger and easy to miss:

- **Tool supply chain.** Glow Labs [reported on 2 November 2026](https://www.glow.io/blogs/mcphantom-ai-coding-agents-are-installing-vulnerable-deprecated-mcp-servers-from-training-data)
  that coding agents install archived `@modelcontextprotocol/server-*`
  packages remembered from training data. Separately, an MCP tool approved
  once can change its description later; if approval is a boolean, the new
  (malicious) description inherits it.
- **Indirect prompt injection.** Text fetched by the agent (a TXT record, a
  document, a web page) contains instructions. If the model follows them, it
  can publish attacker-controlled values, echo instructions or leak keys.

## Threat model

| | In scope | Out of scope |
|---|---|---|
| Attacker | Controls content the agent reads (TXT records, documents); controls an MCP tool's metadata after approval; relies on the agent recalling an archived package name | Compromised host, compromised model provider, malicious human operator |
| Assets | API keys in the environment, integrity of the advice/output (no attacker mailbox, host, URL or DKIM key published; no weakened SPF/DMARC), which tools the agent may call | Availability, model weights, confidentiality of the evidence itself |
| Assumptions | The caller labels `actor=agent` vs `human`; process telemetry has `CommandLine` and `ParentImage` | Real MCP client wiring, remote MCP servers, already-running binaries |

Adaptive attacker (RESULTS section 4), as modelled:

- **White-box:** knows the defense design and code (detector keywords, allowlist, filter rules).
- **Controls:** up to 4 extra TXT records with attacker-chosen names and values, and any text in them. In the
  `compromised` model it also controls the advisory model's whole answer (a hijacked model); in `e2e` it does not.
- **Feedback:** sees the detector markers, the decision, the filter reasons and the published output of each try.
- **Budget:** fixed iteration cap per goal (30 live, 300 offline), repeated over 10 seeds, spend capped in a ledger.
- **Goal:** a dangerous literal value in a published record whose action is not `remove`.
- **Not modelled:** an LLM attacker (the provider refused the red-team prompt, see RESULTS section 4), attackers who
  can change the DNS zone itself, attacks on the human who reads the advice, other models or providers' safety
  layers, a real MCP client, side channels.

## Architecture

```text
mcp_integrity/            MCP supply-chain and rug-pull checks
  install                 classify an npx invocation: info / medium / high (deny)
  indicators              archived package list (Glow Labs names + synthetic fixture)
  bind                    canonical tool digest (NFKC, format chars removed, homoglyphs folded, sorted keys)
  approval                approval ledger: digest-bound, re-checked on every invoke, revoked on drift
security/                 prompt-injection defense around one model call
  normalize               Unicode normalisation and trick detection
  detect                  injection markers
  delimit                 evidence block with a non-forgeable end delimiter
  pipeline                defend(): validate -> budget -> isolate -> call at most once -> filter
  output_filter           reject output that is not grounded in the evidence
  allowlist               URLs/emails/DKIM keys allowed only if present in evidence
  semantics               consistency checks of the advice against the evidence
  redact, budget          secret masking in traces; call and cost ceilings
live/                     opt-in real-model runner with a spend cap, judge, offline replay, adaptive attacker
detections/               4 Sigma-style rules (not deployed anywhere)
lab01-rag-injection/      standalone RAG injection lab (in French), stdlib only
```

The design rule is **"the model proposes, deterministic code decides"**:
nothing the model returns is published unless every value can be traced back
to the observed evidence, and approval of a tool is a cryptographic digest of
its normalised metadata, not a flag.

More detail: [`docs/MCP-INTEGRITY.md`](docs/MCP-INTEGRITY.md).

## What is in this repository

| Path | Content |
|---|---|
| `docs/MCP-INTEGRITY.md` | MCP integrity design (conceptual) |
| `docs/RESULTS.md` | Methodology, aggregated results and limits |
| `results/` | Machine-readable aggregates of the live runs (counts only, no case text, no model output) |
| `excerpts/mcp_integrity/bind.py` | Canonical tool digest used for digest-bound approval |
| `excerpts/security/redact.py` | Secret masking in traces |
| `detections/mcp_npx_install_telemetry.yml` | One Sigma-style rule (informational) |

The excerpts are not runnable on their own: they import private modules.

## Running it

The engine, tests and evaluation scripts are private, so there is nothing to
run here. The private repository runs, offline and without any API key: the
unit tests, the MCP integrity demo, the RAG lab solutions, the adaptive attacker
in the compromised-model threat model and an offline replay of the stored live
outputs. The real-model runner is opt-in, reads its API key from the environment
only and refuses to spend above a hard cap. A walkthrough or read access can be
arranged on request for evaluation.

## Results (with limits)

Methodology and caveats: [`docs/RESULTS.md`](docs/RESULTS.md). Numbers are dated and tied to how they
were produced.

Offline, in the private repository (26 Nov 2026): **85 tests pass**. The deterministic layer blocks 70/70 (v1) and 48/48 (v2)
cases against a deliberately *obedient* stub model. That shows coverage of the cases written next to the
defenses, not robustness to unknown attacks.

Live, 26 Nov 2026, `grok-4.20-0309-non-reasoning`, temperature 0, **10 repetitions** on the final code
(after the adaptive-attacker fixes; `$3.53` for this series, `$11.74` for all 26 Nov adaptive work;
[details](docs/RESULTS.md#3-ten-repetition-live-series-on-the-final-code-26-november-2026)):

| | Result (pooled over 10 runs, 95 % Wilson, per-run mean and min–max) |
|---|---|
| Attacks, v1 (70 generic cases x 10) | undefended followed 2/690; **0/700 published** (upper bound 0.5 %) |
| Attacks, v2 (48 concrete cases x 10) | undefended followed **72/480 (15 %)**; defended prompt 66/480 (14 %); **0/480 published** (upper bound 0.8 %) |
| False positives, `fresh` benign set (25 x 10) | **12/250 (4.8 %)**, interval 2.8–8.2 %, mean 1.2 (1–2) per run. Not a clean holdout for the final name-mismatch rule (see below) |
| False positives, `stress` (15 x 10) | 109/150 (73 %): by design the detector isolates it and only a refusal is published |
| RAG lab, undefended | 4/80 compromised (real model) vs 5/8 (simulator); **0/240** with any defense |

Adaptive white-box attacker, same day ([RESULTS section 4](docs/RESULTS.md#4-adaptive-white-box-attacker-26-november-2026)):

| Threat model | Before any fix | After the fixes (attacker catalog extended) |
|---|---|---|
| compromised (10 seeds x 11 goals, up to 300 attempts, offline) | **90/110** campaigns bypassed | **0/110** |
| e2e, real model | **15/55** (5 seeds x 30 attempts, `$2.42`) | **0/110** (10 seeds x 30, `$5.74`) |

What these numbers do **not** say:

- The prompt-level defense barely helps on v2 (15 % followed undefended vs 14 % with delimiting). The output
  filter and the consistency layer stop publication. The keyword detector flags only 19 % of v2 cases.
- 0 published on the written corpus is not the same as 0 against an adaptive attacker. Before the fixes the
  attacker published a dangerous value in 15 of 55 live campaigns (mailbox and SPF-host goals). Those holes
  were recorded first, then fixed, then replayed; the after-fix 0/110 is on a catalog I wrote and extended
  until it stopped finding anything.
- False positives rose after those fixes. An earlier 3-repetition series, on the filter before the fixes, had a held-out
  `fresh` rate of 1/75 (1.3 %). On the final code it is 12/250 (4.8 %), mostly `record_name_mismatch` (the
  model proposing a DMARC record at the apex, which would not work in DNS). `fresh` was written before that
  rule, so it is not a clean holdout for the final filter. `dev` and `plain` were already tuned on.
- v2 simulates tool output, tool metadata, summaries and image captions as TXT evidence. It does not test a
  real MCP client, compaction pipeline or vision model.
- A published answer can keep the other recommendations when one is dropped (clean evidence only).
- One model, one provider. A second target was budgeted and not run in this series.

Context from the private prototype (not reproducible here, the agent and gate are not included): on 27-28 Oct
2026, with a real model and 123 responses per prompt version, the share of responses accepted by the strict
output gate went from 26/123 (baseline) to 61/123 (v2) and 112/123 (v7). In v5-v7 the real model followed 0/30
injected instructions. Synthetic cases only, one model, no independent holdout.

## Limits

- Synthetic fixtures only; no real MCP client, no real npm, no real DNS.
- Sigma-style rules are validated by unit tests only, not by `sigma-cli`,
  a SIEM or an EDR.
- `actor=agent` must be provided by the caller; without `ParentImage` the
  archived-package rule cannot reach `high`.
- Homoglyph folding covers common confusables, not the full Unicode table.
- Code, tests, messages and docs are in English. Lab 01 and a few multilingual
  attack payloads are in French on purpose.
- Built largely by AI coding agents (design, code, tests and the live runs) under the
  author's direction, and not reviewed by an independent third party. The live numbers
  come from stored outputs kept in the private repository.

## Roadmap

- [ ] Measure a second model and a larger held-out benign set written after the final filter.
- [ ] Attack cases written by someone other than the defense author, and an LLM-driven attacker.
- [ ] Test with a real MCP client and a real compaction step instead of TXT-embedded simulations.
- [ ] Validate the rules with `sigma-cli` / pySigma and convert one to SPL or KQL.
- [ ] Wire the approval ledger into a real MCP client (stdio) behind a feature flag.
- [ ] Lab 02: tool poisoning through MCP tool descriptions.

## License

Copyright (c) 2026 JUMPO-UX. All rights reserved. See [LICENSE](LICENSE).
Shown for reading and evaluation only; no reuse without written permission.
