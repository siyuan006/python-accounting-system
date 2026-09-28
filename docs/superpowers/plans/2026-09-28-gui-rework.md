# GUI 重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `GUI.py` 的致命递归 bug 与 8 处缺陷，把它重构成一个真正可用的 PyQt6 桌面记账界面。

**Architecture:** 保持单文件 `GUI.py`，内部拆为 4 个职责单一的类 —— `AccountDialog`（添加/修改合一）、`StatisticsBar`（统计卡片）、`FilterPanel`（查询条件 + `QStackedWidget`）、`MainWindow`（装配 + 唯一刷新入口 `refresh()`）。统计从**当前显示的 `list[Account]`** 算出，与表格消费同一个列表，二者结构上不可能脱节。

**Tech Stack:** Python 3.12 / PyQt6 (Qt 6.11) / SQLite / pytest

## Global Constraints

- 设计依据：`docs/superpowers/specs/2026-09-28-gui-rework-design.md`
- **不引入任何新依赖**（明确排除 matplotlib、pytest-qt）
- GUI 测试通过 `QT_QPA_PLATFORM=offscreen` 运行，不依赖真实显示器
- 测试**必须**把 `database.DATABASE` 指向 `tmp_path`；**不得**沿用 `tests/test_database.py:18` 的 `"accounts.db"`（那是相对路径，会指向仓库根目录）
- 现有 29 个测试必须全程保持通过
- 界面文案一律中文，与现有代码风格一致
- 每个任务结束必须提交一次

## 文件结构

| 文件 | 动作 | 职责 |
|---|---|---|
| `GUI.py` | 重写 | 全部界面代码（4 个类 + 常量 + `main()`） |
| `database.py` | 改 1 行 (447) | `get_accounts_by_date_range` 走 `DATABASE` |
| `backup.py` | 改 1 处 | `restore_database(confirm=True)` 可跳过 `input()` |
| `tests/conftest.py` | 新建 | `qt_app` / `gui_db` 夹具 |
| `tests/test_gui.py` | 新建 | 全部 GUI 测试（按任务逐步追加） |
| `tests/test_backup.py` | 新建 | 备份/恢复测试 |
| `tests/test_database.py` | 追加 1 个测试 | 缺陷 #6 回归 |
| `requirements.txt` | 新建 | README 引用了但文件不存在 |
| `README.md` | 更新 | 勾选已完成项 |

---

## Task 1: 前置修补与测试夹具

GUI 正确性的三个前置条件：`database.py` 的路径 bug、`backup.py` 的 `input()` 阻塞、以及一套不会污染真实数据的 GUI 测试夹具。

**Files:**
- Modify: `database.py:447`
- Modify: `backup.py:28-52`
- Create: `tests/conftest.py`
- Create: `tests/test_backup.py`
- Modify: `tests/test_database.py`（末尾追加）
- Create: `requirements.txt`

**Interfaces:**
- Consumes: 无
- Produces: `database.DATABASE`（模块级可变全局，后续所有 GUI 测试依赖它可被 monkeypatch）；`backup.restore_database(confirm=True)`；pytest 夹具 `qt_app`（session 级 `QApplication`）与 `gui_db`（把 `database.DATABASE` 指向 `tmp_path/test_gui.db` 并建表）

- [ ] **Step 1: 写失败测试 —— 日期范围查询必须走 DATABASE**

追加到 `tests/test_database.py` 末尾：

```python
def test_get_accounts_by_date_range_uses_configured_database(test_db):
    """缺陷 #6 回归：必须走 database.DATABASE，而不是硬编码的 accounts.db。"""
    database.insert_account("工资", 5000, "收入", "2026-09-01")
    database.insert_account("餐饮", 100, "支出", "2026-09-25")
    database.insert_account("购物", 200, "支出", "2026-10-01")

    accounts = database.get_accounts_by_date_range("2026-09-01", "2026-09-30")

    assert len(accounts) == 2
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_database.py::test_get_accounts_by_date_range_uses_configured_database -v`
Expected: FAIL —— `assert 0 == 2`。硬编码的 `"accounts.db"` 在仓库根目录不存在表，`sqlite3.Error` 被吞掉返回 `[]`。

- [ ] **Step 3: 修复 database.py**

`database.py:447`，把：

```python
        with sqlite3.connect("accounts.db") as conn:
```

改为：

```python
        with sqlite3.connect(DATABASE) as conn:
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_database.py -v`
Expected: 全部 PASS（含新增的那个）。

- [ ] **Step 5: 写失败测试 —— 恢复数据库不得阻塞在 input()**

创建 `tests/test_backup.py`：

```python
import backup


def test_backup_copies_database(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "DATABASE", str(tmp_path / "accounts.db"))

    (tmp_path / "accounts.db").write_bytes(b"payload")

    backup.backup_database()

    assert (tmp_path / "accounts_backup.db").read_bytes() == b"payload"


def test_restore_skips_input_when_confirm_false(tmp_path, monkeypatch):
    """GUI 里调用 restore_database() 若触发 input() 会挂死整个程序。"""

    def explode(*args, **kwargs):
        raise AssertionError("confirm=False 时不应调用 input()")

    monkeypatch.setattr(backup, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "DATABASE", str(tmp_path / "accounts.db"))
    monkeypatch.setattr("builtins.input", explode)

    (tmp_path / "accounts_backup.db").write_bytes(b"backup-payload")

    backup.restore_database(confirm=False)

    assert (tmp_path / "accounts.db").read_bytes() == b"backup-payload"


def test_restore_aborts_when_user_declines(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "DATABASE", str(tmp_path / "accounts.db"))
    monkeypatch.setattr("builtins.input", lambda *args: "no")

    (tmp_path / "accounts.db").write_bytes(b"current")
    (tmp_path / "accounts_backup.db").write_bytes(b"backup-payload")

    backup.restore_database()

    assert (tmp_path / "accounts.db").read_bytes() == b"current"
```

- [ ] **Step 6: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_backup.py -v`
Expected: `test_restore_skips_input_when_confirm_false` FAIL —— `TypeError: restore_database() got an unexpected keyword argument 'confirm'`。

- [ ] **Step 7: 给 backup.py 的 restore_database 加 confirm 参数**

把 `backup.py:28-35` 的开头：

```python
def restore_database():
    confirm = input(
        "恢复数据库会覆盖当前数据，确定吗？(yes/no)："
    )

    if confirm.lower() != "yes":
        print("已取消恢复")
        return
```

改为：

```python
def restore_database(confirm=True):
    if confirm:
        answer = input(
            "恢复数据库会覆盖当前数据，确定吗？(yes/no)："
        )

        if answer.lower() != "yes":
            print("已取消恢复")
            return
```

其余部分（`try: ... shutil.copy(backup_file, DATABASE) ...`）保持不变。

- [ ] **Step 8: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_backup.py tests/test_database.py -v`
Expected: 全部 PASS。

- [ ] **Step 9: 创建 tests/conftest.py**

```python
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
```

- [ ] **Step 10: 验证夹具可用**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: 全部 PASS（此时 `gui_db` 还没人用，但语法与导入必须无误）。

- [ ] **Step 11: 创建 requirements.txt**

README 第 294 行让用户 `pip install -r requirements.txt`，但该文件不存在。创建：

```text
PyQt6>=6.6
pytest>=8.0
```

- [ ] **Step 12: 提交**

```bash
git add database.py backup.py requirements.txt tests/conftest.py tests/test_backup.py tests/test_database.py
git commit -m "fix: 日期范围查询走 DATABASE，恢复备份可跳过 input() 确认

- database.get_accounts_by_date_range 不再硬编码 accounts.db（缺陷 #6）
- backup.restore_database 增加 confirm 参数，供 GUI 调用（避免挂死在 stdin）
- 新增 GUI 测试夹具 qt_app / gui_db
- 补上 README 引用但缺失的 requirements.txt

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 2: AccountDialog（合并添加与修改）

替换掉 `AddAccountDialog` 与 `UpdateAccountDialog`（二者近 200 行几乎逐行重复），并修掉「校验失败静默无提示」（缺陷 #5）与「无未来日期校验」（缺陷 #9）。

> 本任务**新增** `AccountDialog`，旧的两个对话框暂不删除（Task 5 一并清理）。

**Files:**
- Modify: `GUI.py`（在 import 区之后新增常量、`ValidationError`、`AccountDialog`）
- Create: `tests/test_gui.py`

**Interfaces:**
- Consumes: `database.insert_account(name, price, type, date) -> bool`、`database.update_account_db(id, name, price, type, date) -> bool`、`database.get_accounts() -> list[Account]`
- Produces:
  - `GUI.ValidationError(message, widget=None)`，属性 `.message` / `.widget`
  - `GUI.AccountDialog(mode="add"|"edit", account=None, parent=None)`；属性 `name_input: QLineEdit`、`price_input: QLineEdit`、`type_input: QComboBox`、`date_input: QDateEdit`；方法 `read_form() -> tuple[str, float, str, str]`（失败抛 `ValidationError`）、`save_account()`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_gui.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -v`
Expected: FAIL —— `AttributeError: module 'GUI' has no attribute 'AccountDialog'`。

- [ ] **Step 3: 实现 AccountDialog**

在 `GUI.py` 的 import 区之后插入。先替换 import 区（原第 1-35 行）：

```python
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
```

紧接着插入常量与两个基础类型：

```python
INCOME_COLOR = "#1a7f37"
EXPENSE_COLOR = "#c0392b"

COL_ID, COL_NAME, COL_AMOUNT, COL_TYPE, COL_DATE = range(5)
HEADERS = ["ID", "名称", "金额", "类型", "日期"]

TYPE_FILTER_ALL = "全部"


class ValidationError(Exception):
    """表单校验失败。widget 指向需要重新获得焦点的输入控件。"""

    def __init__(self, message, widget=None):
        super().__init__(message)
        self.message = message
        self.widget = widget
```

然后插入 `AccountDialog`：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -v`
Expected: 全部 PASS（9 个）。

> 若报 `ImportError: cannot import name 'QPushButton'`，说明 Step 3 的 import 区替换不完整。

- [ ] **Step 5: 确认既有测试未受影响**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: 全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add GUI.py tests/test_gui.py
git commit -m "feat(gui): 添加 AccountDialog，合并添加/修改对话框

修掉缺陷 #5（校验失败静默无提示）与 #9（缺未来日期校验）。
两个旧对话框暂留，Task 5 清理。

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 3: StatisticsBar（统计卡片）

**Files:**
- Modify: `GUI.py`（新增 `StatisticsBar` 类）
- Modify: `tests/test_gui.py`（追加）

**Interfaces:**
- Consumes: 常量 `INCOME_COLOR` / `EXPENSE_COLOR`
- Produces: `GUI.StatisticsBar()`；属性 `income_card` / `expense_card` / `balance_card`，每个卡片带 `title_label` / `amount_label` / `count_label`（均为 `QLabel`）；方法 `set_stats(income: float, expense: float, income_count: int, expense_count: int) -> None`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_gui.py` 末尾：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -k statistics -v`
Expected: FAIL —— `AttributeError: module 'GUI' has no attribute 'StatisticsBar'`。

- [ ] **Step 3: 实现 StatisticsBar**

在 `GUI.py` 中 `AccountDialog` 之后插入：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -k statistics -v`
Expected: 4 个 PASS。

- [ ] **Step 5: 提交**

```bash
git add GUI.py tests/test_gui.py
git commit -m "feat(gui): 添加 StatisticsBar 统计卡片

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 4: Query 与 FilterPanel（查询条件区）

修掉缺陷 #3（起止日期控件从未加入布局，导致「按日期范围」不可用）。

**Files:**
- Modify: `GUI.py`（新增 `Query` dataclass 与 `FilterPanel` 类）
- Modify: `tests/test_gui.py`（追加）

**Interfaces:**
- Consumes: `database.search_accounts(keyword, account_type, account_month, start_date, end_date)` 的**关键字参数名**
- Produces:
  - `GUI.Query(mode="全部账单", keyword="", account_type=None, date="", month="", start_date="", end_date="")`；方法 `to_search_kwargs() -> dict`；属性 `is_range_reversed: bool`
  - `GUI.FilterPanel()`；信号 `queryRequested(object)`；属性 `mode_input: QComboBox`、`keyword_input: QLineEdit`、`type_input: QComboBox`、`day_input` / `month_input` / `start_input` / `end_input`（均 `QDateEdit`）、`date_stack: QStackedWidget`、`search_button` / `reset_button`（`QPushButton`）；方法 `build_query() -> Query`、`emit_query()`、`reset()`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_gui.py` 末尾：

```python
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
```

在文件顶部补两个 import：

```python
from PyQt6.QtWidgets import QDateEdit, QDialog
```

（替换原来的 `from PyQt6.QtWidgets import QDialog`）

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -k "query or filter" -v`
Expected: FAIL —— `AttributeError: module 'GUI' has no attribute 'Query'`。

- [ ] **Step 3: 实现 Query**

在 `GUI.py` 的 `ValidationError` 之后插入：

```python
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
```

- [ ] **Step 4: 实现 FilterPanel**

在 `GUI.py` 的 `StatisticsBar` 之后插入：

```python
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
```

- [ ] **Step 5: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -k "query or filter" -v`
Expected: 13 个 PASS。

- [ ] **Step 6: 提交**

```bash
git add GUI.py tests/test_gui.py
git commit -m "feat(gui): 添加 Query 与 FilterPanel 查询条件区

修掉缺陷 #3：起止日期控件此前从未加入任何布局，「按日期范围」不可用。
FilterPanel 用 QStackedWidget 按模式切换可见的日期控件。

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 5: MainWindow 主体（渲染 / 统计 / 查询）

**这是根治致命缺陷 #1 的任务**：整段替换旧 `MainWindow`，并删除已被取代的 `AddAccountDialog` 与 `UpdateAccountDialog`。

**Files:**
- Modify: `GUI.py`（删除旧 `AddAccountDialog`、`UpdateAccountDialog`、旧 `MainWindow`、旧 `if __name__` 块；新增新 `MainWindow` 与 `main()`）
- Modify: `tests/test_gui.py`（追加）

**Interfaces:**
- Consumes: `AccountDialog`、`StatisticsBar`、`FilterPanel`、`Query`；`database.search_accounts(...)`、`database.create_table()`；常量 `COL_*` / `HEADERS` / `INCOME_COLOR` / `EXPENSE_COLOR`
- Produces:
  - `GUI.NumericTableItem(value, text)` —— 按真实数值排序
  - `GUI.MainWindow()`；属性 `accounts: list[Account]`、`statistics: StatisticsBar`、`filter_panel: FilterPanel`、`table: QTableWidget`、`table_stack: QStackedWidget`、`empty_label: QLabel`；方法 `refresh()`、`run_query(query: Query)`、`_apply_accounts(accounts)`、`_fill_table(accounts)`、`_update_statistics(accounts)`、`_update_status_bar(accounts)`、`_selected_account()`
  - `GUI.main()` —— 入口

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_gui.py` 末尾：

```python
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
```

在 `tests/test_gui.py` 顶部 import 区补：

```python
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import QAbstractItemView, QDateEdit, QDialog
```

（替换掉原来的 `from PyQt6.QtCore import QDate` 与 `from PyQt6.QtWidgets import QDateEdit, QDialog`）

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -k "startup or statistics or range or empty or sorted or editable" -v`
Expected: FAIL —— 旧 `MainWindow` 没有 `statistics` / `filter_panel` / `table_stack` 属性。

- [ ] **Step 3: 删除旧类**

在 `GUI.py` 中**删除**以下三块（新类不受影响）：

1. `class AddAccountDialog(QDialog):` 整个类
2. `class UpdateAccountDialog(QDialog):` 整个类
3. `class MainWindow(QMainWindow):` 整个类
4. 文件末尾旧的 `if __name__ == "__main__":` 块

> 删除后 `GUI.py` 此刻只剩新组件（`ValidationError` / `Query` / `AccountDialog` / `StatisticsBar` / `FilterPanel`），测试会因找不到 `MainWindow` 而失败 —— 下一步补上。

- [ ] **Step 4: 运行测试确认失败方式符合预期**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -v`
Expected: 引用 `GUI.MainWindow` 的用例 FAIL，错误为 `AttributeError: module 'GUI' has no attribute 'MainWindow'`；`AccountDialog` / `StatisticsBar` / `Query` / `FilterPanel` 的用例继续 PASS。

- [ ] **Step 5: 实现 NumericTableItem 与新 MainWindow**

在 `GUI.py` 的 `AccountDialog` 之前插入：

```python
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
```

在 `GUI.py` 末尾（`FilterPanel` 之后）追加：

```python
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
    # 增删改（Task 6 补全菜单与实现）
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
        raise NotImplementedError("Task 6 实现")

    def update_account(self):
        raise NotImplementedError("Task 6 实现")

    def delete_account(self):
        raise NotImplementedError("Task 6 实现")

    def export_csv(self):
        raise NotImplementedError("Task 6 实现")

    def backup_db(self):
        raise NotImplementedError("Task 6 实现")

    def restore_db(self):
        raise NotImplementedError("Task 6 实现")

    def show_about(self):
        raise NotImplementedError("Task 6 实现")


def main():
    create_table()

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

同时在常量区补上占位样式表（Task 7 完善）：

```python
STYLE_SHEET = ""
```

> `add_account` 等方法暂时抛 `NotImplementedError` 是刻意的：它们是 Task 6 的交付物，此处先让 `MainWindow` 能被构建和测试。Task 6 会全部填实。

- [ ] **Step 6: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -v`
Expected: 全部 PASS。

- [ ] **Step 7: 全量测试**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: 全部 PASS。

- [ ] **Step 8: 手动冒烟启动**

Run: `.venv/Scripts/python.exe GUI.py`
Expected: 窗口正常打开，三个统计卡片显示当前真实数据的金额，表格有内容。点「查询：按日期 → 查询」**不再崩溃**（这是缺陷 #1 的最终验证）。关闭窗口。

- [ ] **Step 9: 提交**

```bash
git add GUI.py tests/test_gui.py
git commit -m "fix(gui): 重写 MainWindow，根治 load_statistics 自递归

- 删除旧 AddAccountDialog / UpdateAccountDialog / MainWindow（约 500 行）
- 新 MainWindow 由 StatisticsBar + FilterPanel + 表格装配而成
- 表格只读、按日期降序、金额右对齐并按数值排序、收支着色
- 空结果显示占位页；统计与表格消费同一列表

修掉缺陷 #1 #2 #7 #8。

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 6: 增删改与菜单栏 / 导出 / 备份 / 恢复

**Files:**
- Modify: `GUI.py`（填实 `add_account` / `update_account` / `delete_account` / `export_csv` / `backup_db` / `restore_db` / `show_about`；工具栏补数据按钮；接双击）
- Modify: `tests/test_gui.py`（追加）

**Interfaces:**
- Consumes: `AccountDialog`、`_selected_account()`、`restore_database(confirm=False)`（Task 1）、`backup_database()`、`export_accounts()`、`config.BACKUP_DIR` / `config.EXPORT_DIR`
- Produces: `MainWindow.add_account()` / `update_account()` / `delete_account()` / `export_csv()` / `backup_db()` / `restore_db()` / `show_about()`，均为无参无返回

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_gui.py` 末尾：

```python
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
    item = window.table.item(row_of(window, "餐饮"), GUI.COL_NAME)
    window.table.itemDoubleClicked.emit(item)

    assert captured["mode"] == "edit"


def test_menu_and_toolbar_expose_all_actions(qt_app, gui_db):
    window = make_window()

    menu_titles = [
        action.text() for menu in window.menuBar().findChildren(QMenu)
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
```

在 `tests/test_gui.py` 顶部 import 区补：

```python
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDialog,
    QMenu,
)

import backup
import export
```

> **为什么备份/恢复测试要 patch 两个模块：** `GUI.backup_db()` 用 `GUI.BACKUP_DIR` 拼提示路径并判断文件是否生成，而真正 `shutil.copy` 发生在 `backup.backup_database()` 里、读的是 `backup.BACKUP_DIR` 与 `backup.DATABASE`。只 patch 一处，另一处会写到仓库的真实 `backup/` 目录。

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -k "delete or dialog_writes or double_click or menu_and or about or export or backup or restore" -v`
Expected: FAIL —— `NotImplementedError: Task 6 实现`。

- [ ] **Step 3: 填实实现**

在 `GUI.py` 中，把 Task 5 留下的这一整块：

```python
    def add_account(self):
        raise NotImplementedError("Task 6 实现")

    def update_account(self):
        raise NotImplementedError("Task 6 实现")

    def delete_account(self):
        raise NotImplementedError("Task 6 实现")

    def export_csv(self):
        raise NotImplementedError("Task 6 实现")

    def backup_db(self):
        raise NotImplementedError("Task 6 实现")

    def restore_db(self):
        raise NotImplementedError("Task 6 实现")

    def show_about(self):
        raise NotImplementedError("Task 6 实现")
```

替换为：

```python
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
```

同时在 `__init__` 的 `self.filter_panel.queryRequested.connect(self.run_query)` 之后补一行：

```python
        self.table.itemDoubleClicked.connect(self.update_account)
```

并在 `_build_toolbar` 的三行 `addAction` 之后补：

```python
        toolbar.addSeparator()
        toolbar.addAction("导出", self.export_csv)
        toolbar.addAction("备份", self.backup_db)
        toolbar.addAction("恢复", self.restore_db)
```

> **实现要点：** `GUI.py` 顶部无需 `import backup` / `import export` —— 它只导入函数（`from backup import backup_database, restore_database`、`from export import export_accounts`）。测试里 `import backup` / `import export` 拿到模块对象后 patch 其全局变量即可生效，因为这些函数在**自己模块的 globals** 里解析 `BACKUP_DIR` / `EXPORT_DIR` / `DATABASE`。
> `GUI.py` 自己仍需要 `BACKUP_DIR` / `EXPORT_DIR`（来自 `from config import ...`）来拼提示路径与做存在性检查 —— 这个 import 在 Task 2 已经加好了。

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -v`
Expected: 全部 PASS。

- [ ] **Step 5: 全量测试**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: 全部 PASS。

- [ ] **Step 6: 手动验证导出 / 备份 / 恢复**

Run: `.venv/Scripts/python.exe GUI.py`
Expected，依次确认：

1. 工具栏点「导出」→ 弹「导出成功」并显示 `exports/accounts.csv` 路径
2. 工具栏点「备份」→ 弹「备份成功」并显示 `backup/accounts_backup.db` 路径
3. 手工删掉几条账单，再点「恢复」→ 确认后数据回来，**界面不卡死**
4. 双击某一行 → 打开预填好的「修改账单」对话框

- [ ] **Step 7: 提交**

```bash
git add GUI.py tests/test_gui.py
git commit -m "feat(gui): 补全增删改、菜单栏、导出与备份恢复

- 工具栏接入导出/备份/恢复，双击一行即修改
- 恢复流程用 QMessageBox 确认后调 restore_database(confirm=False)，不再挂死
- 增删改后 refresh() 保持当前筛选条件

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 7: 样式、README 与收尾验证

**Files:**
- Modify: `GUI.py`（填实 `STYLE_SHEET`）
- Modify: `README.md`
- Modify: `tests/test_gui.py`（追加 1 个冒烟测试）

**Interfaces:**
- Consumes: Task 5 留下的 `STYLE_SHEET` 常量与 `main()` 里的 `app.setStyleSheet(STYLE_SHEET)`
- Produces: 无新接口

- [ ] **Step 1: 写冒烟测试**

追加到 `tests/test_gui.py` 末尾：

```python
# =========================
# 样式
# =========================

def test_stylesheet_covers_core_widgets():
    assert "#StatCard" in GUI.STYLE_SHEET
    assert "QTableWidget" in GUI.STYLE_SHEET
    assert "#PrimaryButton" in GUI.STYLE_SHEET
    assert GUI.STYLE_SHEET.strip() != ""


def test_window_applies_stylesheet_without_error(qt_app, gui_db):
    qt_app.setStyleSheet(GUI.STYLE_SHEET)

    window = make_window()

    assert window.isEnabled()

    qt_app.setStyleSheet("")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -k stylesheet -v`
Expected: FAIL —— `STYLE_SHEET` 目前是空字符串。

- [ ] **Step 3: 填实 STYLE_SHEET**

把 `GUI.py` 中的：

```python
STYLE_SHEET = ""
```

替换为：

```python
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
QPushButton {
    background: #ffffff;
    border: 1px solid #d5d9df;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover {
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui.py -v`
Expected: 全部 PASS。

- [ ] **Step 5: 手动确认样式生效**

Run: `.venv/Scripts/python.exe GUI.py`
Expected: 统计卡片为白底圆角带边框；表格斑马纹；「查询」按钮为蓝色实心；输入框圆角。视觉正常，无控件被样式挤坏。

- [ ] **Step 6: 更新 README.md**

把「第五阶段：PyQt6 GUI」的勾选列表：

```markdown
* [ ] 完善界面布局
* [ ] 完善错误提示
* [ ] GUI 与 AccountManager 完整解耦
* [ ] 软件打包
* [ ] 发布可执行版本
```

改为：

```markdown
* [x] 完善界面布局
* [x] 完善错误提示
* [x] GUI 测试（tests/test_gui.py）
* [ ] GUI 与 AccountManager 完整解耦
* [ ] 软件打包
* [ ] 发布可执行版本
```

把「## 🎯 后续计划」里的：

```markdown
* [ ] 完善 PyQt6 用户界面
```

改为：

```markdown
* [x] 完善 PyQt6 用户界面
```

把「## 📷 项目截图」一节：

```markdown
## 📷 项目截图

后续将添加：

* 软件主界面
* 添加账单界面
* 修改账单界面
* 数据统计界面
* 查询界面
```

改为：

```markdown
## 📷 项目截图

待补充：

* 软件主界面
* 添加账单界面
* 修改账单界面
```

在「### 💾 数据库」一节之后新增：

```markdown
---

### 🖥️ 桌面界面

运行：

```bash
python GUI.py
```

界面结构：

```text
菜单栏      文件 / 编辑 / 数据 / 帮助
工具栏      ＋添加 ✎修改 －删除 │ 导出 备份 恢复
统计卡片    总收入 / 总支出 / 余额（含笔数）
查询区      查询模式 · 关键词 · 类型 · 日期控件
账单表格    只读、可点表头排序、收支着色、双击即修改
状态栏      记录条数
```

查询模式：

```text
全部账单 / 按日期 / 按月份 / 按日期范围
```

关键词与类型筛选对所有查询模式叠加生效。
```

- [ ] **Step 7: 全量测试**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: 全部 PASS（29 个原有 + 新增）。

- [ ] **Step 8: 确认旧缺陷已全部消失**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: 无 FAIL、无 ERROR。

逐条核对设计文档第 2 节的 9 个缺陷：

| # | 验证方式 |
|---|---|
| 1 递归 | `test_date_query_does_not_recurse` / `test_month_query_does_not_recurse` / `test_range_query_does_not_recurse` |
| 2 统计不刷新 | `test_statistics_match_displayed_rows` |
| 3 日期范围控件不可见 | `test_filter_panel_shows_both_bounds_in_range_mode` |
| 4 未建表 | `main()` 首行 `create_table()`；`test_empty_database_shows_placeholder` |
| 5 校验静默 | `test_dialog_rejects_empty_name` 等 4 个 |
| 6 硬编码路径 | `test_get_accounts_by_date_range_uses_configured_database` |
| 7 表格可编辑 | `test_table_cells_are_not_editable` |
| 8 行序不稳 | `test_rows_sorted_by_date_descending` |
| 9 无未来日期校验 | `test_dialog_rejects_future_date` |

- [ ] **Step 9: 手动端到端走查**

Run: `.venv/Scripts/python.exe GUI.py`

依次操作并确认无异常：

1. 添加一条收入、一条支出 → 卡片与表格同步更新
2. 双击某行改名改金额 → 保存后表格更新
3. 选一行点删除 → 确认后消失，统计同步
4. 查询模式切到「按月份」→ 日期控件变成月份选择器
5. 查询模式切到「按日期范围」→ 出现起止两个日期框，可修改
6. 把起始日期设成晚于结束日期 → 弹提示，表格内容不变
7. 关键词输入框回车 → 触发查询
8. 点「重置」→ 回到全部账单
9. 导出一份 CSV，用 Excel 打开确认中文不乱码
10. 备份 → 删几条 → 恢复 → 数据回来且界面不卡

- [ ] **Step 10: 提交**

```bash
git add GUI.py README.md tests/test_gui.py
git commit -m "style(gui): 添加 QSS 样式并更新 README

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## 完成标准

- `pytest` 全绿（29 个原有 + 约 60 个新增）
- `python GUI.py` 可正常启动、增删改查全流程可用
- 设计文档第 2 节的 9 个缺陷全部有对应回归测试
- 未引入任何新依赖
