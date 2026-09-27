import account_manager
import database
import pytest
from account_model import Account


@pytest.fixture
def test_manager(tmp_path):
    test_database = tmp_path / "test_accounts.db"

    database.DATABASE = str(test_database)
    database.create_table()

    manager = account_manager.AccountManager()

    yield manager

    database.DATABASE = "accounts.db"

def test_add_account(test_manager, monkeypatch):
    inputs = iter([
        "早餐",
        "20",
        "支出",
        "1"
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(inputs)
    )

    test_manager.add_account()

    accounts = database.get_accounts()

    assert len(accounts) == 1
    assert accounts[0].name == "早餐"
    assert accounts[0].price == 20
    assert accounts[0].type == "支出"

def test_delete_account(test_manager, monkeypatch):
    # 先准备一条测试数据
    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-26"
    )

    # 模拟用户输入：删除第 1 条
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "1"
    )

    test_manager.delete_account()

    accounts = database.get_accounts()

    assert len(accounts) == 0

def test_delete_account_when_empty(test_manager, monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "1"
    )

    test_manager.delete_account()

    accounts = database.get_accounts()

    assert len(accounts) == 0

def test_delete_account_invalid_index(test_manager, monkeypatch):
    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-26"
    )

    inputs = iter([
        "5",
        "1"
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(inputs)
    )

    test_manager.delete_account()

    accounts = database.get_accounts()

    assert len(accounts) == 0

def test_update_account(test_manager, monkeypatch):
    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-26"
    )

    inputs = iter([
        "1",       # 修改第1条
        "午餐",    # 新名称
        "30",      # 新金额
        "支出",    # 新类型
        "1"        # 保持原日期
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(inputs)
    )

    test_manager.update_account()

    accounts = database.get_accounts()

    assert len(accounts) == 1
    assert accounts[0].name == "午餐"
    assert accounts[0].price == 30
    assert accounts[0].type == "支出"
    assert accounts[0].date == "2026-09-26"

def test_update_account_change_date(test_manager, monkeypatch):
    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-01"
    )

    inputs = iter([
        "1",
        "午餐",
        "30",
        "支出",
        "4",
        "2026-09-05"
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(inputs)
    )

    test_manager.update_account()

    accounts = database.get_accounts()

    assert accounts[0].name == "午餐"
    assert accounts[0].price == 30
    assert accounts[0].date == "2026-09-05"

def test_show_accounts_by_date(test_manager, monkeypatch, capsys):
    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-01"
    )

    database.insert_account(
        "午餐",
        30,
        "支出",
        "2026-09-01"
    )

    database.insert_account(
        "购物",
        500,
        "支出",
        "2026-09-02"
    )

    # 模拟输入日期
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "2026-09-01"
    )

    test_manager.show_accounts_by_date()

    captured = capsys.readouterr()

    assert "早餐" in captured.out
    assert "午餐" in captured.out
    assert "购物" not in captured.out

def test_show_accounts_by_date(test_manager, monkeypatch, capsys):
    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-01"
    )

    database.insert_account(
        "午餐",
        30,
        "支出",
        "2026-09-01"
    )

    database.insert_account(
        "购物",
        500,
        "支出",
        "2026-09-02"
    )

    # 模拟输入日期
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "2026-09-01"
    )

    test_manager.show_accounts_by_date()

    captured = capsys.readouterr()

    assert "早餐" in captured.out
    assert "午餐" in captured.out
    assert "购物" not in captured.out

def test_show_accounts_by_month(test_manager, monkeypatch, capsys):
    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-01"
    )

    database.insert_account(
        "工资",
        5000,
        "收入",
        "2026-09-15"
    )

    database.insert_account(
        "购物",
        500,
        "支出",
        "2026-08-20"
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "2026-09"
    )

    test_manager.show_accounts_by_month()

    captured = capsys.readouterr()

    assert "早餐" in captured.out
    assert "工资" in captured.out
    assert "购物" not in captured.out

def test_sort_accounts_price_asc(test_manager):
    accounts = [
        Account(1, "购物", 500, "支出", "2026-09-20"),
        Account(2, "早餐", 20, "支出", "2026-09-01"),
        Account(3, "午餐", 30, "支出", "2026-09-10")
    ]

    result = test_manager.sort_accounts(accounts, "price_asc")

    prices = [account.price for account in result]

    assert prices == [20, 30, 500]

def test_sort_accounts_price_desc(test_manager):
    accounts = [
        Account(1, "购物", 500, "支出", "2026-09-20"),
        Account(2, "早餐", 20, "支出", "2026-09-01"),
        Account(3, "午餐", 30, "支出", "2026-09-10")
    ]

    result = test_manager.sort_accounts(accounts, "price_desc")

    prices = [account.price for account in result]

    assert prices == [500, 30, 20]

def test_sort_accounts_date_asc(test_manager):
    accounts = [
        Account(1, "购物", 500, "支出", "2026-09-20"),
        Account(2, "早餐", 20, "支出", "2026-09-01"),
        Account(3, "午餐", 30, "支出", "2026-09-10")
    ]

    result = test_manager.sort_accounts(accounts, "date_asc")

    dates = [account.date for account in result]

    assert dates == [
        "2026-09-01",
        "2026-09-10",
        "2026-09-20"
    ]

def test_sort_accounts_date_desc(test_manager):
    accounts = [
        Account(1, "购物", 500, "支出", "2026-09-20"),
        Account(2, "早餐", 20, "支出", "2026-09-01"),
        Account(3, "午餐", 30, "支出", "2026-09-10")
    ]

    result = test_manager.sort_accounts(accounts, "date_desc")

    dates = [account.date for account in result]

    assert dates == [
        "2026-09-20",
        "2026-09-10",
        "2026-09-01"
    ]

def test_sort_accounts_invalid_type(test_manager):
    accounts = [
        Account(1, "购物", 500, "支出", "2026-09-20"),
        Account(2, "早餐", 20, "支出", "2026-09-01")
    ]

    result = test_manager.sort_accounts(accounts, "abc")

    assert result == accounts