import argparse
import logging
import sys
from pathlib import Path

import yaml
from PyQt5.QtWidgets import QApplication

from src.app import VideoApp
from src.utils import func_profile, log_handler

CONFIG_FILE = str(Path(__file__).resolve().parents[0] / 'config.yaml')

def argparser():
    """parse arguments from terminal"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--video', dest='video')
    parser.add_argument('-c', '--config', dest='config', default=CONFIG_FILE)
    return parser

@func_profile
def main(args: argparse.Namespace):
    """an interface to activate pyqt5 app"""
    logger = logging.getLogger(__name__)
    log_handler(logger)
    logger.info(args)
    with open(args.config, 'r') as config_file:
        config = yaml.load(config_file)

    video_path = Path(args.video)
    output_path = Path('outputs')
    if not output_path.exists():
        output_path.mkdir(parents=True)
    label_path = output_path / '{}_label.csv'.format(video_path.stem)

    app = QApplication(sys.argv)
    video_app = VideoApp(args.video, str(label_path), **config)
    try:
        log_handler(video_app.logger)
        app.exec()
    except Exception as e:
        logger.exception(e)

if __name__ == '__main__':
    main(argparser().parse_args())
