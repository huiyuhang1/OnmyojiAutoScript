from types import SimpleNamespace

import pytest

from module.exception import GameStuckError
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.DemonEncounter.script_task import ScriptTask


@pytest.mark.parametrize('battle_frame', [1, 2, 3, 4])
def test_preset_stops_when_battle_starts_at_any_stage(monkeypatch, battle_frame):
    frames, clicks = [], []
    monkeypatch.setattr('tasks.Component.GeneralBattle.general_battle.time.sleep', lambda _: None)
    monkeypatch.setattr('tasks.Component.GeneralBattle.general_battle.get_color', lambda *args: (0, 0, 0))
    task = SimpleNamespace(device=SimpleNamespace(image=None))
    for name in ['I_PRESET_ENSURE', 'I_PRESENT_LESS_THAN_5', 'I_PRESET',
                 'I_PRESET_WIT_NUMBER', 'O_PRESET', 'O_PRESET_FULL']:
        setattr(task, name, name)
    task.C_PRESET_GROUP_1 = SimpleNamespace(roi_back=(0, 0, 5, 5))
    task.C_PRESET_TEAM_1 = SimpleNamespace(roi_back=(0, 0, 5, 5))
    task.screenshot = lambda: frames.append(1)
    task.is_in_real_battle = lambda _: len(frames) >= battle_frame
    task.appear = lambda target: target == task.I_PRESET_ENSURE
    task.wait_until_appear = lambda *args, **kwargs: None
    def click(target, **kwargs):
        assert len(frames) < battle_frame
        clicks.append(target)
    task.click = click
    assert GeneralBattle.switch_preset_team(task, True) is False
    assert len(frames) == battle_frame


def test_missing_preset_does_not_wait_forever(monkeypatch):
    class Deadline:
        def __init__(self, *args):
            self.calls = 0
        def start(self):
            return self
        def reached(self):
            self.calls += 1
            return self.calls > 3
    monkeypatch.setattr('tasks.Component.GeneralBattle.general_battle.Timer', Deadline)
    saved = []
    task = SimpleNamespace(
        screenshot=lambda: None, is_in_real_battle=lambda _: False,
        appear=lambda *args: False, appear_then_click=lambda *args, **kwargs: False,
        ocr_appear=lambda *args: False, save_image=lambda: saved.append(True),
    )
    for name in ['I_PRESET_ENSURE', 'I_PRESENT_LESS_THAN_5', 'I_PRESET',
                 'I_PRESET_WIT_NUMBER', 'O_PRESET', 'O_PRESET_FULL']:
        setattr(task, name, name)
    with pytest.raises(GameStuckError, match='Preset selection timed out'):
        GeneralBattle.switch_preset_team(task, True)
    assert saved == [True]


def test_battle_before_does_not_open_buff_after_auto_start():
    started = []
    task = SimpleNamespace(
        current_count=1, screenshot=lambda: None,
        is_in_real_battle=lambda _: bool(started), is_in_prepare=lambda _: True,
        appear_then_click=lambda *args, **kwargs: False,
        I_DISABLE_7DAYS_DIFF_SOUL=None, I_CONFIRM_CLOSE_DIFF_SOUL=None,
        switch_preset_team=lambda *args: started.append(True),
    )
    assert GeneralBattle.battle_before(task, None, GeneralBattleConfig(preset_enable=True)) is True


@pytest.mark.parametrize('scenes', [
    ['gather', 'gather', 'prepare', 'prepare', 'done'],
    ['gather', 'battle', 'done'],
    ['prepare', 'done'],
    ['battle', 'done'],
    ['reward', 'done'],
])
def test_boss_retries_keep_preset_and_take_over_started_battle(monkeypatch, scenes):
    monkeypatch.setattr('tasks.DemonEncounter.script_task.sleep', lambda _: None)
    original = object()
    task = SimpleNamespace(device=SimpleNamespace(stuck_timer_long=original), current_count=9)
    task.device.stuck_record_clear = lambda: None
    task.device.stuck_record_add = lambda _: None
    for name in ['I_BOSS_DONE_CHECK', 'I_PREPARE_HIGHLIGHT', 'I_BOSS_GATHER',
                 'I_BOSS_WAIT', 'I_DE_WIN', 'I_WIN', 'I_FALSE', 'I_REWARD']:
        setattr(task, name, name)
    sequence = iter(scenes)
    task.screenshot = lambda: setattr(task, 'scene', next(sequence))
    task.appear = lambda target: target == {
        'prepare': task.I_PREPARE_HIGHLIGHT,
        'gather': task.I_BOSS_GATHER,
        'reward': task.I_REWARD,
        'done': task.I_BOSS_DONE_CHECK,
    }.get(task.scene)
    task.is_in_real_battle = lambda _: task.scene == 'battle'
    config = GeneralBattleConfig(preset_enable=True, preset_group=7, preset_team=1)
    calls = []
    switches = []
    def switch_boss_preset(selected_config):
        assert task.scene == 'gather'
        switches.append((True, selected_config.preset_group, selected_config.preset_team))
        return True
    task._switch_boss_preset = switch_boss_preset
    def run_general_battle(config):
        if task.scene == 'prepare':
            assert task.current_count == 0
        calls.append(config)
        task.current_count += 1
    task.run_general_battle = run_general_battle
    ScriptTask._run_boss_battle(task, config)
    assert len(calls) == sum(scene in ('prepare', 'battle', 'reward') for scene in scenes)
    assert all(not item.preset_enable and item.preset_group == 7 and item.preset_team == 1 for item in calls)
    assert switches == ([(True, 7, 1)] if 'gather' in scenes else [])
    assert config.preset_enable is True
    assert task.device.stuck_timer_long is original


def test_boss_restores_watchdog_on_failure():
    original = object()
    def screenshot():
        raise GameStuckError('test failure')
    task = SimpleNamespace(device=SimpleNamespace(stuck_timer_long=original), screenshot=screenshot)
    with pytest.raises(GameStuckError):
        ScriptTask._run_boss_battle(task, GeneralBattleConfig())
    assert task.device.stuck_timer_long is original


def boss_preset_task(monkeypatch, scenes):
    monkeypatch.setattr('tasks.DemonEncounter.script_task.sleep', lambda _: None)
    class Deadline:
        def __init__(self, *args):
            self.calls = 0
        def start(self):
            return self
        def reached(self):
            self.calls += 1
            return self.calls > 6
    monkeypatch.setattr('tasks.DemonEncounter.script_task.Timer', Deadline)
    task = SimpleNamespace()
    for name in ['I_BOSS_DONE_CHECK', 'I_PRESET_ENSURE', 'I_PRESENT_LESS_THAN_5',
                 'I_BOSS_GATHER', 'O_BOSS_PRESET_ENTRY']:
        setattr(task, name, name)
    frames, clicks, selections = [], [], []
    def screenshot():
        task.scene = scenes[min(len(frames), len(scenes) - 1)]
        frames.append(task.scene)
    task.screenshot = screenshot
    task.appear = lambda target: target == {
        'gather': task.I_BOSS_GATHER, 'window': task.I_PRESET_ENSURE,
        'done': task.I_BOSS_DONE_CHECK,
    }.get(task.scene)
    task.is_in_real_battle = lambda _: task.scene == 'battle'
    def click(target, **kwargs):
        assert task.scene == 'gather'
        assert target == task.O_BOSS_PRESET_ENTRY
        clicks.append(target)
        return True
    task.ocr_appear_click = click
    def select(*args):
        assert task.scene == 'window'
        selections.append(args)
        return True
    task.switch_preset_team = select
    task.save_image = lambda: None
    return task, clicks, selections


def test_boss_opens_right_entry_before_selecting_team(monkeypatch):
    task, clicks, selections = boss_preset_task(monkeypatch, ['gather', 'window'])
    config = GeneralBattleConfig(preset_enable=True, preset_group=7, preset_team=1)
    assert ScriptTask._switch_boss_preset(task, config) is True
    assert clicks == [task.O_BOSS_PRESET_ENTRY]
    assert selections == [(True, 7, 1)]


@pytest.mark.parametrize('scenes,expected_clicks', [(['battle'], 0), (['gather', 'battle'], 1), (['done'], 0)])
def test_boss_entry_stops_on_battle_or_completion(monkeypatch, scenes, expected_clicks):
    task, clicks, selections = boss_preset_task(monkeypatch, scenes)
    assert ScriptTask._switch_boss_preset(task, GeneralBattleConfig()) is False
    assert len(clicks) == expected_clicks
    assert not selections


def test_boss_entry_has_bounded_retries(monkeypatch):
    task, clicks, selections = boss_preset_task(monkeypatch, ['gather'])
    with pytest.raises(GameStuckError, match='preset window could not be opened'):
        ScriptTask._switch_boss_preset(task, GeneralBattleConfig())
    assert len(clicks) == 3
    assert not selections
