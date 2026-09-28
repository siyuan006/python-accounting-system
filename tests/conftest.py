import os
import sys

import pytest

# 必须在导入 PyQt6 之前设置，否则会尝试连接真实显示器。
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

import database  # noqa: E402
from config import DATABASE  # noqa: E402


@pytest.fixture(scope="session")
def qt_app():
    """整个测试会话共用一个 QApplication。"""
    return QApplication.instance() or QApplication(sys.argv[:1])


@pytest.fixture
def gui_db(tmp_path, qt_app):
    """把 database.DATABASE 指向临时库，绝不碰真实账单数据。"""
    database.DATABASE = str(tmp_path / "test_gui.db")
    database.create_table()

    yield

    database.DATABASE = DATABASE
