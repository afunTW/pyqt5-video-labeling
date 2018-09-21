import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (QAbstractItemView, QDesktopWidget, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                             QPushButton, QSlider, QStyle, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)


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

    def revise_coor(self, pt1: tuple, pt2: tuple):
        revise_pt1 = (min(pt1[0], pt2[0]), min(pt1[1], pt2[1]))
        revise_pt2 = (max(pt1[0], pt2[0]), max(pt1[1], pt2[1]))
        return (revise_pt1, revise_pt2)

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
            pt1, pt2 = self.revise_coor(self.pt1, self.pt2)
            self._draw_rect(pt1, pt2, pen)

        elif not self.is_drawing and self.select_pt1 and self.select_pt2:
            pen = QPen(self.select_color, self.select_thickness, self.select_style)
            pt1, pt2 = self.revise_coor(self.select_pt1, self.select_pt2)
            self._draw_rect(pt1, pt2, pen)

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
        self.table_preview_records = self._get_preview_table(self)
        vbox_option.addWidget(self.table_preview_records)

        # self.tree_preview_records = QTreeView()
        # self.tree_preview_records.setRootIsDecorated(False)
        # self.tree_preview_records.setAlternatingRowColors(True)
        # self.model_preview_records = self._get_preview_model(self)
        # self.tree_preview_records.setModel(self.model_preview_records)
        # self.tree_preview_records.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # vbox_option.addWidget(self.tree_preview_records)

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
    
    def _get_preview_table(self, parent):
        table = QTableWidget(parent=parent)
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(['timestamp', 'frame', 'pt1', 'pt2'])
        table.setSortingEnabled(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        return table
    
    def add_record_to_preview(self, timestamp: str, frame_idx: int, pt1: tuple, pt2: tuple):
        self.table_preview_records.insertRow(0)
        self.table_preview_records.setItem(0, 0, QTableWidgetItem(timestamp))
        self.table_preview_records.setItem(0, 1, QTableWidgetItem(str(frame_idx)))
        self.table_preview_records.setItem(0, 2, QTableWidgetItem(str(pt1)))
        self.table_preview_records.setItem(0, 3, QTableWidgetItem(str(pt2)))
        self.table_preview_records.sortByColumn(0, Qt.AscendingOrder)
    
    def remove_record_from_preview(self, row_idx: int):
        self.table_preview_records.removeRow(row_idx)
