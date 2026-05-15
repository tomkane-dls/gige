"""
GigE camera acquisition script.

Usage:
    uv run gige config.yaml
    uv run gige --help
"""
import argparse
import logging
import os

import yaml

from gige.camera import Gige1Camera

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load camera configuration from a YAML file."""

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    logger.info("Loaded config from %s", config_path)

    required_keys = [
        "base_pv", "folder_path", "file_no", "acquire_time", "num_images",
        "width", "height", "x_start", "y_start", "image_mode", "data_type",
        "file_template", "poll_interval", "connection_timeout",
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {', '.join(missing)}")

    return config


def main():
    parser = argparse.ArgumentParser(
        description="GigE camera tiff acquisition",
        epilog=(
            "All parameters are read from the yaml config file. "
            "See config.yaml for an example with descriptions of each field."
        ),
    )
    parser.add_argument(
        "config",
        help="Path to YAML configuration file (e.g. config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging for detailed caput/caget output",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    cfg = load_config(args.config)

    os.makedirs(cfg["folder_path"], exist_ok=True)
    logger.info("Output directory ready: %s", cfg["folder_path"])

    camera = Gige1Camera(
        base_pv=cfg["base_pv"],
        folder_path=cfg["folder_path"],
        file_no=cfg["file_no"],
        acquire_time=cfg["acquire_time"],
        num_images=cfg["num_images"],
        width=cfg["width"],
        height=cfg["height"],
        x_start=cfg["x_start"],
        y_start=cfg["y_start"],
        image_mode=cfg["image_mode"],
        data_type=cfg["data_type"],
        file_template=cfg["file_template"],
        poll_interval=cfg["poll_interval"],
    )

    if not camera.check_connection(timeout=cfg["connection_timeout"]):
        logger.error("Cannot reach camera — aborting.")
        raise SystemExit(1)

    camera.acquire()
