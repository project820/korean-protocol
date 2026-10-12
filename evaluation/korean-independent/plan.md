# Independent Korean normative evaluation plan

This suite contains exactly 24 newly authored fictional cases in eight families, with one normal, one failure, and one keep case per family.

The author used only the assignment and self-contained fictional source/context when creating the cases. The author did not read existing rule, example, or evaluation contents before freezing this suite. The author did not run a model, change rules, commit files, install dependencies, or test real readers.

The suite records normative judgments by a separate author. It provides no empirical reader evidence, real-world technical claims, or expert endorsement.

## The case contract fixes the evaluation question.

Each case supplies an explicit context, source, candidate, expected decision, one acceptable output, one rejected output, rationale, preserved facts, and prohibited changes. Context is part of the input; a reviewer must not silently replace it with a different context.

An accept decision means the different candidate preserves meaning within the stated context. A reject decision means the candidate introduces a concrete supported mismatch. A keep decision means the unchanged candidate preserves an already clear, natural source. Acceptable outputs are examples of valid responses, not exhaustive exact-string answer keys.

The cases treat shared-context omission, possibility, passive forms, Sino-Korean vocabulary, 하다 forms, polite requests, and quotations as legitimate where meaning and context support them. The permission case explicitly assigns discretion, so its rejection follows from converting that discretion into obligation. The causative case distinguishes the directing person from the actual performer. The negation case distinguishes not all from none. The conditions cases distinguish conjunction, simultaneity, and unsupported instructions for the opposite condition.

## The freeze makes later review independent.

Run `python3 validate.py --freeze` once from this directory after authoring. This command validates case schema and counts, then writes check.json with SHA256 digests for cases.json, plan.md, and validate.py. It refuses to replace an existing check.json.

Run `python3 validate.py --verify` before and after review. This command checks the same structural contract and compares all three files with the frozen digests. It does not rewrite the freeze record.

The author must not read existing rule/example/evaluation contents until the freeze exists. After the freeze, no author or reviewer may tune cases.json to the rules. A substantive case concern must go into a separate review artifact outside this owned directory and must preserve this original frozen version.

## The reviewer tests the latest integrated rules.

The parent must assign a separate reviewer to read the frozen suite and the latest integrated rules. The reviewer records the integrated rules path and revision or SHA256 before mapping, then maps each of the 24 case IDs to the actual rule IDs and relevant text. The reviewer must not use invented or stale rule IDs.

For each case, the reviewer records the rule-derived candidate decision, expected decision, matching or conflicting rule IDs, concrete source/context evidence, and a final status of covered, conflict, ambiguous, or no applicable rule. The reviewer evaluates whether keep cases stay concise without invented facts, and whether normal candidates remain eligible even when their grammatical form is optional.

The reviewer must distinguish a rule defect from a case defect and state evidence for either. The reviewer reports uncertainty in a separate artifact instead of changing the expected decision. Structural validation and frozen hashes do not establish semantic correctness or rule performance.

The parent receives the frozen cases and independent mapping for integration decisions. This assignment ends at 24 cases and adds no extra cases or rule implementation.
