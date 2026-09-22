# Acquisition guard closure — 2026-09-22 00:34 UTC

Reviewed exact `bddbdd3b28582b3498506996fc5f064f9f726430`, acquisition validator only. Immutable export: outer `work/acquisition0034/`. No network, benchmark data, sandbox, model, or reference execution.

**Close the two previously demonstrated acquisition defects on the default integrity-enabled path.** A shared pre-return validator now runs for both new acquisition and existing-manifest reuse. Required-source integrity is checked regardless of S1/EXT mode, and an explicit EXT requirement is enforced when reusing S1.

## Independent bounded witnesses

Created two tiny real temporary source files, one absent optional test source, and patched `lab_data.SOURCES` to their actual SHA-256 pins. Every call omitted `verify_required_bytes`, exercising its default **True** value. No assertion relied on an integrity bypass.

| Case | Observed result |
|---|---|
| Fresh S1 acquisition, both required files hash-correct | accepted S1 |
| Repeat acquisition with identical source bytes | accepted S1; original manifest bytes unchanged |
| Existing S1 manifest with explicit `expect_mode='EXT'` | refused by common mode validator |
| Existing S1 with corrupted required source | refused by required-byte validator |
| Existing S1 with missing required source | refused by required-byte validator |

These exercise the actual `acquire_sources` entry point and filesystem checks. The two prior counterexamples no longer return a usable acquisition. The valid repeat preserves original acquisition provenance rather than rewriting it because a cache origin changes.

## Scope and finite test cleanup

The delivered tests use `verify_required_bytes=False`, which does not exercise the integrity half of the repaired contract. That workaround is unnecessary: the tiny real-file/temporary-pin method above tests the real default path without downloading or embedding benchmark data. Replace those integrity-skipping fixture calls accordingly. The current source still exposes the bypass keyword; the comment “production never passes this” is a convention, not enforcement. Follow root's decision not to expose a production integrity opt-out rather than preserving one solely for tests.

This does not reopen the repaired default-path findings or require another dataset census. An explicit EXT request remains binding even if S2 is legitimately absent; intentionally choosing a distinct S1 study is a separate recorded design decision, not permission to drop EXT intent on a failed acquisition.

The nonce-handshake implementation and its reported failure are outside this narrow review and remain root-owned. No additional experiment, readiness credit, or execution authorization is granted here.
