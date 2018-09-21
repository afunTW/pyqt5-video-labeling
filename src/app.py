import logging
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

import cv2
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QColor, QImage, QPixmap
from PyQt5.QtWidgets import QMessageBox, QStyle, QWidget

from .view import VideoAppViewer


class VideoApp(VideoAppViewer):
    def __init__(self, videopath: str, outpath: str, **config):
        self.videopath = videopath
        self.outpath = outpath
        self.config = config
        self.title = self.config.get('title', 'PyQt5 video labeling viewer')
        super().__init__(title=self.title)

        # draw config
        if self.config.get('draw') and isinstance(self.config['draw'], dict):
            draw_config = self.config['draw']
            self.label_frame.draw_color = draw_config.get('color', QColor(0, 0, 0))
            self.label_frame.draw_thickness = draw_config.get('thickness', 2)
            self.label_frame.draw_style = draw_config.get('style', Qt.SolidLine)
        if self.config.get('select') and isinstance(self.config['select'], dict):
            select_config = self.config['select']
            self.label_frame.select_color = select_config.get('color', QColor(0, 0, 0))
            self.label_frame.select_thickness = select_config.get('thickness', 3)
            self.label_frame.select_style = select_config.get('style', Qt.SolidLine)

        # record config
        check_label = self.config.get('label')
        label_color = self.config['label'].get('color', (0, 0, 0)) if check_label else None
        label_thickness = self.config['label'].get('thickness', 2) if check_label else None
        self.label_color = label_color
        self.label_thickness = label_thickness
        self.limit_nlabel = self.config.get('limit_nlabel', None)
        self.records = []

        # read video
        self.cap = cv2.VideoCapture(self.videopath)
        self.target_frame_idx = 0       # ready to update
        self.render_frame_idx = None    # redneded
        self.scale_height = self.scale_width = None
        self.is_playing_video = False
        self.is_force_update = False
        self._update_video_info()
        self._update_frame()

        # widget binding
        self.slider_video.setRange(0, self.frame_count-1)
        self.slider_video.sliderMoved.connect(self.on_slider_moved)
        self.slider_video.sliderReleased.connect(self.on_slider_released)
        self.btn_play_video.clicked.connect(self.on_play_video_clicked)
        self.label_frame.mousePressEvent = self.event_frame_mouse_press
        self.label_frame.mouseMoveEvent = self.event_frame_mouse_move
        self.label_frame.mouseReleaseEvent = self.event_frame_mouse_release
        self.btn_previous_record.clicked.connect(self._goto_previous_record)
        self.btn_next_record.clicked.connect(self._goto_next_record)
        self.btn_export_records.clicked.connect(self.save_file)
        self.table_preview_records.doubleClicked.connect(self.event_preview_double_clicked)
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

    def _frame_idx_to_hmsf(self, frame_idx: int):
        """convert to hmsf timestamp by given frame idx and fps"""
        assert self.video_fps
        base = datetime.strptime('00:00:00.000000', '%H:%M:%S.%f')
        delta = timedelta(seconds=frame_idx/self.video_fps)
        return (base + delta).strftime('%H:%M:%S.%f')

    def _frame_idx_to_hms(self, frame_idx: int):
        """convert to hms timestamp by given frame idx and fps"""
        assert self.video_fps
        base = datetime.strptime('00:00:00', '%H:%M:%S')
        delta = timedelta(seconds=frame_idx//self.video_fps)
        return (base + delta).strftime('%H:%M:%S')

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

    def _update_video_info(self):
        shape = str((self.frame_width, self.frame_height))
        self.label_video_path.setText(self.videopath)
        self.label_video_shape.setText(shape)
        self.label_video_fps.setText(str(self.video_fps))

    def _update_frame(self):
        """read and update image to label"""
        if self.target_frame_idx != self.render_frame_idx or self.is_force_update:
            self.is_force_update = False
            frame = self._read_frame(self.target_frame_idx)
            if frame is not None:
                # draw, convert, resize pixmap
                frame = self.draw_rects(self.target_frame_idx, frame)
                pixmap = QPixmap(self._ndarray_to_qimage(frame))
                self.scale_width = int(min(pixmap.width(), self.screen.width()*0.8))
                self.scale_height = int(pixmap.height() * (self.scale_width / pixmap.width()))
                pixmap = pixmap.scaled(self.scale_width, self.scale_height, Qt.KeepAspectRatio)
                self.label_frame.setPixmap(pixmap)
                self.label_frame.resize(self.scale_width, self.scale_height)

                # sync, update related information
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

    def _get_records_by_frame_idx(self, frame_idx=None):
        """return specfic records by frame index (default: current frame)"""
        frame_idx = frame_idx or self.render_frame_idx
        return list(filter(lambda x: x['frame_idx'] == frame_idx, self.records))

    def _get_nrecord_in_current_frame(self):
        """get the number of records in current frame"""
        current_records = self._get_records_by_frame_idx()
        return len(current_records) if current_records else None
    
    def _get_closest_record_in_current_frame(self, coor_x: int, coor_y: int):
        """get the closest record by given coor in current frame
        Arguments:
            coor_x {int} -- cooridinate x
            coor_y {int} -- cooridinate

        Returns:
            {OrderedDict} -- the closest record
        """
        current_records = deepcopy(self._get_records_by_frame_idx())
        for rid, record in enumerate(current_records):
            pt1, pt2 = (record['x1'], record['y1']), (record['x2'], record['y2'])
            if pt1[0] < coor_x < pt2[0] and pt1[1] < coor_y < pt2[1]:
                center = np.array(((pt2[0]+pt1[0])/2, (pt2[1]+pt1[1])/2))
                dist = np.linalg.norm(center - np.array((coor_x, coor_y)))
                current_records[rid]['dist'] = dist
        current_records = list(filter(lambda x: 'dist' in x, current_records))
        if current_records:
            return sorted(current_records, key=lambda x: x['dist'])[0]
    
    def _remove_record(self, frame_idx: int, pt1: tuple, pt2: tuple):
        """remove record by given value
        Arguments:
            frame_idx {int} -- record frame index
            pt1 {tuple} -- record (x1, y1)
            pt2 {tuple} -- record (x2, y2)
        """
        current_records = self._get_records_by_frame_idx(frame_idx)
        target_record = None
        for record in current_records:
            src_pt1, src_pt2 = (record['x1'], record['y1']), (record['x2'], record['y2'])
            if src_pt1 == pt1 and src_pt2 == pt2:
                target_record = record
        if target_record:
            target_row_idx = self.records.index(target_record)
            self.records.remove(target_record)
            self.remove_record_from_preview(target_row_idx)

    @pyqtSlot()
    def _goto_previous_record(self):
        rest_records = list(filter(lambda x: x['frame_idx'] < self.render_frame_idx, self.records))
        if not rest_records:
            QMessageBox.information(self, 'Info', 'no previous record', QMessageBox.Ok)
        else:
            self.target_frame_idx = rest_records[-1]['frame_idx']

    @pyqtSlot()
    def _goto_next_record(self):
        rest_records = list(filter(lambda x: x['frame_idx'] > self.render_frame_idx, self.records))
        if not rest_records:
            QMessageBox.information(self, 'Info', 'no next record', QMessageBox.Ok)
        else:
            self.target_frame_idx = rest_records[0]['frame_idx']

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
        """label frame press mouse event
        - Qt.LeftButton: drawing
        - Qt.RightButton: select to delete
        Arguments:
            event {PyQt5.QtGui.QMouseEvent} -- event object
        """
        if self._check_coor_in_frame(event.x(), event.y()) and not self.is_playing_video:
            if event.button() == Qt.LeftButton:
                nrecords = self._get_nrecord_in_current_frame()
                if self.limit_nlabel and nrecords and self.limit_nlabel <= nrecords:
                    self.logger.warning('not available to add a new record (exist=%d, limit=%d)', \
                                        nrecords, self.limit_nlabel)
                else:
                    self.label_frame.is_drawing = True
                    self.label_frame.is_selecting = False
                    self.logger.debug('press mouse at (%d, %d)', event.x(), event.y())
                    self.label_frame.pt1 = (event.x(), event.y())
            elif event.button() == Qt.RightButton:
                closest_record = self._get_closest_record_in_current_frame(event.x(), event.y())
                if closest_record:
                    pt1 = (closest_record['x1'], closest_record['y1'])
                    pt2 = (closest_record['x2'], closest_record['y2'])
                    message = '<b>Do you want to delete the record ?</b><br/><br/> \
                    frame index -\t{} <br/> position -\t{} {}'.format(
                        closest_record['frame_idx'], str(pt1), str(pt2))
                    reply = QMessageBox.question(self, 'Delete Record', message, \
                                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        self._remove_record(closest_record['frame_idx'], pt1, pt2)
                        self.is_force_update = True
                        self.update()

    @pyqtSlot()
    def event_frame_mouse_move(self, event):
        if self.label_frame.is_drawing and self._check_coor_in_frame(event.x(), event.y()):
            self.logger.debug('move mouse at (%d, %d)', event.x(), event.y())
            self.label_frame.pt2 = (event.x(), event.y())
            self.update()
        elif not self.label_frame.is_drawing and not self.is_playing_video:
            closest_record = self._get_closest_record_in_current_frame(event.x(), event.y())
            if closest_record:
                self.label_frame.is_selecting = True
                self.label_frame.select_pt1 = (closest_record['x1'], closest_record['y1'])
                self.label_frame.select_pt2 = (closest_record['x2'], closest_record['y2'])
            else:
                self.label_frame.is_selecting = False
                self.label_frame.select_pt1 = self.label_frame.select_pt2 = None
            self.update()

    @pyqtSlot()
    def event_frame_mouse_release(self, event):
        if self.label_frame.is_drawing:
            self.label_frame.is_drawing = False
            self.logger.debug('release mouse at (%d, %d)', event.x(), event.y())
            if self._check_coor_in_frame(event.x(), event.y()):
                self.label_frame.pt2 = (event.x(), event.y())
            pt1, pt2 = self.label_frame.revise_coor(self.label_frame.pt1, self.label_frame.pt2)
            record = OrderedDict([
                ('timestamp_hms', self._frame_idx_to_hms(self.render_frame_idx)),
                ('timestamp_hmsf', self._frame_idx_to_hmsf(self.render_frame_idx)),
                ('frame_idx', self.render_frame_idx), ('fps', self.video_fps),
                ('frame_height', self.frame_height), ('frame_width', self.frame_width),
                ('scale_height', self.scale_height), ('scale_width', self.scale_width),
                ('x1', pt1[0]), ('y1', pt1[1]), ('x2', pt2[0]), ('y2', pt2[1]),
                ('center_x', (pt1[0]+pt2[0])//2), ('center_y', (pt1[1]+pt2[1])//2)
            ])
            self.records.append(record)
            self.records = sorted(self.records, key=lambda x: x['frame_idx'])
            self.add_record_to_preview(record['timestamp_hms'], \
                                       record['frame_idx'], \
                                       (record['x1'], record['y1']), \
                                       (record['x2'], record['y2']))
            self.label_frame.pt1 = self.label_frame.pt2 = None
            self.is_force_update = True
            self.update()

    @pyqtSlot()
    def event_preview_double_clicked(self):
        row = self.table_preview_records.currentRow()
        frame_idx = int(self.table_preview_records.item(row, 1).text())
        self.target_frame_idx = frame_idx

    def draw_rects(self, frame_idx: int, frame: np.ndarray):
        rest_records = list(filter(lambda x: x['frame_idx'] == frame_idx, self.records))
        if not rest_records:
            return frame
        for record in rest_records:
            pt1, pt2 = (record['x1'], record['y1']), (record['x2'], record['y2'])
            cv2.rectangle(frame, pt1, pt2, self.label_color, self.label_thickness)
        return frame

    def save_file(self):
        """export records to default paths
        - click ok only close message box
        - click close to close PyQt program
        """
        exist_msg = 'File <b>{}</b> exist.<br/><br/>\
                         Do you want to replace?'.format(self.outpath)
        info_msg = 'Save at <b>{}</b><br/>\
                    total records: {}'.format(self.outpath, len(self.records))

        # check the file existense
        exist_reply = QMessageBox.No
        if Path(self.outpath).exists():
            exist_reply = QMessageBox.question(self, 'File Exist', exist_msg, \
                                               QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if not Path(self.outpath).exists() or exist_reply == QMessageBox.Yes:
            df_labels = pd.DataFrame().from_records(self.records)
            df_labels.to_csv(self.outpath, index=False)

        # check if the application is going to close
        reply = QMessageBox.about(self, 'Info', info_msg)
        self.close()
    
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
