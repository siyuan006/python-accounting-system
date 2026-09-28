"""PyQt6 桌面记账界面。"""

import os
import sys

from dataclasses import dataclass

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

import database
from backup import backup_database, restore_database
from config import BACKUP_DIR, EXPORT_DIR
from database import create_table
from export import export_accounts

INCOME_COLOR = "#1a7f37"
EXPENSE_COLOR = "#c0392b"

COL_ID, COL_NAME, COL_AMOUNT, COL_TYPE, COL_DATE = range(5)
HEADERS = ["ID", "名称", "金额", "类型", "日期"]

TYPE_FILTER_ALL = "全部"

STYLE_SHEET = """
QMainWindow, QDialog {
    background: #f5f6f8;
}
QWidget#StatCard {
    background: #ffffff;
    border: 1px solid #e3e6ea;
    border-radius: 10px;
}
QLabel#StatTitle {
    color: #6b7280;
    font-size: 12px;
}
QLabel#StatCount {
    color: #9aa1ab;
    font-size: 11px;
}
QLabel#EmptyHint {
    color: #9aa1ab;
    font-size: 14px;
}
QTableWidget {
    background: #ffffff;
    alternate-background-color: #fafbfc;
    border: 1px solid #e3e6ea;
    gridline-color: #eef0f3;
}
QTableWidget::item:selected {
    background: #dce7ff;
    color: #111827;
}
QHeaderView::section {
    background: #fafbfc;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #e3e6ea;
    font-weight: 600;
}
QLineEdit, QComboBox, QDateEdit {
    background: #ffffff;
    border: 1px solid #d5d9df;
    border-radius: 6px;
    padding: 4px 6px;
}
QPushButton, QToolButton {
    background: #ffffff;
    border: 1px solid #d5d9df;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover, QToolButton:hover {
    background: #f0f2f5;
}
QPushButton#PrimaryButton {
    background: #2f6fed;
    color: #ffffff;
    border: none;
}
QPushButton#PrimaryButton:hover {
    background: #2559c9;
}
"""


class ValidationError(Exception):
    """表单校验失败。widget 指向需要重新获得焦点的输入控件。"""

    def __init__(self, message, widget=None):
        super().__init__(message)
        self.message = message
        self.widget = widget


@dataclass
class Query:
    """一次查询的全部条件。mode 决定日期参数如何映射到 search_accounts。"""

    mode: str = "全部账单"
    keyword: str = ""
    account_type: object = None
    date: str = ""
    month: str = ""
    start_date: str = ""
    end_date: str = ""

    def to_search_kwargs(self):
        kwargs = {
            "keyword": self.keyword or None,
            "account_type": self.account_type,
        }

        if self.mode == "按日期":
            kwargs["start_date"] = self.date
            kwargs["end_date"] = self.date

        elif self.mode == "按月份":
            kwargs["account_month"] = self.month

        elif self.mode == "按日期范围":
            kwargs["start_date"] = self.start_date
            kwargs["end_date"] = self.end_date

        return kwargs

    @property
    def is_range_reversed(self):
        return (
            self.mode == "按日期范围"
            and self.start_date > self.end_date
        )


class NumericTableItem(QTableWidgetItem):
    """显示格式化文本、但按真实数值排序的单元格（金额 / ID 需要）。"""

    def __init__(self, value, text):
        super().__init__(text)

        self._value = value
        self.setFlags(
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        )

    def __lt__(self, other):
        if isinstance(other, NumericTableItem):
            return self._value < other._value
        return super().__lt__(other)


class AccountDialog(QDialog):
    """添加 / 修改账单的共用对话框。mode 取 "add" 或 "edit"。"""

    def __init__(self, mode="add", account=None, parent=None):
        super().__init__(parent)

        self.mode = mode
        self.account = account

        self.setWindowTitle("添加账单" if mode == "add" else "修改账单")
        self.resize(360, 240)

        self.name_input = QLineEdit()
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("例如 25.50")

        self.type_input = QComboBox()
        self.type_input.addItems(["收入", "支出"])

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setDate(QDate.currentDate())

        if account is not None:
            self._prefill(account)

        form_layout = QFormLayout()
        form_layout.addRow("名称：", self.name_input)
        form_layout.addRow("金额：", self.price_input)
        form_layout.addRow("类型：", self.type_input)
        form_layout.addRow("日期：", self.date_input)

        self.save_button = QPushButton("保存")
        self.save_button.setObjectName("PrimaryButton")
        self.cancel_button = QPushButton("取消")

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)

        self.save_button.clicked.connect(self.save_account)
        self.cancel_button.clicked.connect(self.reject)
        self.name_input.setFocus()

    def _prefill(self, account):
        self.name_input.setText(account.name)
        self.price_input.setText(f"{account.price:g}")
        self.type_input.setCurrentText(account.type)

        parsed = QDate.fromString(account.date, "yyyy-MM-dd")
        if parsed.isValid():
            self.date_input.setDate(parsed)

    def read_form(self):
        """校验并返回 (name, price, type, date)。失败时抛 ValidationError。"""
        name = self.name_input.text().strip()
        if not name:
            raise ValidationError("名称不能为空", self.name_input)

        try:
            price = float(self.price_input.text().strip())
        except ValueError:
            raise ValidationError("金额必须是数字", self.price_input)

        if price <= 0:
            raise ValidationError("金额必须大于 0", self.price_input)

        date = self.date_input.date().toString("yyyy-MM-dd")
        if date > QDate.currentDate().toString("yyyy-MM-dd"):
            raise ValidationError("不能添加未来日期的账单", self.date_input)

        return name, price, self.type_input.currentText(), date

    def save_account(self):
        try:
            name, price, account_type, date = self.read_form()
        except ValidationError as error:
            QMessageBox.warning(self, "输入错误", error.message)
            if error.widget is not None:
                error.widget.setFocus()
            return

        if self.mode == "add":
            saved = database.insert_account(name, price, account_type, date)
        else:
            saved = database.update_account_db(
                self.account.id, name, price, account_type, date
            )

        if saved:
            self.accept()
        else:
            QMessageBox.critical(
                self, "保存失败", "数据库写入失败，详情见 logs/app.log"
            )


class StatisticsBar(QWidget):
    """总收入 / 总支出 / 余额三张卡片。纯展示，不含业务逻辑。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.income_card = self._build_card("总收入")
        self.expense_card = self._build_card("总支出")
        self.balance_card = self._build_card("余额")

        for card in (self.income_card, self.expense_card, self.balance_card):
            layout.addWidget(card)

        self.set_stats(0.0, 0.0, 0, 0)

    @staticmethod
    def _build_card(title):
        card = QWidget()
        card.setObjectName("StatCard")

        title_label = QLabel(title)
        title_label.setObjectName("StatTitle")

        amount_label = QLabel("¥ 0.00")
        amount_label.setObjectName("StatAmount")

        font = amount_label.font()
        font.setPointSize(16)
        font.setBold(True)
        amount_label.setFont(font)

        count_label = QLabel("0 笔")
        count_label.setObjectName("StatCount")

        card_layout = QVBoxLayout(card)
        card_layout.addWidget(title_label)
        card_layout.addWidget(amount_label)
        card_layout.addWidget(count_label)

        card.title_label = title_label
        card.amount_label = amount_label
        card.count_label = count_label

        return card

    def set_stats(self, income, expense, income_count, expense_count):
        balance = income - expense

        self._apply(
            self.income_card,
            income,
            f"{income_count} 笔",
            INCOME_COLOR,
        )
        self._apply(
            self.expense_card,
            expense,
            f"{expense_count} 笔",
            EXPENSE_COLOR,
        )
        self._apply(
            self.balance_card,
            balance,
            f"共 {income_count + expense_count} 笔",
            EXPENSE_COLOR if balance < 0 else INCOME_COLOR,
        )

    @staticmethod
    def _apply(card, amount, count_text, color):
        card.amount_label.setText(f"¥ {amount:,.2f}")
        card.count_label.setText(count_text)
        card.amount_label.setStyleSheet(f"color: {color};")


class FilterPanel(QWidget):
    """查询条件区。发出 queryRequested(Query)，自身不访问数据库。"""

    queryRequested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.mode_input = QComboBox()
        self.mode_input.addItems(
            ["全部账单", "按日期", "按月份", "按日期范围"]
        )

        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("名称关键词")
        self.keyword_input.setClearButtonEnabled(True)

        self.type_input = QComboBox()
        self.type_input.addItems([TYPE_FILTER_ALL, "收入", "支出"])

        self.day_input = self._make_date_edit(QDate.currentDate())
        self.month_input = self._make_date_edit(
            QDate.currentDate(), "yyyy-MM"
        )
        self.start_input = self._make_date_edit(
            QDate.currentDate().addMonths(-1)
        )
        self.end_input = self._make_date_edit(QDate.currentDate())

        self.date_stack = QStackedWidget()
        self.date_stack.addWidget(QWidget())
        self.date_stack.addWidget(self._labeled("日期：", self.day_input))
        self.date_stack.addWidget(self._labeled("月份：", self.month_input))
        self.date_stack.addWidget(
            self._labeled("从", self.start_input, "至", self.end_input)
        )

        self.search_button = QPushButton("查询")
        self.search_button.setObjectName("PrimaryButton")
        self.reset_button = QPushButton("重置")

        first_row = QHBoxLayout()
        first_row.addWidget(QLabel("查询："))
        first_row.addWidget(self.mode_input)
        first_row.addSpacing(12)
        first_row.addWidget(QLabel("关键词："))
        first_row.addWidget(self.keyword_input, 1)
        first_row.addSpacing(12)
        first_row.addWidget(QLabel("类型："))
        first_row.addWidget(self.type_input)

        second_row = QHBoxLayout()
        second_row.addWidget(self.date_stack)
        second_row.addStretch()
        second_row.addWidget(self.search_button)
        second_row.addWidget(self.reset_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(first_row)
        layout.addLayout(second_row)

        self.mode_input.currentIndexChanged.connect(
            self.date_stack.setCurrentIndex
        )
        self.search_button.clicked.connect(self.emit_query)
        self.reset_button.clicked.connect(self.reset)
        self.keyword_input.returnPressed.connect(self.emit_query)

    @staticmethod
    def _make_date_edit(date, display_format="yyyy-MM-dd"):
        editor = QDateEdit()
        editor.setCalendarPopup(True)
        editor.setDisplayFormat(display_format)
        editor.setDate(date)
        return editor

    @staticmethod
    def _labeled(*items):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        for item in items:
            if isinstance(item, str):
                layout.addWidget(QLabel(item))
            else:
                layout.addWidget(item)

        return container

    def build_query(self):
        account_type = self.type_input.currentText()

        return Query(
            mode=self.mode_input.currentText(),
            keyword=self.keyword_input.text().strip(),
            account_type=(
                None if account_type == TYPE_FILTER_ALL else account_type
            ),
            date=self.day_input.date().toString("yyyy-MM-dd"),
            month=self.month_input.date().toString("yyyy-MM"),
            start_date=self.start_input.date().toString("yyyy-MM-dd"),
            end_date=self.end_input.date().toString("yyyy-MM-dd"),
        )

    def emit_query(self):
        self.queryRequested.emit(self.build_query())

    def reset(self):
        self.mode_input.setCurrentIndex(0)
        self.keyword_input.clear()
        self.type_input.setCurrentIndex(0)
        self.emit_query()




class MainWindow(QMainWindow):
    """主窗口。refresh() 是唯一刷新入口。"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("我的记账软件")
        self.resize(1040, 700)

        self.accounts = []

        self.statistics = StatisticsBar()
        self.filter_panel = FilterPanel()

        self.table = self._build_table()

        self.empty_label = QLabel("暂无账单，点击「＋ 添加账单」开始记录")
        self.empty_label.setObjectName("EmptyHint")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table_stack = QStackedWidget()
        self.table_stack.addWidget(self.table)
        self.table_stack.addWidget(self.empty_label)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.statistics)
        layout.addWidget(self.filter_panel)
        layout.addWidget(self.table_stack, 1)
        self.setCentralWidget(central)

        self._build_menu()
        self._build_toolbar()

        self.filter_panel.queryRequested.connect(self.run_query)
        self.table.itemDoubleClicked.connect(self.update_account)

        self.refresh()

    # =========================
    # 构建
    # =========================

    @staticmethod
    def _build_table():
        table = QTableWidget(0, len(HEADERS))
        table.setHorizontalHeaderLabels(HEADERS)
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)

        header = table.horizontalHeader()
        header.setSectionResizeMode(
            COL_NAME, QHeaderView.ResizeMode.Stretch
        )
        for column in (COL_ID, COL_AMOUNT, COL_TYPE, COL_DATE):
            header.setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )

        table.setSortingEnabled(True)
        table.sortItems(COL_DATE, Qt.SortOrder.DescendingOrder)

        return table

    def _build_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件(&F)")
        file_menu.addAction("导出为 CSV", self.export_csv)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        edit_menu = menu_bar.addMenu("编辑(&E)")
        edit_menu.addAction("添加账单", self.add_account)
        edit_menu.addAction("修改账单", self.update_account)
        edit_menu.addAction("删除账单", self.delete_account)

        data_menu = menu_bar.addMenu("数据(&D)")
        data_menu.addAction("备份数据库", self.backup_db)
        data_menu.addAction("恢复数据库", self.restore_db)

        help_menu = menu_bar.addMenu("帮助(&H)")
        help_menu.addAction("关于", self.show_about)

    def _build_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction("＋ 添加账单", self.add_account)
        toolbar.addAction("✎ 修改账单", self.update_account)
        toolbar.addAction("－ 删除账单", self.delete_account)
        toolbar.addSeparator()
        toolbar.addAction("导出", self.export_csv)
        toolbar.addAction("备份", self.backup_db)
        toolbar.addAction("恢复", self.restore_db)

    # =========================
    # 数据流：表格与统计的唯一数据源
    # =========================

    def refresh(self):
        """按当前筛选条件重新加载。增删改之后调用，保持筛选不重置。"""
        self.run_query(self.filter_panel.build_query())

    def run_query(self, query):
        if query.is_range_reversed:
            QMessageBox.warning(
                self, "日期错误", "开始日期不能晚于结束日期"
            )
            return

        accounts = database.search_accounts(**query.to_search_kwargs())
        self._apply_accounts(accounts)

    def _apply_accounts(self, accounts):
        """表格与统计消费同一个列表，结构上不可能脱节。"""
        self.accounts = accounts

        self._fill_table(accounts)
        self._update_statistics(accounts)
        self._update_status_bar(accounts)

        self.table_stack.setCurrentIndex(1 if not accounts else 0)

    def _fill_table(self, accounts):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(accounts))

        for row, account in enumerate(accounts):
            self.table.setItem(
                row, COL_ID, NumericTableItem(account.id, str(account.id))
            )
            self.table.setItem(
                row, COL_NAME, self._readonly_item(account.name)
            )

            color = QColor(
                INCOME_COLOR if account.is_income() else EXPENSE_COLOR
            )

            amount_item = NumericTableItem(
                account.price, f"{account.price:,.2f}"
            )
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )
            amount_item.setForeground(color)
            self.table.setItem(row, COL_AMOUNT, amount_item)

            type_item = self._readonly_item(account.type)
            type_item.setForeground(color)
            self.table.setItem(row, COL_TYPE, type_item)

            self.table.setItem(
                row, COL_DATE, self._readonly_item(account.date)
            )

        self.table.setSortingEnabled(True)

    @staticmethod
    def _readonly_item(text):
        item = QTableWidgetItem(text)
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        )
        return item

    def _update_statistics(self, accounts):
        income = sum(a.price for a in accounts if a.is_income())
        expense = sum(a.price for a in accounts if a.is_expense())
        income_count = sum(1 for a in accounts if a.is_income())
        expense_count = sum(1 for a in accounts if a.is_expense())

        self.statistics.set_stats(
            income, expense, income_count, expense_count
        )

    def _update_status_bar(self, accounts):
        self.statusBar().showMessage(
            f"共 {len(accounts)} 条记录 · 双击一行可修改"
        )

    # =========================
    # 增删改
    # =========================

    def _selected_account(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一条账单")
            return None

        id_item = self.table.item(row, COL_ID)
        if id_item is None:
            return None

        account_id = int(id_item.text())

        for account in self.accounts:
            if account.id == account_id:
                return account

        QMessageBox.warning(self, "错误", "找不到这条账单，请刷新后重试")
        return None

    def add_account(self):
        dialog = AccountDialog("add", parent=self)
        if dialog.exec():
            self.refresh()

    def update_account(self):
        account = self._selected_account()
        if account is None:
            return

        dialog = AccountDialog("edit", account, self)
        if dialog.exec():
            self.refresh()

    def delete_account(self):
        account = self._selected_account()
        if account is None:
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除「{account.name}」（{account.price:,.2f} 元）吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if database.delete_account_db(account.id):
            self.refresh()
        else:
            QMessageBox.critical(self, "删除失败", "没有找到这条账单")

    # =========================
    # 导出 / 备份 / 恢复
    # =========================

    def export_csv(self):
        export_accounts()

        path = os.path.join(EXPORT_DIR, "accounts.csv")
        if os.path.exists(path):
            QMessageBox.information(self, "导出成功", f"导出文件：\n{path}")
        else:
            QMessageBox.warning(
                self, "导出失败", "导出失败，详情见 logs/app.log"
            )

    def backup_db(self):
        backup_database()

        path = os.path.join(BACKUP_DIR, "accounts_backup.db")
        if os.path.exists(path):
            QMessageBox.information(self, "备份成功", f"备份文件：\n{path}")
        else:
            QMessageBox.warning(self, "备份失败", "找不到数据库文件")

    def restore_db(self):
        path = os.path.join(BACKUP_DIR, "accounts_backup.db")
        if not os.path.exists(path):
            QMessageBox.warning(
                self, "恢复失败", "还没有备份文件，请先执行备份"
            )
            return

        reply = QMessageBox.question(
            self,
            "确认恢复",
            "恢复会用备份覆盖当前全部账单数据，且不可撤销。确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        restore_database(confirm=False)

        QMessageBox.information(self, "恢复成功", "数据已恢复，界面已刷新。")
        self.refresh()

    def show_about(self):
        QMessageBox.about(
            self,
            "关于",
            "我的记账软件\n\nPython + SQLite + PyQt6\n个人学习项目",
        )


def main():
    create_table()

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
