from types import SimpleNamespace

import pytest

from module.exception import GameStuckError
from tasks.RichMan.mall.scales import Scales


@pytest.mark.parametrize('automatic', [True, False])
@pytest.mark.parametrize('requested,available,money,expected', [
    (30, 30, 9000, [30]),
    (12, 30, 9000, [12]),
    (30, 18, 9000, [18]),
    (30, 30, 1000, [5]),
    (1, 30, 9000, [1]),
    (40, 50, 10000, [30, 10]),
])
def test_sea_purchase_uses_thirty_item_batches(monkeypatch, automatic, requested, available, money, expected):
    monkeypatch.setattr('tasks.RichMan.mall.scales.time.sleep', lambda _: None)
    calls = []
    def buy(target, number):
        calls.append(number)
    task = SimpleNamespace(
        screenshot=lambda: None, device=SimpleNamespace(image=None),
        I_SCA_PICTURE_BOOK='sea', appear=lambda _: True,
        O_SCA_NUMBER_SEA=SimpleNamespace(ocr=lambda _: available),
        O_SCA_RES_SEA=SimpleNamespace(ocr=lambda _: money),
        config=SimpleNamespace(rich_man=SimpleNamespace(scales=SimpleNamespace(enable_book_auto=automatic))),
        _scales_buy_more=buy if automatic else None,
        _scales_buy_sea_more=buy if not automatic else None,
    )
    Scales._scales_sea(task, requested)
    assert calls == expected


def result_task(monkeypatch, after):
    monkeypatch.setattr('tasks.RichMan.mall.scales.time.sleep', lambda _: None)
    class Deadline:
        def __init__(self, *args):
            self.calls = 0
        def start(self):
            return self
        def reached(self):
            self.calls += 1
            return self.calls > 5
    monkeypatch.setattr('tasks.RichMan.mall.scales.Timer', Deadline)
    task = SimpleNamespace()
    for name in ['I_BUY_PLUS', 'I_SCA_SIX_STAR', 'I_SCA_REWARD', 'C_BUY_MORE',
                 'I_MALL_CONSIGNMENT', 'I_MALL_SCCALES']:
        setattr(task, name, name)
    frames, clicks = [], []
    task.screenshot = lambda: frames.append(1)
    task.appear = lambda target: (target == task.I_BUY_PLUS and len(frames) == 2) or (
        target in (task.I_MALL_CONSIGNMENT, task.I_MALL_SCCALES) and len(frames) >= 3)
    task._scales_resource_amount = lambda _: 9000 if len(frames) == 1 else after
    task._scales_buy_confirm = lambda *args: None
    task.save_image = lambda: None
    def click(target, **kwargs):
        assert len(frames) == 2, 'Must not click disappeared purchase dialog'
        clicks.append(target)
        return True
    task.click = click
    return task, clicks


def test_returned_shop_and_spent_currency_confirm_purchase(monkeypatch):
    task, clicks = result_task(monkeypatch, 3000)
    assert Scales._scales_buy_more(task, 'sea', 30) is True
    assert clicks == [task.C_BUY_MORE]


def test_returned_shop_without_currency_change_does_not_blindly_click(monkeypatch):
    task, clicks = result_task(monkeypatch, 9000)
    with pytest.raises(GameStuckError, match='result could not be confirmed'):
        Scales._scales_buy_more(task, 'sea', 30)
    assert clicks == [task.C_BUY_MORE]


@pytest.mark.parametrize('number,readings,expected', [(30, [30], ['max']), (2, [5, 3, 2], ['sub', 'sub'])])
def test_quantity_is_exact(monkeypatch, number, readings, expected):
    clicks = []
    readings = iter(readings)
    task = SimpleNamespace(
        screenshot=lambda: None, device=SimpleNamespace(image=None),
        I_BUY_PLUS='max', I_BUY_ADD='add', I_BUY_SUB='sub',
        appear=lambda target: target == 'max',
        O_BUY_NUMBER=SimpleNamespace(ocr=lambda _: next(readings)),
        appear_then_click=lambda target, **kwargs: clicks.append(target),
    )
    Scales._scales_buy_confirm(task, 'sea', number)
    assert clicks == expected
