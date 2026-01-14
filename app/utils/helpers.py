"""Helper utility functions"""
import os
import socket
from datetime import datetime
from werkzeug.utils import secure_filename
from app.config import Config


def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def get_hostname():
    """Get current hostname"""
    return socket.gethostname()


def get_current_timestamp():
    """Get current timestamp as formatted string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def secure_filepath(filename):
    """Get secure filepath for uploads"""
    return os.path.join(Config.UPLOAD_FOLDER, secure_filename(filename))

