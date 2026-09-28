# GUI 重构设计（PyQt6 桌面记账软件）

日期：2026-09-28
状态：已批准，待实现
范围：`GUI.py` 重写为主，附带 `database.py` / `backup.py` 各一处最小修补

---

## 1. 背景

`GUI.py` 已实现主窗口、账单表格、增删改、统计标签与三种查询入口，但当前**不可用**：
任何按日期 / 按月份 / 按日期范围的查询都会触发 `RecursionError` 崩溃。
本次改造目标是把界面从「能启动」提升到「真正可用」，不引入新依赖（不加 matplotlib，不加 pytest-qt）。

---

## 2. 已确认缺陷清单

分析阶段通过阅读代码 + 无头运行复现得出。

### 致命

| # | 位置 | 问题 | 后果 |
|---|---|---|---|
| 1 | `GUI.py:502` | `load_statistics()` 方法体末尾无条件调用 `self.load_statistics()`，自递归 | 按日期/月份/范围查询必然 `RecursionError`（已用 `QT_QPA_PLATFORM=offscreen` 复现） |

### 功能失效

| # | 位置 | 问题 | 后果 |
|---|---|---|---|
| 2 | `GUI.py:324` | `load_accounts()` 不调用 `load_statistics()` | 启动时统计恒为「0 元」 |
| 3 | `GUI.py:184,190` | `self.start_date` / `self.end_date` 创建后从未 `addWidget` 进任何布局 | 「按日期范围」的起止日期控件不可见且不可改，日期锁死为今天 |
| 4 | `GUI.py` | 从不调用 `create_table()`（仅 `main.py` 调用） | 新环境首次运行 `data/accounts.db` 无表，添加账单静默失败 |
| 5 | `GUI.py:126-139` | `AddAccountDialog.save_account` 校验失败只 `setFocus()`，无任何提示 | 点「保存」无反应，用户不知原因（`UpdateAccountDialog` 反而有提示，两处不一致） |
| 6 | `database.py:447` | `get_accounts_by_date_range` 硬编码 `sqlite3.connect("accounts.db")`，绕过 `config.DATABASE` | 换库/测试时读错文件；与同文件其余函数不一致 |

### 数据完整性

| # | 位置 | 问题 | 后果 |
|---|---|---|---|
| 7 | `GUI.py:329` | `QTableWidget` 默认单元格可编辑，但编辑结果不写库 | 用户改了单元格、界面显示已改，重开程序发现没保存 |
| 8 | `database.py:70` | `get_accounts()` 无 `ORDER BY` | 每次刷新行序不稳定，同一批数据顺序会变 |

### 体验缺失

| # | 位置 | 问题 | 后果 |
|---|---|---|---|
| 9 | `GUI.py:112` | 无未来日期校验（`input_skills.InputSkills.input_date` 有） | 可录入明天/明年的账单 |

---

## 3. 目标架构

保持单文件 `GUI.py`，内部拆为 4 个职责单一的类。

### 3.1 `AccountDialog(QDialog)`

合并现有 `AddAccountDialog` 与 `UpdateAccountDialog`（二者近 200 行几乎逐行重复）。

```
AccountDialog(mode: str, account: Account | None = None, parent=None)
```

- `mode="add"` → 标题「添加账单」，空表单，日期默认今天
- `mode="edit"` → 标题「修改账单」，用 `account` 预填
- 保存逻辑唯一：`_validate()` 返回 `(name, price, type, date)` 或抛 `ValueError`；`mode` 决定调 `insert_account` 还是 `update_account_db`
- 校验规则（与 CLI 对齐）：名称非空、金额可转 `float` 且 `> 0`、日期不晚于今天
- 校验失败 **一律** `QMessageBox.warning` 并把焦点移回问题控件

依赖：`database.insert_account` / `database.update_account_db`。

### 3.2 `StatisticsBar(QWidget)`

三张卡片：总收入 / 总支出 / 余额，每张显示金额 + 笔数。

```
StatisticsBar.set_stats(income: float, expense: float, income_count: int, expense_count: int)
```

余额卡金额为负时用支出色。纯展示组件，不含业务逻辑。

### 3.3 `FilterPanel(QWidget)`

```
查询模式 [全部账单 ▾]  关键词 [______]  类型 [全部 ▾]
[起始日期 ▾] 至 [结束日期 ▾]        [查询] [重置]
```

- 查询模式：全部账单 / 按日期 / 按月份 / 按日期范围
- 日期控件放 `QStackedWidget`：按模式只显示相关控件（按日期→单个日期；按月份→单个月份；按日期范围→起止两个；全部账单→不显示）
- 发出信号 `queryRequested`，携带一个查询条件对象；`resetRequested` 重置为「全部账单」
- 不直接访问数据库

### 3.4 `MainWindow(QMainWindow)`

- **菜单栏**：文件（导出 CSV、退出）/ 编辑（添加、修改、删除）/ 数据（备份、恢复）/ 帮助（关于）
- **工具栏**：＋添加、✎修改、－删除 │ 导出、备份、恢复
- **中央区**：`StatisticsBar` → `FilterPanel` → `QTableWidget`（顺序即上→下）
- **状态栏**：`共 N 条记录 · 双击一行可修改`
- **表格**：5 列（ID/名称/金额/类型/日期），只读（`EditTrigger.NoEditTriggers`）、整行选择、交替行色、点击表头排序、金额列右对齐、收入绿 / 支出红、列宽自适应
- **交互**：双击某行 = ✎修改
- `refresh()` 是唯一刷新入口

---

## 4. 数据流：单一数据源

核心设计决定：**统计从当前显示的列表算出来，而不是另发一次聚合查询。**

```
FilterPanel.queryRequested
        ↓
MainWindow._fetch(query)  →  database.search_accounts(...)  →  list[Account]
        ↓
MainWindow._apply_accounts(accounts)
        ├─→ 填表（格式化、着色）
        └─→ 遍历同一列表，用 account.is_income() / is_expense() 累加
                ↓
            StatisticsBar.set_stats(...)
```

理由：

- 表格与统计**在结构上不可能脱节** —— 它们消费的是同一个 `list[Account]`
- 校验逻辑与 `AccountManager.calculate_balance()` 同源，GUI 与 CLI 行为一致
- 避免依赖 `get_money_count_by_*` 那一组函数（其中 `get_accounts_by_date_range` 还有缺陷 #6）

### 查询条件到数据库的映射

全部查询统一走 `database.search_accounts(keyword, account_type, account_month, start_date, end_date)`：

| 模式 | 映射 |
|---|---|
| 全部账单 | 全部参数为 `None` |
| 按日期 | `start_date = end_date = 所选日期` |
| 按月份 | `account_month = "YYYY-MM"` |
| 按日期范围 | `start_date` / `end_date` |

`search_accounts` 已支持全部这几种参数组合，且带 `ORDER BY date DESC`，无需改动。

关键词与类型筛选对**所有**模式叠加生效。

### 增删改后的刷新

`refresh()` 重跑**当前筛选条件**，而不是重置为「全部账单」。
理由：用户在「按月份 + 关键词=餐饮」下删掉一条，期望留在当前视图里继续操作。

---

## 5. 对 `GUI.py` 之外的两处修改

两处都是最小改动，且都是 GUI 正确性的前置条件。

### 5.1 `database.py`

```python
# 第 447 行
with sqlite3.connect("accounts.db") as conn:   # 改前
with sqlite3.connect(DATABASE) as conn:        # 改后
```

### 5.2 `backup.py`

`restore_database()` 目前用 `input()` 做确认。GUI 里调用它会让整个程序**挂死在等待 stdin**。

```python
def restore_database(confirm=True):
    if confirm:
        ...原有 input() 确认逻辑...
```

GUI 侧：先用 `QMessageBox.question` 确认，再调 `restore_database(confirm=False)`，并提示「恢复需重启程序生效」。

`backup_database()` 只 `print`，无阻塞，可直接复用。

---

## 6. 错误处理

| 场景 | 处理 |
|---|---|
| 写操作返回 `False` | `QMessageBox.critical`，提示具体失败原因 |
| 起始日期晚于结束日期 | `QMessageBox.warning`，中止查询，保留上次结果 |
| 金额非数字 / ≤ 0 / 名称为空 | 对话框内 `QMessageBox.warning` + 聚焦问题控件 |
| 日期晚于今天 | 对话框内拒绝，与 CLI 行为一致 |
| 查询结果为空 | 表格显示「暂无账单」占位行，状态栏「共 0 条记录」，统计全为 0 |
| 数据库文件缺失 | 启动时 `create_table()` 建表（缺陷 #4） |
| 恢复备份文件不存在 | `backup.py` 已有 `FileNotFoundError` 处理；GUI 转为 `QMessageBox.warning` |

数据库层的异常已经由 `database.py` 内部 `try/except sqlite3.Error` + `logger` 记录，GUI 只负责把 `False` / 空列表呈现给用户，不重复记日志。

---

## 7. 测试策略

### 现有测试

`tests/` 下 29 个测试当前全绿，覆盖 `database.py` 与 `account_manager.py`。
本次改动**不得**让其中任何一个失败 —— 尤其 `tests/test_database.py:20` 那行 `database.DATABASE = "accounts.db"`，它依赖 `DATABASE` 是模块级可变全局（缺陷 #6 的修复正建立在这一点上）。

### 新增 `tests/test_gui.py`

无 `pytest-qt` 依赖，用 `QT_QPA_PLATFORM=offscreen` 直接构造控件。

夹具：`monkeypatch.setattr(database, "DATABASE", str(tmp_path / "test.db"))` + `create_table()`，
并在用例结束后还原为 `config.DATABASE`（**不可**沿用 `test_database.py` 的 `"accounts.db"`，那会指向仓库根目录的真实库）。

覆盖点：

1. **递归回归** —— `load_statistics()` 能正常返回（缺陷 #1 的直接回归测试）
2. 启动后表格行数 == 库中记录数
3. 统计与表格一致：`StatisticsBar` 的总收入/总支出 == 遍历表格行累加的结果
4. 筛选后统计只算筛出来的那部分（缺陷 #2）
5. 日期范围模式：起止控件可见且可改（缺陷 #3）
6. 空库启动不崩，显示 0 条
7. 删除后表格与统计同步刷新
8. `AccountDialog` 对空名称 / 非数字金额 / 负数 / 未来日期的拒绝

---

## 8. 明确不做（YAGNI）

- 不引入 matplotlib / 图表（用户已排除）
- 不做分类统计面板（属范围 C）
- 不改 `main.py` 与 CLI 行为
- 不拆 `gui/` 包（用户已选单文件方案）
- 不动 `account_manager.py`、`export.py`、`input_skills.py`、`logger.py`
- 不做分页（个人账单量级不需要）
