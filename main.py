import argparse
import logging
import sys

from PyQt5.QtWidgets import QApplication

from src.app import VideoApp
from src.utils import func_profile, log_handler


def argparser():
    """parse arguments from terminal"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--video', dest='video')
    return parser

@func_profile
def main(args: argparse.Namespace):
    """an interface to activate pyqt5 app"""
    logger = logging.getLogger(__name__)
    log_handler(logger)
    logger.info(args)

    app = QApplication(sys.argv)
    video_app = VideoApp(args.video)
    try:
        app.exec()
    except Exception as e:
        logger.exception(e)

if __name__ == '__main__':
    main(argparser().parse_args())
