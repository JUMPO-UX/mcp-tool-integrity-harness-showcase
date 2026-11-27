# MCP tool integrity: archived-package selection and post-approval rug pull

Conceptual overview of the MCP module of the private prototype. The full module, its
package indicators, its fixture catalog and its tests are not published here.

## 1. Archived / deprecated MCP package chosen by an agent ("MCPhantom")

Glow Labs described this pattern publicly on 2 November 2026
([blog post](https://www.glow.io/blogs/mcphantom-ai-coding-agents-are-installing-vulnerable-deprecated-mcp-servers-from-training-data)):
a coding agent picks an MCP server that is already archived or deprecated
because the name is in its training data, then installs it with `npx`.

The prototype did **not** reproduce their session study, their download
counts, or the vulnerability they cite. Those figures are Glow's claims, not
measurements made by this project. The archived package names are used only
as detection indicators.

How the prototype handles it:

- an `npx` invocation is classified `info`, `medium` or `high`;
- `high` (and the command is not run) requires both an agent actor and a
  listed archived package;
- a human running `npx` on a maintained package stays at `info`.

## 2. Tool metadata changes after human approval (rug pull)

A different problem, not described as such in the Glow post: a tool's
description or schema changes **after** a human approved it, for example by
adding an exfiltration instruction.

### Approval is a digest, not a flag

Before hashing (see the excerpt [`excerpts/mcp_integrity/bind.py`](../excerpts/mcp_integrity/bind.py)):
NFKC normalisation, removal of Unicode format characters, folding of common
homoglyphs, sorted schema keys. A zero-width character or a Cyrillic `е` that
looks like `e` does not create a second approval. One extra visible word
changes the digest.

Every invocation re-reads the current metadata. There is no window where an
"approved" boolean survives a description swap. After a drift, the binding is
removed; the old shape does not pass again either. Only an explicit new
approval binds the new shape.

## Detection rules (Sigma-style)

| Rule | Level | Fires when | Published here |
|---|---|---|---|
| npx telemetry | informational | process image is `npx` | yes, [`detections/mcp_npx_install_telemetry.yml`](../detections/mcp_npx_install_telemetry.yml) |
| archived package installed by an agent | high | `npx` AND an agent parent process AND a listed archived package | no (private) |
| tool metadata drift | high | harness log line `kind=tool_metadata_drift` | no (private) |

Prerequisites: `CommandLine` and `ParentImage` (or an equivalent field) for the
process rules. Without the parent, a rule reduced to "`npx`" must not be raised
above informational. **These rules are not wired to any EDR or SIEM.** They are
evaluated only by the prototype's unit tests.

## Limits

- The agent actor label is supplied by the caller. Without it or without
  `ParentImage`, an `npx` of an archived package is a `medium` review, not a
  high alert.
- The Glow list may be incomplete or may have changed since 2 November 2026.
- Not covered: remote MCP servers, an already-running binary, a deployed EDR,
  and real MCP clients (tool specs are built from a local fixture catalog).
