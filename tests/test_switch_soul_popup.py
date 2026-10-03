from types import SimpleNamespace

import pytest

from module.exception import GameStuckError
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul


@pytest.mark.parametrize('title,cancel,handled,clicked', [
    ('场景扩展包下载', '取消', True, True),
    ('场景 扩展包 下载', '取 消', True, True),
    ('场景扩展包下载', '', True, False),
    ('其他确认窗口', '取消', False, False),
])
def test_only_cancel_scene_download(title, cancel, handled, clicked):
    clicks = []
    cancel_rule = SimpleNamespace(ocr=lambda image: cancel)
    task = SimpleNamespace(
        device=SimpleNamespace(image=None),
        O_SCENE_DOWNLOAD_TITLE=SimpleNamespace(ocr=lambda image: title),
        O_SCENE_DOWNLOAD_CANCEL=cancel_rule,
        click=lambda target, **kwargs: clicks.append(target),
    )
    assert SwitchSoul.cancel_scene_download(task) is handled
    assert clicks == ([cancel_rule] if clicked else [])


def preset_task(monkeypatch, modal_frames=0, opens=True):
    frames, clicks, failures = [], [], []
    monkeypatch.setattr('tasks.Component.SwitchSoul.switch_soul.sleep', lambda seconds: None)
    class BoundedTimer:
        def __init__(self, *args):
            self.n = 0
        def start(self):
            return self
        def reached(self):
            self.n += 1
            return self.n > 12
    monkeypatch.setattr('tasks.Component.SwitchSoul.switch_soul.Timer', BoundedTimer)
    task = SimpleNamespace()
    for name in ['I_SOU_SWITCH_1', 'I_SOU_SWITCH_2', 'I_SOU_SWITCH_3',
                 'I_SOU_SWITCH_4', 'I_SOU_TEAM_PRESENT', 'I_SOUL_PRESET']:
        setattr(task, name, name)
    task.screenshot = lambda: frames.append(1)
    task.cancel_scene_download = lambda: len(frames) <= modal_frames
    task.appear = lambda target: target == 'I_SOUL_PRESET' or (
        target == 'I_SOU_SWITCH_1' and bool(clicks) and opens)
    def click(target, **kwargs):
        assert len(frames) > modal_frames
        clicks.append(target)
        return True
    task.click = click
    task.save_image = lambda **kwargs: failures.append(kwargs)
    return task, clicks, failures


def test_popup_clears_before_preset_click(monkeypatch):
    task, clicks, failures = preset_task(monkeypatch, modal_frames=2)
    SwitchSoul.click_preset(task)
    assert clicks == ['I_SOUL_PRESET']
    assert not failures


def test_preset_clicks_are_bounded(monkeypatch):
    task, clicks, failures = preset_task(monkeypatch, opens=False)
    with pytest.raises(GameStuckError):
        SwitchSoul.click_preset(task)
    assert len(clicks) == 5
    assert len(failures) == 1


def test_unhandled_modal_times_out_without_clicking_background(monkeypatch):
    task, clicks, failures = preset_task(monkeypatch, modal_frames=100)
    with pytest.raises(GameStuckError):
        SwitchSoul.click_preset(task)
    assert not clicks
    assert len(failures) == 1
