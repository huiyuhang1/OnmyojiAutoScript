from datetime import datetime

import pytest

from module.config.config import Config
from module.config.config_model import ConfigModel
from module.config.config_modify import ConfigModify
from module.config.config_persistence import merge_changes


@pytest.fixture
def config_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    initial = ConfigModel('live')
    initial.save()
    return tmp_path / 'config' / 'live.json'


def test_running_task_save_preserves_close_computer(config_folder):
    running = Config('live')
    gui = ConfigModify('live')
    device_config = Config('live')
    optimization_reference = running.script.optimization
    assert gui.gui_set_task('Script', 'Optimization', 'when_task_queue_empty', 'close_computer')

    # Completing a task updates scheduling through an older config instance.
    next_run = datetime(2026, 10, 9, 18, 0)
    running.demon_encounter.scheduler.next_run = next_run
    running.save()
    assert running.script.optimization is optimization_reference
    assert optimization_reference.when_task_queue_empty == 'close_computer'

    # Scheduler status and device saves used to overwrite the GUI edit again.
    running.model.running_task = ''
    device_config.script.device.handle = 'updated-handle'
    device_config.save()
    latest = ConfigModel('live')
    assert latest.script.optimization.when_task_queue_empty == 'close_computer'
    assert latest.demon_encounter.scheduler.next_run == next_run
    assert latest.script.device.handle == 'updated-handle'


def test_second_gui_edit_preserves_scheduler_changes(config_folder):
    gui = ConfigModify('live')
    running = Config('live')
    assert gui.gui_set_task('Script', 'Optimization', 'when_task_queue_empty', 'close_computer')
    running.model.running_task = 'DemonEncounter'
    assert gui.gui_set_task('Script', 'Optimization', 'when_task_queue_empty', 'close_game')
    assert ConfigModel('live').running_task == 'DemonEncounter'
    running.model.running_task = ''
    assert ConfigModel('live').script.optimization.when_task_queue_empty == 'close_game'


def test_same_field_explicit_change_wins_without_overwriting_other_fields():
    assert merge_changes(
        {'option': 'goto_main', 'scheduler': {'next_run': 'old'}},
        {'option': 'close_computer', 'scheduler': {'next_run': 'old'}},
        {'option': 'close_game', 'scheduler': {'next_run': 'new'}, 'unknown': 42},
    ) == {'option': 'close_computer', 'scheduler': {'next_run': 'new'}, 'unknown': 42}


def test_invalid_file_is_not_replaced(config_folder):
    config = Config('live')
    config_folder.write_text('{unfinished', encoding='utf-8')
    with pytest.raises(ValueError):
        config.save()
    assert config_folder.read_text(encoding='utf-8') == '{unfinished'


def test_gui_edit_during_save_is_kept_for_next_save(config_folder, monkeypatch):
    running = Config('live')
    gui = ConfigModify('live')
    assert gui.gui_set_task('Script', 'Optimization', 'when_task_queue_empty', 'close_computer')
    from module.config.config_persistence import save_changes
    def edit_during_save(*args):
        merged = save_changes(*args)
        running.script.optimization.when_task_queue_empty = 'close_game'
        return merged
    with monkeypatch.context() as patch:
        patch.setattr('module.config.config_model.save_changes', edit_during_save)
        running.save()
    assert running.script.optimization.when_task_queue_empty == 'close_game'
    running.save()
    assert ConfigModel('live').script.optimization.when_task_queue_empty == 'close_game'


def test_reset_schedule_preserves_live_option(config_folder):
    running = Config('live')
    gui = ConfigModify('live')
    assert gui.gui_set_task('Script', 'Optimization', 'when_task_queue_empty', 'close_computer')
    running.model.reset_datetime_for_all_enabled_tasks(datetime(2026, 10, 9, 18, 0))
    running.save()
    assert ConfigModel('live').script.optimization.when_task_queue_empty == 'close_computer'
    assert running.script.optimization.when_task_queue_empty == 'close_computer'
