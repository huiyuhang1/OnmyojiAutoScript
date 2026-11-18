from module.atom.ocr import RuleOcr
from module.logger import logger


class SceneDownloadPopup:
    O_SCENE_DOWNLOAD_TITLE = RuleOcr(
        roi=(500, 195, 290, 55), area=(500, 195, 290, 55),
        mode='Single', method='Default', keyword='', name='scene_download_title')
    O_SCENE_DOWNLOAD_CANCEL = RuleOcr(
        roi=(430, 448, 112, 43), area=(430, 448, 112, 43),
        mode='Single', method='Default', keyword='', name='scene_download_cancel')

    def cancel_scene_download(self) -> bool:
        title = ''.join(self.O_SCENE_DOWNLOAD_TITLE.ocr(self.device.image).split())
        if '场景扩展包下载' not in title:
            return False
        cancel = ''.join(self.O_SCENE_DOWNLOAD_CANCEL.ocr(self.device.image).split())
        if '取消' in cancel:
            self.click(self.O_SCENE_DOWNLOAD_CANCEL, interval=2)
            logger.info('取消场景扩展包下载弹窗，继续当前操作')
        # Even if cancel OCR fails, never click controls behind the modal.
        return True
