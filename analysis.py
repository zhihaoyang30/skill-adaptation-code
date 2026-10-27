"""Summarize only the user's local results, with task-paired control differences."""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

from core import read_json, write_json


def summarize(root, out):
    groups = defaultdict(dict)
    for path in Path(root).rglob('history.json'):
        for row in read_json(path):
            if row['status'] != 'scored' or row['reward'] is None:
                continue
            key = (row['benchmark'], row['executor'], row['mode'], row['arm'], row['round'])
            if row['task'] in groups[key]:
                raise ValueError('Duplicate task cells; summarize each run separately')
            groups[key][row['task']] = row['reward']
    rows = []
    for key, values in sorted(groups.items()):
        benchmark, executor, mode, arm, number = key
        original = groups.get((benchmark, executor, mode, 'original', number), {})
        common = sorted(values.keys() & original.keys())
        rows.append({'benchmark': benchmark, 'executor': executor, 'mode': mode,
                     'arm': arm, 'round': number, 'n': len(values),
                     'mean_reward': statistics.mean(values.values()), 'paired_n': len(common),
                     'paired_gain': statistics.mean(values[t] - original[t] for t in common) if common else None,
                     'unpaired_n': len(values) - len(common)})
    if not rows:
        raise ValueError('No scored pipeline histories found')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / 'summary.json', rows)
    with (out / 'summary.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows
