# V7 adoption security audit

The review found and remediated one P3 availability issue and found no confirmed P0–P2 vulnerability in the inspected installer, updater, and release paths. This result does not certify arbitrary publisher content or a compromised local account as safe.

The source baseline is `52008bdd1eabf0d5e3d359898bedcaebaf057e0a`. The audit ran on 2026-10-15 and changed only the updater's transient-stage lifecycle, its regression tests, and this report. The audit did not change live agent instructions, credentials, LaunchAgents, or remote services. Concurrent V7 profile work was outside this runtime review.

## Remediated finding: P3 — update staging had no retention bound

The baseline `runtime/kproto.py:1248–1266` created `downloads/<uuid>` before every update and left it behind after successful updates, unchanged releases, and rejected manifests. The HTTPS endpoint could therefore retain unauthenticated response bytes on disk even when authentication correctly prevented activation. The per-request byte limit and scheduled retry backoff limited growth per attempt, but neither limited total retained bytes.

A disposable signed fixture produced these results:

| Reproduction condition | Observed result |
| --- | --- |
| Three explicit updates serving the identical valid signed release | Each returned `False`; three directories retained 27 files and 7,335 bytes. |
| Three further explicit updates serving a maximum-size invalid manifest and signature | Each failed; six total directories retained 33 files and 253,095 bytes. |
| Host instructions after all six attempts | The original installed bytes remained unchanged. |

The invalid-response growth was exactly 81,920 bytes per attempt: 65,536 manifest bytes plus 16,384 signature bytes. Scheduled failures back off to at most one attempt per 24 hours; explicit updates bypass that schedule. This finding concerns cumulative disk retention, not instruction injection, signature bypass, or execution of downloaded code.

The fix in `runtime/kproto.py:1248–1269` uses an exclusive `TemporaryDirectory` beneath the checked downloads path, so normal context exit cleans only the stage created by that attempt. It does not remove historical download directories, authenticated release caches, or backups. Abrupt process termination can still leave a stage behind; this change does not promise cleanup after `SIGKILL` or power loss.

Three regressions in `tests/test_runtime.py` first failed against the baseline and then passed after the fix. They cover successful activation, repeated unchanged releases, network failure, malformed manifests, invalid signatures, modified payloads, and filesystem errors. They also verify that an injected symlink inside a stage does not delete its external target, historical directories survive, host/state bytes survive failed updates, cached settings remain usable, and cached rollback still succeeds.

The reproduction used `tests.test_runtime.SignedRuntimeTests` to generate a temporary Ed25519 key, a signed seven-file content bundle, and a disposable host target. It called `install_signed`, configured `https://example.test`, and patched only `Controller.fetch` to serve those fixture bytes for three updates. It then patched `fetch` to return `b'x' * maximum` for three updates and counted regular files under `state/downloads`. No live endpoint or production key was used.

## Inspected controls and evidence

| Boundary | Source and verification evidence |
| --- | --- |
| HTTPS origin and redirects | `runtime/kproto.py:428–474,1168–1232` requires a credential-free HTTPS source on port 443, compares fetch origins, rejects redirects, and bounds downloaded bodies. Tests exercised real TLS through a local proxy, refused cross-origin redirects, and checked secret-free failure messages. |
| macOS proxy discovery and subprocess cleanup | `runtime/kproto.py:1192–1224` starts a fresh interpreter with `-I -B`, sends request data through stdin, discards worker diagnostics, applies the remaining deadline, and kills/reaps unfinished workers. Tests checked dynamic runtime loading, inherited proxy discovery, blocked readers, malformed input, and worker termination. |
| Content authentication and rollback | `runtime/kproto.py:779–843,987–1012,1132–1145` checks the local Ed25519 anchor, SSHSIG namespace/principal, file sizes/hashes, compatibility, and installed sequence high-water mark. Cached rollback rechecks content/signatures and pins the selected version. Tests rejected modified manifests, payloads, wrong namespaces, replayed sequences, and changed cached data. |
| Bootstrap anchor and durable helper | `distribution/agent_install.py:123–187,284–458` verifies recorded helper hashes/ownership, captures signed input, preserves an existing trust anchor, and refuses unsigned replacement of an existing signed installation. Tests covered concurrent anchor changes, unsigned downgrade attempts, altered helpers, and clone-independent management. |
| Paths and archives | `runtime/kproto.py:130–230` uses descriptor walks and `O_NOFOLLOW`, bounds regular-file reads, rejects hardlinked files, and checks parent/target identities before replacement. `distribution/actions_release.py:170–186` rejects archive traversal, duplicate paths, symlinks, oversized files, and oversized history. Targeted tests exercised those rejections and FIFO locks. |
| Host instructions and scheduler | `runtime/kproto.py:845–985,646–713,1288–1356` uses marker/hash ownership, preserves bytes outside the managed block, rechecks the selected host target, and requires an explicit signed scheduled installation for registration. Scheduler tests covered modified files, loaded-label collisions, unknown live identity, interrupted migration, and cleanup failure. |
| GitHub token redirects | `distribution/actions_release.py:57–89` handles the artifact-storage redirect separately without forwarding GitHub Authorization. `test_artifact_redirect_does_not_forward_github_authorization` exercised that behavior. |
| Signing secrets and workflow authority | `distribution/actions_release.py:249–267` writes the key into a private temporary directory, excludes its environment value from signer child processes, verifies its public identity, and captures signer diagnostics. `.github/workflows/release.yml` pins all referenced actions to full 40-character SHAs, disables checkout credential persistence, separates Pages write/OIDC authority from signing, and scopes the signing secret to the signing steps. Tests checked wrong-key rejection, temporary-key cleanup, rerun rejection, and publication-history continuity. |

## Validation and limits

Before the fix, `python3 -B -m unittest tests.test_runtime tests.test_agent_install tests.test_release tests.test_actions_release tests.test_history_store tests.test_scheduler tests.test_launcher` passed all 269 tests in 45.079 seconds. The duplicate-ZIP-name warning came from the archive rejection fixture. These passing tests supported the named controls but did not cover the staging-retention finding.

After the fix, the three new staging regressions passed in 0.444 seconds. `python3 -B -m unittest tests.test_runtime tests.test_scheduler` then passed all 157 tests in 15.671 seconds, and `git diff --check` reported no whitespace errors.

A broad rerun executed 272 tests in 43.729 seconds and reported four assertion failures and nine errors during concurrent V7 source migration. Nine errors and three assertion failures reported stale compiled `profiles/coding-agent.md`; the remaining assertion exercised a legacy-helper fixture with signed `0.3.0` after the installer version became `0.4.0`, which correctly triggered the downgrade guard. Those integration checks require compiled-profile regeneration and fixture alignment before the final adoption verdict.

A read-only pattern scan covered 1,526 tracked regular files and found no PEM private-key header, OpenAI-key-shaped token, GitHub-token-shaped token, or AWS-access-key-shaped token. The scan printed no matched values and cannot prove the absence of other credential formats or credentials in untracked files, Git history, external logs, or configured services.

The audit treated the installed Python runtime, the local account, the explicitly selected offline bundle, and the separately checked publisher key as trust anchors. Content signatures authenticate the seven content files, not the Python installer or helper code. The durable helper's self-recorded hashes detect accidental or partial modification; they do not protect against an attacker who can replace both code and its ownership metadata as the same local user.

The review did not invoke production signing, publishing, actual LaunchAgent registration, or live GitHub environment/branch-protection configuration. Scheduler mutation tests used fixtures/mocks. The configured repository environment's human approval rules, administrator access, GitHub action commit provenance, production key storage, and the content of future publisher-signed instructions require their owning operational checks.
