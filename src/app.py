import logging
from collections import OrderedDict
from time import sleep

import cv2
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QColor
from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox, QStyle, QWidget

from .view import VideoAppViewer


class VideoApp(VideoAppViewer):
    def __init__(self, videopath: str, outpath: str, **config):
        self.videopath = videopath
        self.outpath = outpath
        self.config = config
        self.title = self.config.get('title', 'PyQt5 video labeling viewer')
        super().__init__(title=self.title)

        # draw config
        label_color = self.config.get('label_color', QColor(0, 0, 0))
        label_thickness = self.config.get('label_thickness', 2)
        label_style = self.config.get('label_style', Qt.SolidLine)
        self.label_frame.pen_color = label_color
        self.label_frame.pen_thickness = label_thickness
        self.label_frame.pen_style = label_style

        # record config
        self.limit_nlabel = self.config.get('limit_nlabel', None)
        self.records = []

        # read video
        self.cap = cv2.VideoCapture(self.videopath)
        self.target_frame_idx = 0       # ready to update
        self.render_frame_idx = None    # redneded
        self.scale_height = self.scale_width = None
        self.is_playing_video = False
        self._update_frame()

        # widget binding
        self.slider_video.setRange(0, self.frame_count-1)
        self.slider_video.sliderMoved.connect(self.on_slider_moved)
        self.slider_video.sliderReleased.connect(self.on_slider_released)
        self.btn_play_video.clicked.connect(self.on_play_video_clicked)
        self.label_frame.mousePressEvent = self.event_frame_mouse_press
        self.label_frame.mouseMoveEvent = self.event_frame_mouse_move
        self.label_frame.mouseReleaseEvent = self.event_frame_mouse_release
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
            self.target_frame_idx = frame_idx
            self.cap.set(1, frame_idx)
            read_success, frame = self.cap.read()
            if read_success:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return frame
            self.logger.exception('read #%d frame failed', frame_idx)

    def _update_frame(self):
        """read and update image to label"""
        if self.target_frame_idx != self.render_frame_idx:
            frame = self._read_frame(self.target_frame_idx)
            if frame is not None:
                pixmap = QPixmap(self._ndarray_to_qimage(frame))
                self.scale_width = int(min(pixmap.width(), self.screen.width()*0.8))
                self.scale_height = int(pixmap.height() * (self.scale_width / pixmap.width()))
                pixmap = pixmap.scaled(self.scale_width, self.scale_height, Qt.KeepAspectRatio)
                self.label_frame.setPixmap(pixmap)
                self.label_frame.resize(self.scale_width, self.scale_height)
                self._update_frame_status(self.target_frame_idx)
                self.render_frame_idx = self.target_frame_idx
                self.slider_video.setValue(self.render_frame_idx)

        QTimer.singleShot(1000/self.video_fps, self._update_frame)

    def _update_frame_status(self, frame_idx: int, err: str = ''):
        """update frame status
        Arguments:
            frame_idx {int} -- frame index

        Keyword Arguments:
            err {str} -- show status when exception (default: '')
        """
        msg = '#frame ({}/{})'.format(frame_idx, self.frame_count-1)
        if err:
            msg += '\n{}'.format(err)
        self.label_video_status.setText(msg)

    def _play_video(self):
        """play video when button clicked"""
        if self.is_playing_video and self.video_fps:
            frame_idx = min(self.render_frame_idx+1, self.frame_count)
            if frame_idx == self.frame_count:
                self.on_play_video_clicked()
            else:
                self.target_frame_idx = frame_idx
        QTimer.singleShot(1/self.video_fps, self._play_video)

    def _check_coor_in_frame(self, coor_x: int, coor_y: int):
        """check the coordinate in mouse event"""
        return 0 < coor_x < self.scale_width and 0 < coor_y < self.scale_height

    def _nrecord_in_current_frame(self):
        if self.records:
            rest = list(filter(lambda x: x['frame_idx'] == self.render_frame_idx, self.records))
            return len(rest) if rest else None

    @pyqtSlot()
    def on_slider_released(self):
        """update frame and frame status when the slider released"""
        self.target_frame_idx = self.slider_video.value()

    @pyqtSlot()
    def on_slider_moved(self):
        """update frame status only when the slider moved"""
        self._update_frame_status(frame_idx=self.slider_video.value())

    @pyqtSlot()
    def on_play_video_clicked(self):
        """control to play or pause the video"""
        self.is_playing_video = not self.is_playing_video
        if self.is_playing_video:
            self.btn_play_video.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self._play_video()
        else:
            self.btn_play_video.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    @pyqtSlot()
    def event_frame_mouse_press(self, event):
        if self._check_coor_in_frame(event.x(), event.y()) and not self.is_playing_video:
            nrecords = self._nrecord_in_current_frame()
            if self.limit_nlabel and nrecords and self.limit_nlabel <= nrecords:
                self.logger.warning('not available to add a new record (exist=%d, limit=%d)', \
                                    nrecords, self.limit_nlabel)
            else:
                self.label_frame.is_drawing = True
                self.logger.debug('press mouse at (%d, %d)', event.x(), event.y())
                self.label_frame.pt1 = (event.x(), event.y())

    @pyqtSlot()
    def event_frame_mouse_move(self, event):
        if self.label_frame.is_drawing and self._check_coor_in_frame(event.x(), event.y()):
            self.logger.debug('move mouse at (%d, %d)', event.x(), event.y())
            self.label_frame.pt2 = (event.x(), event.y())
            pt1 = (min(self.label_frame.pt1[0], self.label_frame.pt2[0]), \
                   min(self.label_frame.pt1[1], self.label_frame.pt2[1]))
            pt2 = (max(self.label_frame.pt1[0], self.label_frame.pt2[0]), \
                   max(self.label_frame.pt1[1], self.label_frame.pt2[1]))
            self.label_frame.pt1, self.label_frame.pt2 = pt1, pt2
            self.update()

    @pyqtSlot()
    def event_frame_mouse_release(self, event):
        if self.label_frame.is_drawing and self._check_coor_in_frame(event.x(), event.y()):
            self.label_frame.is_drawing = False
            self.logger.debug('release mouse at (%d, %d)', event.x(), event.y())
            self.label_frame.pt2 = (event.x(), event.y())
            self.records.append(OrderedDict([
                ('frame_idx', self.render_frame_idx), ('fps', self.video_fps),
                ('frame_height', self.frame_height), ('frame_width', self.frame_width),
                ('scale_height', self.scale_height), ('scale_width', self.scale_width),
                ('x1', min(self.label_frame.pt1[0], self.label_frame.pt2[0])),
                ('y1', min(self.label_frame.pt1[1], self.label_frame.pt2[1])),
                ('x2', max(self.label_frame.pt1[0], self.label_frame.pt2[0])),
                ('y2', max(self.label_frame.pt1[1], self.label_frame.pt2[1]))
            ]))
            self.label_frame.pt1 = self.label_frame.pt2 = None

    def exports(self):
        df_labels = pd.DataFrame().from_records(self.records)
        print(df_labels)
        df_labels.to_csv(self.outpath, index=False)

    def keyPressEvent(self, event):
        """global keyboard event"""
        if event.key() in [Qt.Key_Space, Qt.Key_P]:
            self.on_play_video_clicked()
        elif event.key() in [Qt.Key_Right, Qt.Key_D]:
            self.target_frame_idx = min(self.target_frame_idx+self.video_fps, self.frame_count-1)
        elif event.key() in [Qt.Key_Left, Qt.Key_A]:
            self.target_frame_idx = max(0, self.target_frame_idx-self.video_fps)
        else:
            self.logger.debug('clicked %s but no related binding event', str(event.key()))
