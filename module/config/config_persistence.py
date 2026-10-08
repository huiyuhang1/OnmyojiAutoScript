import copy
import json

from filelock import FileLock

from module.config.atomicwrites import atomic_write


def merge_changes(previous, current, latest):
    """Apply this writer's changed fields to the latest saved configuration."""
    result = copy.deepcopy(latest)
    for key, value in current.items():
        if key not in previous or key not in latest:
            result[key] = copy.deepcopy(value)
        elif isinstance(value, dict) and isinstance(previous[key], dict) and isinstance(latest[key], dict):
            result[key] = merge_changes(previous[key], value, latest[key])
        elif value != previous[key]:
            result[key] = copy.deepcopy(value)
    return result


def save_changes(filepath, previous, current):
    # Use the same lock as read_file/write_file for the entire read/merge/write.
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(f'{filepath}.lock'):
        latest = json.loads(filepath.read_text(encoding='utf-8')) if filepath.exists() else {}
        merged = merge_changes(previous, current, latest)
        with atomic_write(str(filepath), overwrite=True, encoding='utf-8', newline='') as stream:
            json.dump(merged, stream, indent=2, ensure_ascii=False)
    return merged
