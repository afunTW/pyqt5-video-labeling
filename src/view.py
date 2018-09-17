import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QPixmap
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QGridLayout,
                             QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                             QSlider, QStyle, QVBoxLayout, QWidget)


class VideoViewer(QWidget):
    def __init__(self, title='PyQt5 video labeling viewer'):
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
        self.label_frame = QLabel(self)
        self.btn_play_video = QPushButton()
        self.btn_play_video.setEnabled(True)
        self.btn_play_video.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.slider_video = QSlider(Qt.Horizontal)
        self.slider_video.setRange(0, 0)
        self.label_video_err = QLabel()

        # set position
        self.hbox_video_slider.setContentsMargins(0, 0, 0, 0)
        self.hbox_video_slider.addWidget(self.btn_play_video)
        self.hbox_video_slider.addWidget(self.slider_video)
        self.vbox_panels.addWidget(self.label_frame)
        self.vbox_panels.addLayout(self.hbox_video_slider)
        self.vbox_panels.addWidget(self.label_video_err)
        self.grid_root.addLayout(self.vbox_panels, 0, 0)
        self.grid_root.addLayout(self.vbox_option, 0, 1)
