import logging

import cv2
import numpy as np
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget

from .view import VideoViewer


class VideoApp(VideoViewer):
    def __init__(self, videopath, title='PyQt5 video labeling viewer'):
        super().__init__(title=title)
        self.videopath = videopath

        # read video
        self.cap = cv2.VideoCapture(self.videopath)
        self.current_frame_idx = 0
        self._update_frame(self.current_frame_idx)

        # # widget binding
        self.slider_video.setRange(0, self.frame_count)
        self.slider_video.sliderMoved.connect(self.on_slider_moved)
        self.slider_video.sliderReleased.connect(self.on_slider_released)
        # self.btn_play_video.clicked.connect(self.play_video)
        # self.slider_video.sliderMoved.connect(self.set_video_position)
        self.show()

    @property
    def frame_count(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) if self.cap else None

    @property
    def frame_height(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if self.cap else None

    @property
    def frame_width(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if self.cap else None

    @property
    def video_fps(self):
        return int(self.cap.get(cv2.CAP_PROP_FPS)) if self.cap else None

    def _ndarray_to_qimage(self, image: np.ndarray):
        """convert cv2 image to pyqt5 image
        Arguments:
            image {np.ndarray} -- original RGB image

        Returns:
            {QImage} -- pyqt5 image format
        """
        return QImage(image, image.shape[1], image.shape[0], QImage.Format_RGB888)

    def _read_frame(self, frame_idx: int):
        """check frame idx and read frame status than return frame
        Arguments:
            frame_idx {int} -- frame index

        Returns:
            {np.ndarray} -- RGB image in (h, w, c)
        """
        if frame_idx >= self.frame_count:
            self.logger.exception('frame index %d should be less than %d', frame_idx, self.frame_count)
        else:
            self.current_frame_idx = frame_idx
            self.cap.set(1, frame_idx)
            read_success, frame = self.cap.read()
            if read_success:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return frame
            self.logger.exception('read #%d frame failed', frame_idx)

    def _update_frame(self, frame_idx: int):
        """read and update image to label
        Arguments:
            frame_idx {int} -- frame index
        """
        frame = self._read_frame(frame_idx)
        if frame is not None:
            pixmap = QPixmap(self._ndarray_to_qimage(frame))
            resize_w = int(min(pixmap.width(), self.screen.width()*0.8))
            resize_h = int(pixmap.height() * (resize_w/pixmap.width()))
            pixmap = pixmap.scaled(resize_w, resize_h, Qt.KeepAspectRatio)
            self.label_frame.setPixmap(pixmap)
            self.label_frame.resize(resize_w, resize_h)
            self._update_frame_status(self.current_frame_idx)

    def _update_frame_status(self, frame_idx: int):
        msg = '#frame ({}/{})'.format(frame_idx, self.frame_count)
        self.label_video_status.setText(msg)
    
    @pyqtSlot()
    def on_slider_released(self):
        self._update_frame(self.slider_video.value())
    
    @pyqtSlot()
    def on_slider_moved(self):
        self._update_frame_status(frame_idx=self.slider_video.value())
