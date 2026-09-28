from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDialog,
    QMenu,
)

import pytest

import backup
import database
import export
import GUI


@pytest.fixture(autouse=True)
def no_modal_dialogs(monkeypatch):
    """未被用例显式打桩的模态弹窗应立即失败，而不是把测试挂死。"""

    def explode(name):
        def _fail(*args, **kwargs):
            raise AssertionError(f"测试中不应弹出 QMessageBox.{name}()")

        return _fail

    for name in ("information", "warning", "critical", "question", "about"):
        monkeypatch.setattr(GUI.QMessageBox, name, explode(name))


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


# =========================
# MainWindow：渲染与统计
# =========================

def make_window():
    return GUI.MainWindow()


def row_of(window, name):
    for row in range(window.table.rowCount()):
        if window.table.item(row, GUI.COL_NAME).text() == name:
            return row
    raise AssertionError(f"表格中没有「{name}」")


def test_startup_lists_every_account(qt_app, gui_db):
    database.insert_account("工资", 5000, "收入", days_ago(3))
    database.insert_account("餐饮", 100, "支出", days_ago(2))

    window = make_window()

    assert window.table.rowCount() == 2


def test_date_query_does_not_recurse(qt_app, gui_db):
    """缺陷 #1 回归：旧 load_statistics 自递归，按日期查询必崩。"""
    database.insert_account("工资", 5000, "收入", days_ago(3))

    window = make_window()
    window.filter_panel.mode_input.setCurrentIndex(1)
    window.filter_panel.day_input.setDate(QDate.currentDate().addDays(-3))
    window.filter_panel.emit_query()

    assert window.table.rowCount() == 1
    assert window.statistics.income_card.amount_label.text() == "¥ 5,000.00"


def test_month_query_does_not_recurse(qt_app, gui_db):
    database.insert_account("工资", 5000, "收入", days_ago(3))

    window = make_window()
    window.filter_panel.mode_input.setCurrentIndex(2)
    window.filter_panel.emit_query()

    assert window.table.rowCount() == 1


def test_range_query_does_not_recurse(qt_app, gui_db):
    database.insert_account("工资", 5000, "收入", days_ago(3))

    window = make_window()
    window.filter_panel.mode_input.setCurrentIndex(3)
    window.filter_panel.start_input.setDate(QDate.currentDate().addDays(-10))
    window.filter_panel.end_input.setDate(QDate.currentDate())
    window.filter_panel.emit_query()

    assert window.table.rowCount() == 1


def test_statistics_match_displayed_rows(qt_app, gui_db):
    """缺陷 #2 回归：统计标签启动时不再恒为 0。"""
    database.insert_account("工资", 8500, "收入", days_ago(5))
    database.insert_account("餐饮", 200, "支出", days_ago(4))
    database.insert_account("购物", 3000, "支出", days_ago(3))

    window = make_window()

    assert window.statistics.income_card.amount_label.text() == "¥ 8,500.00"
    assert window.statistics.expense_card.amount_label.text() == "¥ 3,200.00"
    assert window.statistics.balance_card.amount_label.text() == "¥ 5,300.00"
    assert window.statistics.income_card.count_label.text() == "1 笔"
    assert window.statistics.expense_card.count_label.text() == "2 笔"


def test_filtered_statistics_only_count_matching_rows(qt_app, gui_db):
    database.insert_account("工资", 8500, "收入", days_ago(5))
    database.insert_account("餐饮", 200, "支出", days_ago(4))

    window = make_window()
    window.filter_panel.type_input.setCurrentText("支出")
    window.filter_panel.emit_query()

    assert window.table.rowCount() == 1
    assert window.statistics.income_card.amount_label.text() == "¥ 0.00"
    assert window.statistics.expense_card.amount_label.text() == "¥ 200.00"


def test_keyword_filter_matches_name(qt_app, gui_db):
    database.insert_account("餐饮", 200, "支出", days_ago(4))
    database.insert_account("工资", 8500, "收入", days_ago(5))

    window = make_window()
    window.filter_panel.keyword_input.setText("餐饮")
    window.filter_panel.emit_query()

    assert window.table.rowCount() == 1
    assert window.table.item(0, GUI.COL_NAME).text() == "餐饮"


def test_empty_database_shows_placeholder(qt_app, gui_db):
    window = make_window()

    assert window.table.rowCount() == 0
    assert window.table_stack.currentIndex() == 1
    assert window.statistics.income_card.amount_label.text() == "¥ 0.00"
    assert "共 0 条" in window.statusBar().currentMessage()


def test_placeholder_hides_once_data_exists(qt_app, gui_db):
    database.insert_account("工资", 5000, "收入", days_ago(3))

    window = make_window()

    assert window.table_stack.currentIndex() == 0


def test_reversed_range_keeps_previous_results(qt_app, gui_db, monkeypatch):
    monkeypatch.setattr(
        GUI.QMessageBox, "warning", lambda *args, **kwargs: None
    )
    database.insert_account("工资", 5000, "收入", days_ago(3))

    window = make_window()
    assert window.table.rowCount() == 1

    window.filter_panel.mode_input.setCurrentIndex(3)
    window.filter_panel.start_input.setDate(QDate.currentDate())
    window.filter_panel.end_input.setDate(QDate.currentDate().addDays(-10))
    window.filter_panel.emit_query()

    assert window.table.rowCount() == 1


def test_table_cells_are_not_editable(qt_app, gui_db):
    """缺陷 #7 回归：单元格可编辑但改动不落库，是数据完整性陷阱。"""
    database.insert_account("工资", 5000, "收入", days_ago(3))

    window = make_window()

    assert (
        window.table.editTriggers()
        == QAbstractItemView.EditTrigger.NoEditTriggers
    )

    for column in range(window.table.columnCount()):
        flags = window.table.item(0, column).flags()
        assert not (flags & Qt.ItemFlag.ItemIsEditable)


def test_income_and_expense_rows_are_colored(qt_app, gui_db):
    database.insert_account("工资", 5000, "收入", days_ago(5))
    database.insert_account("餐饮", 200, "支出", days_ago(4))

    window = make_window()

    income_row = row_of(window, "工资")
    expense_row = row_of(window, "餐饮")

    assert (
        window.table.item(income_row, GUI.COL_AMOUNT)
        .foreground().color().name()
        == GUI.INCOME_COLOR
    )
    assert (
        window.table.item(expense_row, GUI.COL_AMOUNT)
        .foreground().color().name()
        == GUI.EXPENSE_COLOR
    )


def test_rows_sorted_by_date_descending(qt_app, gui_db):
    database.insert_account("早", 10, "支出", days_ago(10))
    database.insert_account("晚", 10, "支出", days_ago(1))

    window = make_window()

    assert window.table.item(0, GUI.COL_NAME).text() == "晚"
    assert window.table.item(1, GUI.COL_NAME).text() == "早"


def test_amount_column_sorts_numerically(qt_app, gui_db):
    database.insert_account("小", 9, "支出", days_ago(2))
    database.insert_account("大", 1000, "支出", days_ago(1))

    window = make_window()
    window.table.sortItems(GUI.COL_AMOUNT, Qt.SortOrder.AscendingOrder)

    assert window.table.item(0, GUI.COL_NAME).text() == "小"
    assert window.table.item(1, GUI.COL_NAME).text() == "大"


def test_selected_account_looks_up_by_id_not_row(qt_app, gui_db, monkeypatch):
    monkeypatch.setattr(
        GUI.QMessageBox, "warning", lambda *args, **kwargs: None
    )
    database.insert_account("小", 9, "支出", days_ago(2))
    database.insert_account("大", 1000, "支出", days_ago(1))

    window = make_window()
    window.table.sortItems(GUI.COL_AMOUNT, Qt.SortOrder.AscendingOrder)
    window.table.setCurrentCell(0, 0)

    assert window._selected_account().name == "小"


def test_selected_account_warns_when_nothing_selected(qt_app, gui_db, monkeypatch):
    calls = []
    monkeypatch.setattr(
        GUI.QMessageBox,
        "warning",
        lambda *args, **kwargs: calls.append(args),
    )
    database.insert_account("工资", 5000, "收入", days_ago(3))

    window = make_window()
    window.table.clearSelection()
    window.table.setCurrentCell(-1, -1)

    assert window._selected_account() is None
    assert len(calls) == 1


# =========================
# MainWindow：增删改与菜单
# =========================

def stub_question(monkeypatch, answer):
    monkeypatch.setattr(
        GUI.QMessageBox, "question", lambda *args, **kwargs: answer
    )


def test_delete_removes_row_and_refreshes_statistics(qt_app, gui_db, monkeypatch):
    stub_question(monkeypatch, GUI.QMessageBox.StandardButton.Yes)
    database.insert_account("工资", 5000, "收入", days_ago(5))
    database.insert_account("餐饮", 100, "支出", days_ago(4))

    window = make_window()
    window.table.setCurrentCell(row_of(window, "餐饮"), 0)

    window.delete_account()

    assert window.table.rowCount() == 1
    assert len(database.get_accounts()) == 1
    assert window.statistics.expense_card.amount_label.text() == "¥ 0.00"
    assert window.statistics.income_card.amount_label.text() == "¥ 5,000.00"


def test_delete_aborts_when_user_declines(qt_app, gui_db, monkeypatch):
    stub_question(monkeypatch, GUI.QMessageBox.StandardButton.No)
    database.insert_account("餐饮", 100, "支出", days_ago(4))

    window = make_window()
    window.table.setCurrentCell(row_of(window, "餐饮"), 0)

    window.delete_account()

    assert window.table.rowCount() == 1
    assert len(database.get_accounts()) == 1


def test_delete_without_selection_changes_nothing(qt_app, gui_db, monkeypatch):
    warnings = []
    monkeypatch.setattr(
        GUI.QMessageBox,
        "warning",
        lambda *args, **kwargs: warnings.append(args),
    )
    database.insert_account("餐饮", 100, "支出", days_ago(4))

    window = make_window()
    window.table.clearSelection()
    window.table.setCurrentCell(-1, -1)

    window.delete_account()

    assert len(database.get_accounts()) == 1
    assert len(warnings) == 1


def test_refresh_keeps_active_filter_after_delete(qt_app, gui_db, monkeypatch):
    stub_question(monkeypatch, GUI.QMessageBox.StandardButton.Yes)
    database.insert_account("餐饮", 100, "支出", days_ago(4))
    database.insert_account("餐饮晚", 50, "支出", days_ago(3))
    database.insert_account("工资", 5000, "收入", days_ago(5))

    window = make_window()
    window.filter_panel.keyword_input.setText("餐饮")
    window.filter_panel.emit_query()
    assert window.table.rowCount() == 2

    window.table.setCurrentCell(row_of(window, "餐饮晚"), 0)
    window.delete_account()

    assert window.table.rowCount() == 1
    assert window.filter_panel.keyword_input.text() == "餐饮"


def test_add_account_dialog_writes_through(qt_app, gui_db, monkeypatch):
    """用桩替换 exec()，模拟用户在对话框里填好并点保存。"""
    def fake_exec(dialog):
        dialog.name_input.setText("工资")
        dialog.price_input.setText("5000")
        dialog.type_input.setCurrentText("收入")
        dialog.save_account()
        return dialog.result()

    monkeypatch.setattr(GUI.AccountDialog, "exec", fake_exec)

    window = make_window()
    window.add_account()

    assert len(database.get_accounts()) == 1
    assert window.table.rowCount() == 1
    assert window.statistics.income_card.amount_label.text() == "¥ 5,000.00"


def test_update_account_dialog_writes_through(qt_app, gui_db, monkeypatch):
    database.insert_account("餐饮", 100, "支出", days_ago(4))

    def fake_exec(dialog):
        dialog.price_input.setText("250")
        dialog.save_account()
        return dialog.result()

    monkeypatch.setattr(GUI.AccountDialog, "exec", fake_exec)

    window = make_window()
    window.table.setCurrentCell(row_of(window, "餐饮"), 0)
    window.update_account()

    accounts = database.get_accounts()
    assert accounts[0].price == 250
    assert window.statistics.expense_card.amount_label.text() == "¥ 250.00"


def test_update_account_opens_prefilled_dialog(qt_app, gui_db, monkeypatch):
    database.insert_account("餐饮", 100, "支出", days_ago(4))

    captured = {}

    def fake_exec(dialog):
        captured["mode"] = dialog.mode
        captured["name"] = dialog.name_input.text()
        return 0

    monkeypatch.setattr(GUI.AccountDialog, "exec", fake_exec)

    window = make_window()
    window.table.setCurrentCell(row_of(window, "餐饮"), 0)
    window.update_account()

    assert captured == {"mode": "edit", "name": "餐饮"}


def test_double_click_opens_editor(qt_app, gui_db, monkeypatch):
    database.insert_account("餐饮", 100, "支出", days_ago(4))

    captured = {}
    monkeypatch.setattr(
        GUI.AccountDialog,
        "exec",
        lambda dialog: captured.update(mode=dialog.mode) or 0,
    )

    window = make_window()
    row = row_of(window, "餐饮")
    window.table.setCurrentCell(row, 0)
    item = window.table.item(row, GUI.COL_NAME)
    window.table.itemDoubleClicked.emit(item)

    assert captured["mode"] == "edit"


def test_menu_and_toolbar_expose_all_actions(qt_app, gui_db):
    window = make_window()

    menu_titles = [
        action.text()
        for menu in window.menuBar().findChildren(QMenu)
        for action in menu.actions()
    ]

    for expected in ["导出为 CSV", "退出", "添加账单", "修改账单", "删除账单",
                     "备份数据库", "恢复数据库", "关于"]:
        assert expected in menu_titles


def test_about_dialog_opens(qt_app, gui_db, monkeypatch):
    captured = []
    monkeypatch.setattr(
        GUI.QMessageBox, "about", lambda *args, **kwargs: captured.append(args)
    )

    window = make_window()
    window.show_about()

    assert len(captured) == 1


def test_export_csv_writes_file(qt_app, gui_db, monkeypatch, tmp_path):
    # GUI.export_csv 用 GUI 自己的 EXPORT_DIR 做存在性检查，
    # 真正的写文件发生在 export 模块里 —— 两处都要指到 tmp_path。
    monkeypatch.setattr(GUI, "EXPORT_DIR", str(tmp_path))
    monkeypatch.setattr(export, "EXPORT_DIR", str(tmp_path))
    monkeypatch.setattr(
        GUI.QMessageBox, "information", lambda *args, **kwargs: None
    )
    database.insert_account("工资", 5000, "收入", days_ago(3))

    window = make_window()
    window.export_csv()

    exported = (tmp_path / "accounts.csv").read_text(encoding="utf-8-sig")
    assert "工资" in exported


def test_backup_writes_file(qt_app, gui_db, monkeypatch, tmp_path):
    monkeypatch.setattr(GUI, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "DATABASE", database.DATABASE)
    monkeypatch.setattr(
        GUI.QMessageBox, "information", lambda *args, **kwargs: None
    )
    database.insert_account("工资", 5000, "收入", days_ago(3))

    window = make_window()
    window.backup_db()

    assert (tmp_path / "accounts_backup.db").exists()


def test_restore_warns_when_no_backup_exists(qt_app, gui_db, monkeypatch, tmp_path):
    monkeypatch.setattr(GUI, "BACKUP_DIR", str(tmp_path))
    warnings = []
    monkeypatch.setattr(
        GUI.QMessageBox,
        "warning",
        lambda *args, **kwargs: warnings.append(args),
    )

    window = make_window()
    window.restore_db()

    assert len(warnings) == 1


def test_restore_never_blocks_on_stdin(qt_app, gui_db, monkeypatch, tmp_path):
    """恢复备份若触发 input()，GUI 会挂死。"""
    monkeypatch.setattr(GUI, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "DATABASE", str(tmp_path / "live.db"))

    stub_question(monkeypatch, GUI.QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(
        GUI.QMessageBox, "information", lambda *args, **kwargs: None
    )

    def explode(*args, **kwargs):
        raise AssertionError("恢复流程不应调用 input()")

    monkeypatch.setattr("builtins.input", explode)

    (tmp_path / "accounts_backup.db").write_bytes(b"backup-payload")

    window = make_window()
    window.restore_db()

    assert (tmp_path / "live.db").read_bytes() == b"backup-payload"
