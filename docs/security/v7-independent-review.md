# Independent V7 security and release review

The review found no confirmed security regression in the inspected V7 diff, including the bounded engine 0.2.0 update. The earlier P3 archive-link defect is closed: `docs/spec/control-expression.md:5` and `docs/spec/korean-rules.md:41` now use explicit repository URLs for the adoption record, and the distribution tests pass. This confirms removal of missing relative archive destinations, not publication of those remote documents.

The review ran on 2026-10-15 against uncommitted changes above baseline `52008bdd1eabf0d5e3d359898bedcaebaf057e0a`. It inspected the updater cleanup, runtime activation/cache/trust paths, helper and launcher version changes, offline build allowlist, release workflow, canonical compiler publication binding, and TEST-signed migration driver. It made no production code changes and used only temporary installation/signing fixtures.

## Security conclusions

- `runtime/kproto.py:1248–1272` creates an exclusive per-attempt temporary stage. Its cleanup does not remove historical downloads, signed release caches, or backups. The local Python reports `shutil.rmtree.avoids_symlink_attacks == True`; tests verify that links inside a stage do not delete their external targets.
- Engine 0.2.0 raises the profile limit from 28 to 30 KiB and the managed-block limit from 30 to 32 KiB to retain reviewed rule meaning. It preserves the seven-path allowlist, per-file/total limits, signature namespace/principal, local key pin, release sequence high-water check, and explicit cached rollback requirement. `host_budget` still separately enforces the Codex project's configured chain limit, which defaults to 32 KiB, and the installer does not enlarge user configuration. The helper version bump does not change signed-install trust decisions.
- `make_manifest` now records engine minimum 0.2.0. The actual baseline engine 0.1.0 rejects this minimum before payload fetching and preserves the installed target and state. Upgrading its management code requires explicitly running the current repository installer; content updates do not replace executable code. The new signed content remains incompatible with an unupgraded 0.1.0 engine even when application is OFF.
- `validation/compile.py:27–40` rejects compact publication text after any change to its bound requirement, conditions, or exceptions. This is a consistency check for trusted authored content, not an independent semantic-equivalence proof. `distribution/release.py:76–122` still captures source, recompiles it, and requires exact compiled bytes before release preparation.
- The workflow changes only its default version. Its signing secret scope, pinned actions, separated publication permissions, and history gates remain unchanged. The new offline migration uses an ephemeral TEST signer and explicitly reports that it does not establish production publication or old-executable migration.

## Verification

The initial `python3 -B -m unittest tests.test_runtime tests.test_agent_install tests.test_release tests.test_actions_release tests.test_history_store tests.test_scheduler tests.test_launcher tests.test_distribution tests.test_candidate_upgrade_smoke tests.test_v7_adoption tests.test_controlled_language` run executed 304 tests in 47.131 seconds. It passed 303 tests and failed only the archive-link assertion subsequently repaired above. The duplicate-ZIP-name warning came from the archive-rejection fixture.

After the engine change and link repairs, `python3 -B -m unittest tests.test_runtime tests.test_agent_install tests.test_distribution tests.test_candidate_upgrade_smoke tests.test_v7_adoption tests.test_release` passed all 224 tests in 44.876 seconds. Boundary tests install complete profiles at 28 KiB + 1 byte and exactly 30 KiB, reject 30 KiB + 1 byte, and reject a larger profile when ancestor instructions leave insufficient Codex project-chain space while preserving child/ancestor instruction bytes and `config.toml`.

An independent disposable probe loaded the exact runtime source from baseline commit `52008bdd1eabf0d5e3d359898bedcaebaf057e0a`, installed a TEST-signed 0.3.0 fixture, and served a TEST-signed manifest for all seven actual V7 candidate files. The old runtime fetched only the manifest and signature, raised `CompatibilityError`, and retained byte-identical target and state files at 0.3.0. This probe did not merely change the current runtime's version constant.

`manual_offline_candidate_migration.run_migration(Path.cwd())` also passed against the exact seven baseline files from that commit. Both temporary Codex and Claude Code installations preserved OFF/honorifics, matched all seven candidate cache files, enabled the full candidate profile, rolled back to both cached versions, and restored user bytes on uninstall. Temporary material was removed. The historical TLS migration driver was inspected after its concurrent repair to expect the old engine's compatibility rejection; this independent follow-up did not execute that TLS driver.

Additional disposable probes confirmed that a symlink at the downloads root is rejected before fetching and preserves installed target/state bytes and the external directory. Separate mutations of each bound source field (`requirement`, `conditions`, `exceptions`) each caused compact publication validation to fail. `git diff --check` passed.

The final checked-in profiles measured 30,137, 30,107, and 30,116 bytes, respectively, beneath the new 30 KiB limit. The reviewed runtime SHA-256 was `fc564ee78ee483961d099e4b50453817aa16e2e3b7924244d8230360d74bb055`; the compiler SHA-256 was `ab378889030dcd007c226ce76ff44a340302d0bd23d472560486a44a261dc7b1`.

## Limits

This review did not run production signing, public publishing, live scheduler registration, or actual model invocations. It does not establish the semantic equivalence of compact rules; that is a separate language review. Cleanup after abrupt process termination remains outside the fix. A compromised local account or trusted publisher remains outside the reviewed trust boundary. The working tree was shared with concurrent integration work, so later edits require their relevant checks.
