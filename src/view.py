import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPainter, QPalette, QPen, QPixmap, QColor
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QGridLayout,
                             QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                             QSlider, QStyle, QVBoxLayout, QWidget)


class VideoFrameViewer(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.logger = logging.getLogger(__name__)
        self.is_drawing = False
        self.pt1 = self.pt2 = None

        self.pen_color = QColor(0, 0, 0)
        self.pen_thickness = 1
        self.pen_style = Qt.SolidLine

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_drawing:
            painter = QPainter()
            painter.begin(self)
            pen = QPen(self.pen_color, self.pen_thickness, self.pen_style)
            painter.setPen(pen)
            pt1_x, pt1_y = self.pt1
            width = self.pt2[0] - pt1_x
            height = self.pt2[1] - pt1_y
            painter.drawRect(pt1_x, pt1_y, width, height)
            painter.end()

class VideoAppViewer(QWidget):
    def __init__(self, parent=None, title='PyQt5 video labeling viewer'):
        """init

        Arguments:
            QWidget {[type]} -- default qt widget

        Keyword Arguments:
            title {str} -- window title (default: {'PyQt5 video labeling viewer'})
        """

        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.title = title
        self.desktop = QDesktopWidget()
        self.screen = self.desktop.availableGeometry()

        # init window - init and set default config about window
        self.setWindowTitle(self.title)

        # init widgets - init and set default config about widgets
        # grid_root
        #   vbox_panels: video viewer
        #       label_frame
        #       hbox_video_slider
        #           btn_play_video
        #   vbox_option: show static message or set the configuration

        self.grid_root = QGridLayout()
        self.vbox_panels = QVBoxLayout()
        self.vbox_option = QVBoxLayout()
        self.hbox_video_slider = QHBoxLayout()
        self.setLayout(self.grid_root)

        # vbox_panels
        self.label_frame = VideoFrameViewer(self)
        self.label_frame.setAlignment(Qt.AlignCenter)
        self.btn_play_video = QPushButton()
        self.btn_play_video.setEnabled(True)
        self.btn_play_video.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.slider_video = QSlider(Qt.Horizontal)
        self.slider_video.setRange(0, 0)
        self.label_video_status = QLabel()
        self.label_video_status.setAlignment(Qt.AlignCenter)

        # set position
        self.hbox_video_slider.setContentsMargins(0, 0, 0, 0)
        self.hbox_video_slider.addWidget(self.btn_play_video)
        self.hbox_video_slider.addWidget(self.slider_video)
        self.vbox_panels.addWidget(self.label_frame)
        self.vbox_panels.addLayout(self.hbox_video_slider)
        self.vbox_panels.addWidget(self.label_video_status)
        self.grid_root.addLayout(self.vbox_panels, 0, 0)
        self.grid_root.addLayout(self.vbox_option, 0, 1)
