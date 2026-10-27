"""Apply the paper's tier-gap rule to a user's own paired evaluation scores."""
import csv
import statistics
from collections import defaultdict

from core import reward


def select(path, tiers, tau=0.10):
    if set(tiers) != {'frontier', 'moderate', 'weak'} or any(not x for x in tiers.values()):
        raise ValueError('Provide nonempty frontier, moderate, and weak model tiers')
    models = [m for group in tiers.values() for m in group]
    if len(models) != len(set(models)):
        raise ValueError('Each model must belong to exactly one tier')
    observations = defaultdict(dict)
    with open(path, newline='') as stream:
        for row in csv.DictReader(stream):
            if row['condition'] not in ('no_skill', 'with_skill'):
                continue
            if row.get('status') and row['status'] != 'scored':
                raise ValueError('Screening requires scored trials; resolve missing cells explicitly')
            key = (row['benchmark'], row['task'], row['executor'], row['condition'])
            repeat = row.get('repeat', '0')
            if repeat in observations[key]:
                raise ValueError('Duplicate model/task/condition/repeat cell')
            observations[key][repeat] = reward(float(row['reward']))
    pairs, report = [], []
    for benchmark, task in sorted({k[:2] for k in observations}):
        scores = {}
        missing = []
        for model in models:
            left = observations.get((benchmark, task, model, 'no_skill'), {})
            right = observations.get((benchmark, task, model, 'with_skill'), {})
            if not left or set(left) != set(right):
                missing.append(model)
            else:
                scores[model] = (statistics.mean(left.values()), statistics.mean(right.values()))
        if missing:
            raise ValueError(f'Incomplete paired screening cells: {benchmark}/{task}: {missing}')
        stats = {}
        for tier, members in tiers.items():
            base = statistics.mean(scores[m][0] for m in members)
            with_skill = statistics.mean(scores[m][1] for m in members)
            stats[tier] = {'base': base, 'with_skill': with_skill, 'gain': with_skill - base}
        weak = stats['weak']['gain']
        def benefits(tier):
            gain = stats[tier]['gain']
            return gain + 1e-12 >= tau and gain - weak + 1e-12 >= tau
        chosen = (benefits('frontier') or (stats['frontier']['base'] >= 0.95 and benefits('moderate')))
        chosen = chosen and stats['weak']['with_skill'] < 0.80
        pair = {'benchmark': benchmark, 'task': task}
        if chosen:
            pairs.append(pair)
        report.append({**pair, 'selected': chosen, 'tiers': stats})
    return {'schema_version': 1, 'tau': tau, 'pairs': pairs}, report
