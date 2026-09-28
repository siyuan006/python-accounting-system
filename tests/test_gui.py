from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QDateEdit, QDialog

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


# =========================
# StatisticsBar
# =========================

def test_statistics_bar_starts_at_zero(qt_app):
    bar = GUI.StatisticsBar()

    assert bar.income_card.amount_label.text() == "¥ 0.00"
    assert bar.expense_card.amount_label.text() == "¥ 0.00"
    assert bar.balance_card.amount_label.text() == "¥ 0.00"


def test_statistics_bar_formats_amounts_with_thousands_separator(qt_app):
    bar = GUI.StatisticsBar()
    bar.set_stats(8500.0, 3200.0, 3, 7)

    assert bar.income_card.amount_label.text() == "¥ 8,500.00"
    assert bar.income_card.count_label.text() == "3 笔"
    assert bar.expense_card.amount_label.text() == "¥ 3,200.00"
    assert bar.expense_card.count_label.text() == "7 笔"
    assert bar.balance_card.amount_label.text() == "¥ 5,300.00"
    assert bar.balance_card.count_label.text() == "共 10 笔"


def test_statistics_bar_negative_balance_uses_expense_color(qt_app):
    bar = GUI.StatisticsBar()
    bar.set_stats(100.0, 400.0, 1, 1)

    assert bar.balance_card.amount_label.text() == "¥ -300.00"
    assert GUI.EXPENSE_COLOR in bar.balance_card.amount_label.styleSheet()


def test_statistics_bar_positive_balance_uses_income_color(qt_app):
    bar = GUI.StatisticsBar()
    bar.set_stats(400.0, 100.0, 1, 1)

    assert GUI.INCOME_COLOR in bar.balance_card.amount_label.styleSheet()


# =========================
# Query
# =========================

def test_query_all_mode_passes_no_filters():
    kwargs = GUI.Query(mode="全部账单").to_search_kwargs()

    assert kwargs["keyword"] is None
    assert kwargs["account_type"] is None
    assert "account_month" not in kwargs
    assert "start_date" not in kwargs


def test_query_date_mode_becomes_single_day_range():
    kwargs = GUI.Query(mode="按日期", date="2026-09-20").to_search_kwargs()

    assert kwargs["start_date"] == "2026-09-20"
    assert kwargs["end_date"] == "2026-09-20"
    assert "account_month" not in kwargs


def test_query_month_mode_uses_account_month():
    kwargs = GUI.Query(mode="按月份", month="2026-09").to_search_kwargs()

    assert kwargs["account_month"] == "2026-09"
    assert "start_date" not in kwargs


def test_query_range_mode_uses_both_bounds():
    kwargs = GUI.Query(
        mode="按日期范围",
        start_date="2026-09-01",
        end_date="2026-09-30",
    ).to_search_kwargs()

    assert kwargs["start_date"] == "2026-09-01"
    assert kwargs["end_date"] == "2026-09-30"


def test_query_keeps_keyword_and_type_across_modes():
    kwargs = GUI.Query(
        mode="按月份", month="2026-09", keyword="餐饮", account_type="支出"
    ).to_search_kwargs()

    assert kwargs["keyword"] == "餐饮"
    assert kwargs["account_type"] == "支出"
    assert kwargs["account_month"] == "2026-09"


def test_query_detects_reversed_range():
    assert GUI.Query(
        mode="按日期范围",
        start_date="2026-09-20",
        end_date="2026-09-01",
    ).is_range_reversed is True

    assert GUI.Query(
        mode="按日期范围",
        start_date="2026-09-01",
        end_date="2026-09-20",
    ).is_range_reversed is False


def test_query_ignores_reversed_dates_outside_range_mode():
    assert GUI.Query(
        mode="按月份",
        start_date="2026-09-20",
        end_date="2026-09-01",
    ).is_range_reversed is False


# =========================
# FilterPanel
# =========================

def test_filter_panel_defaults_to_all_accounts(qt_app):
    panel = GUI.FilterPanel()

    assert panel.mode_input.currentText() == "全部账单"
    assert panel.date_stack.currentIndex() == 0
    assert panel.build_query().mode == "全部账单"


def test_filter_panel_switches_visible_date_controls(qt_app):
    panel = GUI.FilterPanel()

    for index in (1, 2, 3):
        panel.mode_input.setCurrentIndex(index)
        assert panel.date_stack.currentIndex() == index


def test_filter_panel_shows_both_bounds_in_range_mode(qt_app):
    panel = GUI.FilterPanel()
    panel.mode_input.setCurrentIndex(3)

    page = panel.date_stack.currentWidget()
    editors = page.findChildren(QDateEdit)

    assert panel.start_input in editors
    assert panel.end_input in editors


def test_filter_panel_emits_query_with_keyword(qt_app):
    panel = GUI.FilterPanel()
    received = []
    panel.queryRequested.connect(received.append)

    panel.keyword_input.setText("餐饮")
    panel.search_button.click()

    assert len(received) == 1
    assert received[0].keyword == "餐饮"


def test_filter_panel_maps_type_selection(qt_app):
    panel = GUI.FilterPanel()

    assert panel.build_query().account_type is None

    panel.type_input.setCurrentText("支出")
    assert panel.build_query().account_type == "支出"


def test_filter_panel_reset_restores_defaults_and_emits(qt_app):
    panel = GUI.FilterPanel()
    received = []
    panel.queryRequested.connect(received.append)

    panel.mode_input.setCurrentIndex(3)
    panel.keyword_input.setText("餐饮")
    panel.type_input.setCurrentText("支出")

    panel.reset()

    query = received[-1]
    assert query.mode == "全部账单"
    assert query.keyword == ""
    assert query.account_type is None
    assert panel.keyword_input.text() == ""
