import json

import pytest

from core import ROOT, read_json
from data_index import pairs
from tools.package import collect, validate_indexes


def test_selected_is_subset_with_matching_references():
    screening = {(p['benchmark'], p['task']): p for p in pairs({}, 'screening')}
    selected = {(p['benchmark'], p['task']): p for p in pairs({}, 'selected')}
    assert len(screening) == 607
    assert len(selected) == 103
    assert selected.keys() < screening.keys()
    assert all(screening[key] == row for key, row in selected.items())


@pytest.mark.parametrize('problem, expected', [
    ('count', 'must contain'),
    ('duplicate', 'duplicate identities'),
    ('outside', 'must be a subset'),
    ('references', 'references must match'),
])
def test_packager_rejects_invalid_indexes(problem, expected):
    payload = collect()
    selected = json.loads(payload['data/selected.json'])
    rows = selected['pairs']
    if problem == 'count':
        rows.pop()
    elif problem == 'duplicate':
        rows[0] = rows[1]
    elif problem == 'outside':
        rows[0]['task'] = 'outside-the-screening-index'
    else:
        rows[0]['skill_paths'] = ['a/different/skill']
    payload['data/selected.json'] = json.dumps(selected).encode()
    with pytest.raises(ValueError, match=expected):
        validate_indexes(payload)


def test_release_allowlist_has_no_runtime_data():
    payload = collect()
    assert all(not name.startswith(('runs/', 'data/upstream/')) for name in payload)
    assert '.env' not in payload and 'configs/local.json' not in payload
    for name in ('screening', 'selected'):
        for row in read_json(ROOT / f'data/{name}.json')['pairs']:
            assert set(row) == {'benchmark', 'task', 'path', 'skills', 'skill_paths'}
            assert len(row['skills']) == len(row['skill_paths'])
