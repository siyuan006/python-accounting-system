import sys

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QDialog,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
    QLabel
)

from PyQt6.QtCore import QDate

from database import (
    get_accounts,
    insert_account,
    delete_account_db,
    update_account_db,
    get_money_count,
    get_account_by_date,
    get_account_by_month,
    get_money_count_by_date,
    get_money_count_by_month,
    get_accounts_by_date_range,
    get_money_count_by_date_range
)
class AddAccountDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)


        self.setWindowTitle("添加账单")
        self.resize(350, 250)

        # 名称
        self.name_input = QLineEdit()

        # 金额
        self.price_input = QLineEdit()

        # 类型
        self.type_input = QComboBox()
        self.type_input.addItems([
            "收入",
            "支出"
        ])

        # 日期
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())

        # 表单
        form_layout = QFormLayout()

        form_layout.addRow(
            "名称：",
            self.name_input
        )

        form_layout.addRow(
            "金额：",
            self.price_input
        )

        form_layout.addRow(
            "类型：",
            self.type_input
        )

        form_layout.addRow(
            "日期：",
            self.date_input
        )

        # 按钮
        self.save_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")

        button_layout = QHBoxLayout()

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        # 整体布局
        layout = QVBoxLayout()

        layout.addLayout(form_layout)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 按钮事件
        self.save_button.clicked.connect(
            self.save_account
        )

        self.cancel_button.clicked.connect(
            self.reject
        )

    def save_account(self):

        name = self.name_input.text().strip()

        price_text = self.price_input.text().strip()

        account_type = self.type_input.currentText()

        date = self.date_input.date().toString(
            "yyyy-MM-dd"
        )

        # 名称不能为空
        if not name:
            self.name_input.setFocus()
            return

        # 金额必须是数字
        try:
            price = float(price_text)
        except ValueError:
            self.price_input.setFocus()
            return

        # 金额必须大于 0
        if price <= 0:
            self.price_input.setFocus()
            return

        # 写入数据库
        result = insert_account(
            name,
            price,
            account_type,
            date
        )

        if result:
            self.accept()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("我的记账软件")
        self.resize(1000, 650)

        # =========================
        # 统计信息
        # =========================

        self.income_label = QLabel()
        self.expense_label = QLabel()
        self.balance_label = QLabel()

        self.income_label.setText("总收入：0 元")
        self.expense_label.setText("总支出：0 元")
        self.balance_label.setText("余额：0 元")

        statistics_layout = QHBoxLayout()

        statistics_layout.addWidget(self.income_label)
        statistics_layout.addWidget(self.expense_label)
        statistics_layout.addWidget(self.balance_label)

        # =========================
        # 查询区域
        # =========================

        self.search_type = QComboBox()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(
            QDate.currentDate()
        )

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(
            QDate.currentDate()
        )

        self.search_type.addItems([
            "全部账单",
            "按日期",
            "按月份",
            "按日期范围"
        ])

        self.search_date = QDateEdit()
        self.search_date.setCalendarPopup(True)
        self.search_date.setDate(QDate.currentDate())

        self.search_button = QPushButton("查询")
        self.reset_button = QPushButton("显示全部")


        search_layout = QHBoxLayout()

        search_layout.addWidget(
            QLabel("查询：")
        )

        search_layout.addWidget(
            self.search_type
        )

        search_layout.addWidget(
            QLabel("日期：")
        )

        search_layout.addWidget(
            self.search_date
        )

        search_layout.addWidget(
            self.search_button
        )

        search_layout.addWidget(
            self.reset_button
        )


        # =========================
        # 顶部按钮
        # =========================

        self.add_button = QPushButton("＋ 添加账单")

        self.delete_button = QPushButton("− 删除账单")

        self.update_button = QPushButton("✎ 修改账单")

        # 顶部按钮布局
        button_layout = QHBoxLayout()

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.update_button)

        # =========================
        # 账单表格
        # =========================

        self.table = QTableWidget()

        self.table.setColumnCount(5)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "名称",
            "金额",
            "类型",
            "日期"
        ])

        # =========================
        # 主布局
        # =========================

        main_layout = QVBoxLayout()

        main_layout.addLayout(search_layout)

        # 统计信息
        main_layout.addLayout(statistics_layout)

        # 操作按钮
        main_layout.addLayout(button_layout)

        # 账单表格
        main_layout.addWidget(self.table)

        # 中央窗口
        central_widget = QWidget()

        central_widget.setLayout(main_layout)

        self.setCentralWidget(central_widget)

        # =========================
        # 按钮事件
        # =========================

        self.add_button.clicked.connect(
            self.open_add_dialog
        )

        self.delete_button.clicked.connect(
            self.delete_account
        )

        self.update_button.clicked.connect(
            self.update_account
        )
        self.search_button.clicked.connect(
            self.search_accounts
        )

        self.reset_button.clicked.connect(
            self.load_accounts
        )

        # =========================
        # 加载账单
        # =========================

        self.load_accounts()

    def load_accounts(self, accounts=None):

        if accounts is None:
            accounts = get_accounts()

        self.table.setRowCount(len(accounts))

        for row, account in enumerate(accounts):
            self.table.setItem(
                row,
                0,
                QTableWidgetItem(str(account.id))
            )

            self.table.setItem(
                row,
                1,
                QTableWidgetItem(account.name)
            )

            self.table.setItem(
                row,
                2,
                QTableWidgetItem(
                    f"{account.price:.2f}"
                )
            )

            self.table.setItem(
                row,
                3,
                QTableWidgetItem(account.type)
            )

            self.table.setItem(
                row,
                4,
                QTableWidgetItem(account.date)
            )
    def open_add_dialog(self):

        dialog = AddAccountDialog(self)

        result = dialog.exec()

        if result:
            self.load_accounts()

#     删除账单方法
    def delete_account(self):

        row = self.table.currentRow()

        # 没有选择任何行
        if row < 0:
            QMessageBox.warning(
                self,
                "提示",
                "请先选择要删除的账单"
            )
            return

        # 获取账单 ID
        account_id = int(
            self.table.item(row, 0).text()
        )

        # 获取账单名称
        account_name = self.table.item(
            row,
            1
        ).text()

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除「{account_name}」吗？",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 删除数据库记录
        result = delete_account_db(account_id)

        if result:

            QMessageBox.information(
                self,
                "删除成功",
                "账单已删除"
            )

            # 刷新表格
            self.load_accounts()

        else:

            QMessageBox.warning(
                self,
                "删除失败",
                "没有找到这条账单"
            )


# 修改账单方法
    def update_account(self):

        row = self.table.currentRow()

        # 没有选择
        if row < 0:
            QMessageBox.warning(
                self,
                "提示",
                "请先选择要修改的账单"
            )
            return

        # 获取 ID
        account_id = int(
            self.table.item(row, 0).text()
        )

        # 从数据库重新获取数据
        accounts = get_accounts()

        account = None

        for item in accounts:
            if item.id == account_id:
                account = item
                break

        if account is None:
            QMessageBox.warning(
                self,
                "错误",
                "找不到这条账单"
            )
            return

        # 打开修改窗口
        dialog = UpdateAccountDialog(
            account,
            self
        )

        result = dialog.exec()

        if result:
            self.load_accounts()
# 刷新统计方法
    def load_statistics(
            self,
            total_income=None,
            total_expense=None
    ):

        if total_income is None or total_expense is None:
            total_income, total_expense = get_money_count()

        balance = total_income - total_expense

        self.income_label.setText(
            f"总收入：{total_income:.2f} 元"
        )

        self.expense_label.setText(
            f"总支出：{total_expense:.2f} 元"
        )

        self.balance_label.setText(
            f"余额：{balance:.2f} 元"
        )
        self.load_statistics()

# 查询方法
    def search_accounts(self):

        search_type = self.search_type.currentText()

        # =========================
        # 全部账单
        # =========================

        if search_type == "全部账单":
            accounts = get_accounts()

            self.load_accounts(accounts)

            return

        # =========================
        # 按日期
        # =========================

        if search_type == "按日期":
            date = self.search_date.date().toString(
                "yyyy-MM-dd"
            )

            accounts = get_account_by_date(date)

            total_income, total_expense = (
                get_money_count_by_date(date)
            )

            self.load_accounts(accounts)

            self.load_statistics(
                total_income,
                total_expense
            )

            return

        # =========================
        # 按月份
        # =========================

        if search_type == "按月份":
            month = self.search_date.date().toString(
                "yyyy-MM"
            )

            accounts = get_account_by_month(month)

            total_income, total_expense = (
                get_money_count_by_month(month)
            )

            self.load_accounts(accounts)

            self.load_statistics(
                total_income,
                total_expense
            )

            return

        # =========================
        # 按日期范围
        # =========================

        if search_type == "按日期范围":

            start_date = self.start_date.date().toString(
                "yyyy-MM-dd"
            )

            end_date = self.end_date.date().toString(
                "yyyy-MM-dd"
            )

            # 开始日期不能晚于结束日期
            if start_date > end_date:
                QMessageBox.warning(
                    self,
                    "日期错误",
                    "开始日期不能晚于结束日期"
                )

                return

            accounts = get_accounts_by_date_range(
                start_date,
                end_date
            )

            total_income, total_expense = (
                get_money_count_by_date_range(
                    start_date,
                    end_date
                )
            )

            self.load_accounts(accounts)

            self.load_statistics(
                total_income,
                total_expense
            )

class UpdateAccountDialog(QDialog):

    def __init__(self, account, parent=None):
        super().__init__(parent)

        self.account = account

        self.setWindowTitle("修改账单")
        self.resize(350, 250)

        # 名称
        self.name_input = QLineEdit()
        self.name_input.setText(account.name)

        # 金额
        self.price_input = QLineEdit()
        self.price_input.setText(str(account.price))

        # 类型
        self.type_input = QComboBox()
        self.type_input.addItems([
            "收入",
            "支出"
        ])

        self.type_input.setCurrentText(
            account.type
        )

        # 日期
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)

        date = QDate.fromString(
            account.date,
            "yyyy-MM-dd"
        )

        self.date_input.setDate(date)

        # 表单
        form_layout = QFormLayout()

        form_layout.addRow(
            "名称：",
            self.name_input
        )

        form_layout.addRow(
            "金额：",
            self.price_input
        )

        form_layout.addRow(
            "类型：",
            self.type_input
        )

        form_layout.addRow(
            "日期：",
            self.date_input
        )

        # 按钮
        self.save_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")

        button_layout = QHBoxLayout()

        button_layout.addWidget(
            self.cancel_button
        )

        button_layout.addWidget(
            self.save_button
        )

        layout = QVBoxLayout()

        layout.addLayout(form_layout)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 事件
        self.save_button.clicked.connect(
            self.save_account
        )

        self.cancel_button.clicked.connect(
            self.reject
        )

    def save_account(self):

        name = self.name_input.text().strip()

        price_text = self.price_input.text().strip()

        account_type = self.type_input.currentText()

        date = self.date_input.date().toString(
            "yyyy-MM-dd"
        )

        # 名称不能为空
        if not name:
            QMessageBox.warning(
                self,
                "输入错误",
                "名称不能为空"
            )
            return

        # 金额必须是数字
        try:
            price = float(price_text)

        except ValueError:
            QMessageBox.warning(
                self,
                "输入错误",
                "金额必须是数字"
            )
            return

        # 金额必须大于 0
        if price <= 0:
            QMessageBox.warning(
                self,
                "输入错误",
                "金额必须大于 0"
            )
            return

        result = update_account_db(
            self.account.id,
            name,
            price,
            account_type,
            date
        )

        if result:
            self.accept()

        else:
            QMessageBox.warning(
                self,
                "修改失败",
                "账单不存在"
            )

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())