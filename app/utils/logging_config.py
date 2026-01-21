"""Logging configuration"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(app):
    """Setup logging for the application"""
    if not app.debug:
        # Create logs directory if it doesn't exist
        log_dir = Path(app.root_path).parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        # Log file path
        log_file = log_dir / 'app.log'
        
        # Create file handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to app logger
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')


def get_logger(name):
    """Get a logger instance"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


