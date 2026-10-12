"""Verify review provenance and derived counts, not Korean semantic judgments."""
import hashlib
import json
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rules-root', type=Path, help='Verify against an explicit historical source snapshot.')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = args.rules_root.resolve() if args.rules_root else here.parents[1]
    summary = json.loads((here / 'review-summary.json').read_text())
    rules_file = root / 'specification/rules.json'
    rule_hash = hashlib.sha256(rules_file.read_bytes()).hexdigest()
    assert summary['rules_sha256'] == rule_hash
    rule_ids = {row['id'] for row in json.loads(rules_file.read_text())['rules']}
    cases, reviews = {}, {}
    for source in summary['sources']:
        case_file = here / source['cases']
        review_file = here / source['review']
        assert hashlib.sha256(case_file.read_bytes()).hexdigest() == source['cases_sha256']
        assert hashlib.sha256(review_file.read_bytes()).hexdigest() == source['review_sha256']
        rows = json.loads(case_file.read_text())['cases']
        review = json.loads(review_file.read_text())
        assert review['cases_sha256'] == source['cases_sha256']
        assert review['rules_sha256'] == rule_hash
        assert len({row['id'] for row in rows}) == len(rows)
        assert len({row['case_id'] for row in review['reviews']}) == len(rows)
        assert {row['case_id'] for row in review['reviews']} == {row['id'] for row in rows}
        for row in rows:
            assert row['id'] not in cases
            cases[row['id']] = row
        for row in review['reviews']:
            assert row['verdict'] in ('pass', 'needs_revision')
            assert row['rule_ids'] and set(row['rule_ids']) <= rule_ids
            reviews[row['case_id']] = row
    matrix = {}
    for case_id, case in cases.items():
        family = matrix.setdefault(case['family'], {'normal': [], 'failure': [], 'keep': []})
        if reviews[case_id]['verdict'] == 'pass':
            family[case['case_type']].append(case_id)
    assert matrix == summary['family_triplets']
    passed = sum(row['verdict'] == 'pass' for row in reviews.values())
    excluded = [key for key, row in reviews.items() if row['verdict'] != 'pass']
    cells = sum(bool(ids) for family in matrix.values() for ids in family.values())
    assert len(cases) == summary['case_count']
    assert passed == summary['passed_cases']
    assert excluded == summary['needs_revision_cases']
    assert cells == summary['supported_minimum_cells']
    assert len(matrix) * 3 == summary['minimum_cells']
    print(json.dumps({'integrity': 'pass', 'cases': len(cases), 'review_passes': passed,
                      'excluded': excluded, 'minimum_triplet_cells': cells,
                      'semantic_judgments_repeated': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
