from types import SimpleNamespace

import pytest

from tasks.RichMan.mall.bondlings import Bondlings
from tasks.RichMan.assets import RichManAssets


def locate_task():
    task = SimpleNamespace(device=SimpleNamespace(image=None))
    for name in ['I_BL_BUY_SOULS', 'I_BL_BUY_STONE', 'I_BL_BUY_HIGH', 'I_BL_BUY_MEDIUM']:
        setattr(task, name, getattr(RichManAssets, name))
    task._bondlings_item_matches = Bondlings._bondlings_item_matches
    return task


def mock_titles(monkeypatch, titles):
    def detect(ocr, image):
        centers = [242, 537, 823, 1125]
        center = ocr.roi[0] + 115
        index = centers.index(center)
        return [SimpleNamespace(ocr_text=titles[index], score=1)]
    monkeypatch.setattr('tasks.RichMan.mall.bondlings.RuleOcr.detect_and_ocr', detect)


def test_sold_out_souls_never_buy_stone_in_first_column(monkeypatch):
    mock_titles(monkeypatch, ['鸣契石', '高级契灵盘', '中级契灵盘', ''])
    task = locate_task()
    assert Bondlings._bondlings_locate_item(
        task, task.I_BL_BUY_SOULS, RichManAssets.O_BL_RES_SOULS, 1) is None


def test_shifted_item_updates_button_and_counter_without_mutating_assets(monkeypatch):
    mock_titles(monkeypatch, ['鸣契石', '高级契灵盘', '中级契灵盘', ''])
    task = locate_task()
    original = list(task.I_BL_BUY_STONE.roi_front)
    button, counter = Bondlings._bondlings_locate_item(
        task, task.I_BL_BUY_STONE, RichManAssets.O_BL_RES_STONE, 2)
    assert button.roi_front[0] == original[0] - 295
    assert counter.roi[0] == RichManAssets.O_BL_RES_STONE.roi[0] - 295
    assert list(task.I_BL_BUY_STONE.roi_front) == original


def test_zero_quantity_returns_before_any_lookup_or_click():
    task = SimpleNamespace()
    # Missing screenshot/locator/buy methods intentionally fail if zero executes anything.
    Bondlings._bondlings_base(task, RichManAssets.I_BL_BUY_STONE,
                             RichManAssets.O_BL_RES_STONE, 2, 0, 10, 30)


def test_next_batch_stops_if_goods_disappeared(monkeypatch):
    monkeypatch.setattr('tasks.RichMan.mall.bondlings.time.sleep', lambda _: None)
    button = RichManAssets.I_BL_BUY_SOULS
    counter = SimpleNamespace(ocr=lambda _: 30)
    locations = iter([(button, counter), (button, counter), None])
    purchases = []
    def buy(target, number):
        purchases.append((target, number))
        return True
    task = SimpleNamespace(
        device=SimpleNamespace(image=None), screenshot=lambda: None,
        _bondlings_locate_item=lambda *args: next(locations), appear=lambda _: True,
        O_BL_CHECK_MONEY=SimpleNamespace(ocr=lambda _: (1000, 3000, 4000)),
        buy_more=buy,
    )
    Bondlings._bondlings_base(task, button, counter, 1, 30, 25, 20)
    assert purchases == [(button, 25)]


@pytest.mark.parametrize('title,kind,expected', [
    ('六星随机御魂', 1, True), ('鸣契石', 1, False),
    ('鸣 契 石', 2, True), ('', 1, False),
    ('高级契灵盘', 3, True), ('中级契灵盘', 3, False),
])
def test_item_name_matches_requested_goods(title, kind, expected):
    assert Bondlings._bondlings_item_matches(title, kind) is expected
