from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from module.device.platform2.emulator_windows import EmulatorInstance
from module.device.platform2.platform_windows import PlatformWindows


@pytest.mark.parametrize('exe,name,start,stop,wait', [
    ('MuMuNxMain.exe', 'MuMuPlayer-12.0-0',
     'MuMuManager.exe" control -v 0 launch',
     'MuMuManager.exe" control -v 0 shutdown', True),
    ('MuMuNxMain.exe', 'MuMuPlayer-12.0-2',
     'MuMuManager.exe" control -v 2 launch',
     'MuMuManager.exe" control -v 2 shutdown', True),
    ('MuMuPlayer.exe', 'MuMuPlayer-12.0-0',
     'MuMuPlayer.exe" -v 0',
     'MuMuManager.exe" api -v 0 shutdown_player', False),
    ('MuMuNxMain.exe', 'MuMuPlayerGlobal-15.0-1',
     'MuMuManager.exe" control -v 1 --version 15 launch',
     'MuMuManager.exe" control -v 1 --version 15 shutdown', True),
])
@pytest.mark.parametrize('background', [False, True])
def test_mumu_targets_instance_and_preserves_older_versions(exe, name, start, stop, wait, background):
    instance = EmulatorInstance('127.0.0.1:16384', name, f'C:/Program Files/MuMu/{exe}')
    process = Mock()
    task = SimpleNamespace(
        config=SimpleNamespace(script=SimpleNamespace(device=SimpleNamespace(
            emulator_window_minimize=False, run_background_only=background))),
        execute=Mock(return_value=process))
    PlatformWindows._emulator_stop(task, instance)
    task.execute.assert_called_once_with(f'"C:/Program Files/MuMu/{stop}')
    if wait:
        process.wait.assert_called_once_with(timeout=30)
    else:
        process.wait.assert_not_called()
    task.execute.reset_mock()
    PlatformWindows._emulator_start(task, instance)
    task.execute.assert_called_once_with(f'"C:/Program Files/MuMu/{start}', show_window=not background)
