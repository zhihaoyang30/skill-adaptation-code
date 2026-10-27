"""Protocol tests use tiny temporary fixtures, not benchmark data or model calls."""
import csv
from pathlib import Path
from unittest.mock import patch

import pytest

from core import contained, reward
from evolution.rewrite import apply, parse
from harnesses.tessl import normalize_checklist, score_verdict, workspace_evidence
from screening.select_pairs import select


@pytest.fixture
def bundle(tmp_path):
    path = tmp_path / 'bundle' / 'example'
    path.mkdir(parents=True)
    (path / 'SKILL.md').write_text('---\nname: example\ndescription: Example skill\n---\nOriginal guidance.\n')
    (path / 'helper.py').write_text('print(1)\n')
    return path.parent


def block(name, body):
    return f'<<<FILE path={name}>>>\n{body}\n<<<END>>>'


def test_rewrite_is_transactional_and_blocks_path_escape(bundle, tmp_path):
    original = (bundle / 'example/SKILL.md').read_text()
    reply = block('example/SKILL.md', original.replace('Original', 'Improved')) + '\n' + block('../outside.txt', 'bad')
    result = apply(reply, bundle, tmp_path / 'out', (set(), set()), '')
    assert result['status'] == 'rejected'
    assert (tmp_path / 'out/example/SKILL.md').read_text() == original
    assert not (tmp_path / 'outside.txt').exists()


def test_hidden_numbers_blocked_but_visible_feedback_allowed(bundle, tmp_path):
    original = (bundle / 'example/SKILL.md').read_text()
    text = original + '\nValue: 912.345\n'
    reply = block('example/SKILL.md', text)
    hidden = ({'912.345'}, set())
    assert apply(reply, bundle, tmp_path / 'bad', hidden, '')['status'] == 'rejected'
    assert apply(reply, bundle, tmp_path / 'visible', hidden, '912.345')['status'] == 'accepted'


def test_rewrite_keeps_helpers_and_name(bundle, tmp_path):
    original = (bundle / 'example/SKILL.md').read_text()
    result = apply(block('example/SKILL.md', original.replace('Original', 'Improved')), bundle, tmp_path / 'ok', (set(), set()), '')
    assert result['changed']
    assert (tmp_path / 'ok/example/helper.py').read_text() == 'print(1)\n'
    renamed = block('example/SKILL.md', original.replace('name: example', 'name: renamed'))
    assert apply(renamed, bundle, tmp_path / 'renamed', (set(), set()), '')['status'] == 'rejected'


def test_malformed_or_duplicate_output_is_not_silently_accepted():
    for response in ('some prose', '<<<NO_CHANGE>>>', block('a', 'x') + block('a', 'y')):
        with pytest.raises(ValueError):
            parse(response)
    assert parse('<<<NO_CHANGE>>>\n{"reason":"no grounded change"}\n<<<END_NO_CHANGE>>>') == {}


def test_contained_rejects_symlinks_and_absolute_paths(tmp_path):
    (tmp_path / 'link').symlink_to('/tmp')
    for path in ('../a', '/tmp/a', 'link/a'):
        with pytest.raises(ValueError):
            contained(tmp_path, path)


def test_tessl_judge_requires_exact_bounded_coverage():
    items = normalize_checklist({'checklist': [{'id': 'a', 'max_score': 2}, {'name': 'b', 'max_score': 1}]})
    good = {'scores': [{'name': 'a', 'score': 1}, {'name': 'b', 'score': 1}]}
    assert score_verdict(items, good)[0] == pytest.approx(2/3)
    for bad in (
        {'scores': [good['scores'][0]]},
        {'scores': good['scores'] + [good['scores'][0]]},
        {'scores': [{'name': 'a', 'score': -1}, {'name': 'b', 'score': 1}]},
        {'scores': [{'name': 'a', 'score': float('nan')}, {'name': 'b', 'score': 1}]},
        {'scores': [{'name': 'a', 'score': 5}, {'name': 'b', 'score': 1}]},
    ):
        with pytest.raises(ValueError):
            score_verdict(items, bad)


def test_tessl_same_size_edits_are_evidence(tmp_path):
    originals, ws = tmp_path / 'inputs', tmp_path / 'workspace'
    originals.mkdir()
    (ws / 'inputs').mkdir(parents=True)
    (originals / 'a.txt').write_text('before')
    (ws / 'inputs/a.txt').write_text('after!')
    _, bodies = workspace_evidence(ws, originals)
    assert 'after!' in bodies


def test_tessl_distinguishes_semantic_symbols_in_rubric_names():
    items = normalize_checklist({'checklist': [{'name': 'pass@k defined', 'max_score': 1},
                                               {'name': 'pass^k defined', 'max_score': 1}]})
    value, _ = score_verdict(items, {'scores': [{'name': 'pass@k defined', 'score': 1},
                                               {'name': 'pass^k defined', 'score': 0}]})
    assert value == 0.5


def scores(path, extra=False):
    fields = ['benchmark', 'task', 'executor', 'condition', 'repeat', 'reward', 'status']
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for m, pair in {'f': (0.0, 0.8), 'm': (0.0, 0.4), 'w': (0.0, 0.0)}.items():
            for repeat in range(2):
                for condition, value in zip(('no_skill','with_skill'), pair):
                    writer.writerow(dict(benchmark='example', task='task', executor=m, condition=condition,
                                         repeat=repeat, reward=value, status='scored'))
        if extra:
            writer.writerow(dict(benchmark='example', task='task', executor='f', condition='no_skill', repeat=2, reward=1, status='scored'))


def test_screening_averages_repeats_and_checks_pairs(tmp_path):
    p = tmp_path / 'scores.csv'
    tiers = {'frontier':['f'], 'moderate':['m'], 'weak':['w']}
    scores(p)
    selected, _ = select(p, tiers)
    assert selected['pairs'] == [{'benchmark':'example','task':'task'}]
    scores(p, extra=True)
    with pytest.raises(ValueError, match='Incomplete'):
        select(p, tiers)


def test_nonfinite_rewards_rejected():
    for value in (None, True, float('nan'), float('inf'), -0.1, 1.1):
        with pytest.raises(ValueError):
            reward(value)


def test_one_shot_runs_rewrites_before_any_rollout(bundle, tmp_path):
    from evolution.pipeline import run
    calls = []
    def fake_rewrite(config, task, benchmark, rewriter, arm, source, target, last_trial=None):
        import shutil
        assert last_trial is None
        calls.append('rewrite')
        shutil.copytree(source, target)
    def fake_trial(config, pair, executor, out, skill_bundle=None, no_skill=False):
        calls.append('run')
        Path(out).mkdir(parents=True)
        return {'reward':0.5, 'status':'scored', **pair, 'executor':executor}
    with patch('evolution.pipeline.resolve', return_value=tmp_path), patch('evolution.pipeline.skills', return_value=bundle), \
         patch('evolution.pipeline.rewrite', side_effect=fake_rewrite), patch('evolution.pipeline.run_trial', side_effect=fake_trial):
        history = run({}, {'benchmark':'example','task':'task'}, 'executor', tmp_path / 'pipeline', 'adapt', ['meta','no_meta'], rewriter='strong')
    assert calls == ['rewrite','rewrite','run','run','run']
    assert len(history) == 3


def test_evolution_uses_previous_bundle_and_self_model_even_after_zero(bundle, tmp_path):
    from evolution.pipeline import run
    edits = []
    def fake_rewrite(config, task, benchmark, rewriter, arm, source, target, last_trial=None):
        import shutil
        assert rewriter == 'executor'
        assert last_trial[1] == 0
        old = (source / 'example/SKILL.md').read_text()
        edits.append(old.count('EDIT'))
        shutil.copytree(source, target)
        (target / 'example/SKILL.md').write_text(old + 'EDIT\n')
    def fake_trial(config, pair, executor, out, skill_bundle=None, no_skill=False):
        Path(out).mkdir(parents=True)
        return {'reward':0.0, 'status':'scored', **pair, 'executor':executor}
    with patch('evolution.pipeline.resolve', return_value=tmp_path), patch('evolution.pipeline.skills', return_value=bundle), \
         patch('evolution.pipeline.rewrite', side_effect=fake_rewrite), patch('evolution.pipeline.run_trial', side_effect=fake_trial):
        history = run({}, {'benchmark':'example','task':'task'}, 'executor', tmp_path / 'pipeline', 'evolve', ['meta'], rounds=2)
    assert edits == [0,1]
    assert len(history) == 6
    assert [r['round'] for r in history if r['arm'] == 'original'] == [0,1,2]
