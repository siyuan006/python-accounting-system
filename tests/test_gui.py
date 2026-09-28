from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QDialog

import database
import GUI


def days_ago(days):
    """相对今天取日期，保证测试在任何一天运行都成立。"""
    return QDate.currentDate().addDays(-days).toString("yyyy-MM-dd")


def today():
    return QDate.currentDate().toString("yyyy-MM-dd")


# =========================
# AccountDialog
# =========================

def test_dialog_rejects_empty_name(qt_app):
    dialog = GUI.AccountDialog("add")
    dialog.name_input.setText("   ")

    try:
        dialog.read_form()
    except GUI.ValidationError as error:
        assert "名称" in error.message
        assert error.widget is dialog.name_input
    else:
        raise AssertionError("空名称应当被拒绝")


def test_dialog_rejects_non_numeric_price(qt_app):
    dialog = GUI.AccountDialog("add")
    dialog.name_input.setText("早餐")
    dialog.price_input.setText("abc")

    try:
        dialog.read_form()
    except GUI.ValidationError as error:
        assert "数字" in error.message
    else:
        raise AssertionError("非数字金额应当被拒绝")


def test_dialog_rejects_negative_price(qt_app):
    dialog = GUI.AccountDialog("add")
    dialog.name_input.setText("早餐")
    dialog.price_input.setText("-5")

    try:
        dialog.read_form()
    except GUI.ValidationError as error:
        assert "大于 0" in error.message
    else:
        raise AssertionError("负数金额应当被拒绝")


def test_dialog_rejects_future_date(qt_app):
    dialog = GUI.AccountDialog("add")
    dialog.name_input.setText("早餐")
    dialog.price_input.setText("15")
    dialog.date_input.setDate(QDate.currentDate().addDays(1))

    try:
        dialog.read_form()
    except GUI.ValidationError as error:
        assert "未来" in error.message
        assert error.widget is dialog.date_input
    else:
        raise AssertionError("未来日期应当被拒绝")


def test_dialog_reads_trimmed_name_and_price(qt_app):
    dialog = GUI.AccountDialog("add")
    dialog.name_input.setText("  早餐  ")
    dialog.price_input.setText(" 15.5 ")
    dialog.type_input.setCurrentText("支出")

    assert dialog.read_form() == ("早餐", 15.5, "支出", today())


def test_dialog_saves_new_account(qt_app, gui_db):
    dialog = GUI.AccountDialog("add")
    dialog.name_input.setText("早餐")
    dialog.price_input.setText("15.5")
    dialog.type_input.setCurrentText("支出")

    dialog.save_account()

    assert dialog.result() == QDialog.DialogCode.Accepted

    accounts = database.get_accounts()
    assert len(accounts) == 1
    assert accounts[0].name == "早餐"
    assert accounts[0].price == 15.5
    assert accounts[0].type == "支出"


def test_dialog_prefills_existing_account(qt_app, gui_db):
    database.insert_account("早餐", 15, "支出", days_ago(3))
    account = database.get_accounts()[0]

    dialog = GUI.AccountDialog("edit", account)

    assert dialog.windowTitle() == "修改账单"
    assert dialog.name_input.text() == "早餐"
    assert dialog.price_input.text() == "15"
    assert dialog.type_input.currentText() == "支出"
    assert dialog.date_input.date().toString("yyyy-MM-dd") == days_ago(3)


def test_dialog_updates_existing_account(qt_app, gui_db):
    database.insert_account("早餐", 15, "支出", days_ago(3))
    account = database.get_accounts()[0]

    dialog = GUI.AccountDialog("edit", account)
    dialog.price_input.setText("20")
    dialog.save_account()

    accounts = database.get_accounts()
    assert len(accounts) == 1
    assert accounts[0].price == 20
