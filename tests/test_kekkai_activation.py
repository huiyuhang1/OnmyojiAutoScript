from types import SimpleNamespace

import pytest

from tasks.KekkaiActivation.card_filter import card_experience, experience_allowed, income_value
from tasks.KekkaiActivation.config import ActivationConfig, CardType
from tasks.KekkaiActivation.script_task import ScriptTask


def text(value, y, x=0):
    return SimpleNamespace(ocr_text=value, box=[[x, y], [x + 100, y],
                                             [x + 100, y + 20], [x, y + 20]])


@pytest.mark.parametrize('value,allowed', [(2800, False), (2400, True), (1600, True),
                                        (None, False), (0, False), (280, False), (28000, False)])
def test_experience_filter(value, allowed):
    assert experience_allowed(value) is allowed


def test_income_does_not_use_experience_or_duration_as_resource():
    assert income_value('式神经验+2800 勾玉+12/小时 24小时', '勾玉') == 12
    assert income_value('式神经验＋2,400', '经验') == 2400
    assert income_value('体力', '体力') is None


def test_experience_is_associated_with_its_own_card():
    six_exp, six_income = text('式神经验+2800', 0), text('勾玉+16', 30)
    five_exp, five_income = text('式神经验+2400', 140), text('勾玉+12', 170)
    results = [five_income, six_exp, five_exp, six_income]
    assert card_experience(six_income, results) == 2800
    assert card_experience(five_income, results) == 2400
    assert card_experience(five_income, [six_exp, five_income]) is None
    assert card_experience(five_income, [text('经验2400', 140, x=200)]) is None


def fake_task(results, enabled=True, rule=CardType.TAIKO):
    config = ActivationConfig(exclude_six_star=enabled, card_type=rule)
    ocr = SimpleNamespace(roi=(305, 153, 220, 481), detect_and_ocr=lambda image: results)
    return SimpleNamespace(
        config=SimpleNamespace(kekkai_activation=SimpleNamespace(activation_config=config)),
        device=SimpleNamespace(image=None, swipe_adb=lambda *args, **kw: None),
        screenshot=lambda: None, O_CHECK_CARD_NUMBER=ocr, O_SELECTED_CARD_EXP=ocr,
    )


@pytest.mark.parametrize('label,rule', [('勾玉', CardType.TAIKO), ('体力', CardType.FISH)])
@pytest.mark.parametrize('enabled,expected_y', [(True, 323), (False, 183)])
def test_switch_filters_six_star_before_ranking(label, rule, enabled, expected_y):
    results = [text('式神经验+2800', 0), text(label + '+32', 30),
               text('式神经验+2400', 140), text(label + '+24', 170)]
    target = ScriptTask.check_card_num(fake_task(results, enabled, rule))
    assert target.roi_front[1] == expected_y


def test_unknown_experience_and_only_six_star_do_not_select(monkeypatch):
    monkeypatch.setattr('tasks.KekkaiActivation.script_task.time.sleep', lambda seconds: None)
    results = [text('式神经验+2800', 0), text('勾玉+32', 30), text('勾玉+24', 170)]
    assert ScriptTask.check_card_num(fake_task(results)) is None


@pytest.mark.parametrize('exp,allowed', [('2800', False), ('2400', True), ('?', False)])
def test_selected_card_is_checked_before_activation(monkeypatch, exp, allowed):
    monkeypatch.setattr('tasks.KekkaiActivation.script_task.time.sleep', lambda seconds: None)
    assert ScriptTask.selected_card_allowed(fake_task([text('式神经验+' + exp, 0)])) is allowed


def test_existing_config_defaults_to_excluding_six_star():
    assert ActivationConfig.model_validate({}).exclude_six_star is True


def test_preselected_six_star_never_reaches_activate(monkeypatch):
    monkeypatch.setattr('tasks.KekkaiActivation.script_task.time.sleep', lambda seconds: None)
    task = fake_task([text('式神经验+2800', 0)])
    task.goto_cards = lambda: None
    task.check_card_status = lambda: True
    task.check_card_effect = lambda: False
    task.selected_card_allowed = lambda: ScriptTask.selected_card_allowed(task)
    task.save_image = lambda **kwargs: None
    task.set_next_run = lambda *args, **kwargs: None
    # No click/appear methods: attempting activation would fail this test.
    assert ScriptTask.run_activation(task, task.config.kekkai_activation.activation_config) is False


def smart_put_task(monkeypatch, *, button_after=0, success_after=1, stable=True):
    clock = [0.0]
    clicks = []
    screenshots = []
    failures = []
    monkeypatch.setattr('tasks.KekkaiActivation.script_task.time.monotonic', lambda: clock[0])
    monkeypatch.setattr('tasks.KekkaiActivation.script_task.time.sleep',
                        lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    task = SimpleNamespace()
    for name in ['I_RS_RECORDS_SHIKI', 'I_RS_SMART_EXCHANGE', 'I_RS_LEVEL_MAX'] + [
            f'I_DETECT_EMPTY_{n}' for n in range(1, 7)]:
        setattr(task, name, name)

    def appear(target):
        if target == 'I_RS_RECORDS_SHIKI':
            return stable
        if target in ('I_RS_LEVEL_MAX', 'I_DETECT_EMPTY_1'):
            return len(clicks) < success_after
        return False

    def click(target):
        assert target == 'I_RS_SMART_EXCHANGE'
        if clock[0] < button_after:
            return False
        clicks.append(clock[0])
        return True

    task.appear = appear
    task.appear_then_click_multi_scale = click
    task.screenshot = lambda: screenshots.append(clock[0])
    task.save_image = lambda **kwargs: failures.append(kwargs)
    return task, clicks, screenshots, failures


def test_smart_put_waits_for_late_button_and_verifies_result(monkeypatch):
    task, clicks, frames, failures = smart_put_task(monkeypatch, button_after=2)
    assert ScriptTask.smart_put_shikigami(task) is True
    assert len(clicks) == 1 and clicks[0] >= 2
    assert frames[-1] - clicks[0] >= 1.3
    assert not failures


def test_smart_put_retries_when_first_click_does_not_work(monkeypatch):
    task, clicks, _, failures = smart_put_task(monkeypatch, success_after=2)
    assert ScriptTask.smart_put_shikigami(task) is True
    assert len(clicks) == 2 and clicks[1] - clicks[0] >= 3
    assert not failures


@pytest.mark.parametrize('options,expected_clicks', [
    ({'button_after': 100}, 0), ({'stable': False}, 0), ({'success_after': 100}, 3)])
def test_smart_put_times_out_and_saves_failure(monkeypatch, options, expected_clicks):
    task, clicks, frames, failures = smart_put_task(monkeypatch, **options)
    assert ScriptTask.smart_put_shikigami(task) is False
    assert len(clicks) == expected_clicks
    assert len(failures) == 1 and failures[0]['image_type'] == 'png'
    assert frames[-1] < 15
