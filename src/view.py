import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QStandardItemModel
from PyQt5.QtWidgets import (QDesktopWidget, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QPushButton, QSlider, QStyle,
                             QTreeView, QVBoxLayout, QWidget)


class VideoFrameViewer(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.logger = logging.getLogger(__name__)
        self.is_drawing = False
        self.is_selecting = False
        self.pt1 = self.pt2 = None
        self.select_pt1 = self.select_pt2 = None

        # case: draw config
        self.draw_color = QColor(0, 0, 0)
        self.draw_thickness = 1
        self.draw_style = Qt.SolidLine

        # case: select config
        self.select_color = QColor(0, 0, 0)
        self.select_thickness = 2
        self.select_style = Qt.SolidLine

    def _draw_rect(self, pt1: tuple, pt2: tuple, pen: QPen):
        painter = QPainter()
        painter.begin(self)
        painter.setPen(pen)
        pt1_x, pt1_y, pt2_x, pt2_y = pt1[0], pt1[1], pt2[0], pt2[1]
        width, height = (pt2_x - pt1_x), (pt2_y - pt1_y)
        painter.drawRect(pt1_x, pt1_y, width, height)
        painter.end()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_drawing and self.pt1 and self.pt2:
            pen = QPen(self.draw_color, self.draw_thickness, self.draw_style)
            self._draw_rect(self.pt1, self.pt2, pen)

        elif not self.is_drawing and self.select_pt1 and self.select_pt2:
            pen = QPen(self.select_color, self.select_thickness, self.select_style)
            self._draw_rect(self.select_pt1, self.select_pt2, pen)

class VideoAppViewer(QWidget):
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
        self.font_header = QFont()
        self.font_header.setBold(True)

        # init window - init and set default config about window
        self.setWindowTitle(self.title)

        # grid: root layout
        self.grid_root = QGridLayout()
        self.setLayout(self.grid_root)
        vbox_panels = QVBoxLayout()
        vbox_option = QVBoxLayout()
        self.grid_root.addLayout(vbox_panels, 0, 0)
        self.grid_root.addLayout(vbox_option, 0, 1)

        # vbox_panel/label_frame: show frame image
        self.label_frame = VideoFrameViewer(self)
        self.label_frame.setAlignment(Qt.AlignCenter)
        self.label_frame.setMouseTracking(True)
        vbox_panels.addWidget(self.label_frame)

        # vbox_panel/hbox_video: show process about video
        hbox_video_slider = QHBoxLayout()
        self.btn_play_video = QPushButton()
        self.btn_play_video.setEnabled(True)
        self.btn_play_video.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.slider_video = QSlider(Qt.Horizontal)
        self.slider_video.setRange(0, 0)
        hbox_video_slider.addWidget(self.btn_play_video)
        hbox_video_slider.addWidget(self.slider_video)
        vbox_panels.addLayout(hbox_video_slider)

        # vbox_panel/label_video_status: show frame index or exception msg
        self.label_video_status = QLabel()
        self.label_video_status.setAlignment(Qt.AlignCenter)
        vbox_panels.addWidget(self.label_video_status)

        # vbox_option/group_video_info: show video static info
        self.group_video_info = QGroupBox('Video Information')
        sub_grid = QGridLayout()
        label_path = self._get_header_label('Path')
        label_shape = self._get_header_label('Shape')
        label_fps = self._get_header_label('FPS')
        self.label_video_path = QLabel()
        self.label_video_path.setAlignment(Qt.AlignLeft)
        self.label_video_path.setWordWrap(True)
        self.label_video_shape = QLabel()
        self.label_video_shape.setAlignment(Qt.AlignLeft)
        self.label_video_fps = QLabel()
        self.label_video_fps.setAlignment(Qt.AlignLeft)
        sub_grid.addWidget(label_path, 0, 0)
        sub_grid.addWidget(self.label_video_path, 0, 1)
        sub_grid.addWidget(label_shape, 1, 0)
        sub_grid.addWidget(self.label_video_shape, 1, 1)
        sub_grid.addWidget(label_fps, 2, 0)
        sub_grid.addWidget(self.label_video_fps, 2, 1)
        self.group_video_info.setLayout(sub_grid)
        self.group_video_info.contentsMargins()
        self.group_video_info.setAlignment(Qt.AlignTop)
        vbox_option.addWidget(self.group_video_info)

        # vbox_option/table_preview_record: preview the summary of records
        self.tree_preview_records = QTreeView()
        self.tree_preview_records.setRootIsDecorated(False)
        self.tree_preview_records.setAlternatingRowColors(True)
        self.model_preview_records = self._get_preview_model(self)
        self.tree_preview_records.setModel(self.model_preview_records)
        vbox_option.addWidget(self.tree_preview_records)
        vbox_option.addStretch(1)

        # vbox_option/hbox_jump_records: jump to next or previous record
        hbox_jump_records = QHBoxLayout()
        self.btn_previous_record = QPushButton('<< Previous Record')
        self.btn_next_record = QPushButton('Next Record >>')
        hbox_jump_records.addWidget(self.btn_previous_record)
        hbox_jump_records.addWidget(self.btn_next_record)
        vbox_option.addLayout(hbox_jump_records)

        # vbox_option/btn_export: export records
        self.btn_export_records = QPushButton('Export')
        vbox_option.addWidget(self.btn_export_records)

    def _get_header_label(self, text: str = ''):
        label = QLabel(text)
        label.setFont(self.font_header)
        label.setAlignment(Qt.AlignLeft)
        return label

    def _get_preview_model(self, parent):
        model = QStandardItemModel(0, 3, parent)
        model.setHeaderData(0, Qt.Horizontal, '#frame')
        model.setHeaderData(1, Qt.Horizontal, 'pt1')
        model.setHeaderData(2, Qt.Horizontal, 'pt2')
        return model
    
    def add_record_to_treeview(self, frame_idx: int, pt1: tuple, pt2: tuple):
        insert_row_index = self.model_preview_records.rowCount()
        self.model_preview_records.insertRow(insert_row_index)
        col1_index = self.model_preview_records.index(insert_row_index, 0)
        col2_index = self.model_preview_records.index(insert_row_index, 1)
        col3_index = self.model_preview_records.index(insert_row_index, 2)
        self.model_preview_records.setData(col1_index, frame_idx)
        self.model_preview_records.setData(col2_index, str(pt1))
        self.model_preview_records.setData(col3_index, str(pt2))
