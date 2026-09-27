import sqlite3
import pytest
import database


@pytest.fixture
def test_db(tmp_path):
    test_database = tmp_path / "test_accounts.db"

    database.DATABASE = str(test_database)

    database.create_table()

    yield


@pytest.fixture(autouse=True)
def reset_database():
    yield
    database.DATABASE = "accounts.db"


def test_insert_account(test_db):
    result = database.insert_account(
        "早餐",
        15,
        "支出",
        "2026-09-26"
    )

    assert result is True


def test_get_accounts(test_db):
    database.insert_account(
        "早餐",
        15,
        "支出",
        "2026-09-26"
    )

    accounts = database.get_accounts()

    assert len(accounts) == 1
    assert accounts[0].name == "早餐"
    assert accounts[0].price == 15
    assert accounts[0].type == "支出"
    assert accounts[0].date == "2026-09-26"

def test_update_account(test_db):
    database.insert_account(
        "早餐",
        15,
        "支出",
        "2026-09-26"
    )

    accounts = database.get_accounts()

    account_id = accounts[0].id

    result = database.update_account_db(
        account_id,
        "午餐",
        30,
        "支出",
        "2026-09-26"
    )

    assert result is True

    accounts = database.get_accounts()

    assert len(accounts) == 1
    assert accounts[0].name == "午餐"
    assert accounts[0].price == 30

def test_delete_account(test_db):
    database.insert_account(
        "早餐",
        15,
        "支出",
        "2026-09-26"
    )

    accounts = database.get_accounts()

    account_id = accounts[0].id

    result = database.delete_account_db(account_id)

    assert result is True

    accounts = database.get_accounts()

    assert len(accounts) == 0

def test_delete_not_found(test_db):
    result = database.delete_account_db(99999)

    assert result is False

def test_get_money_count(test_db):
    database.insert_account(
        "工资",
        5000,
        "收入",
        "2026-09-01"
    )

    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-02"
    )

    database.insert_account(
        "购物",
        500,
        "支出",
        "2026-09-03"
    )

    total_income, total_expense = database.get_money_count()

    assert total_income == 5000
    assert total_expense == 520

def test_get_money_count_by_date(test_db):
    database.insert_account(
        "工资",
        5000,
        "收入",
        "2026-09-01"
    )

    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-01"
    )

    database.insert_account(
        "购物",
        500,
        "支出",
        "2026-09-02"
    )

    total_income, total_expense = (
        database.get_money_count_by_date("2026-09-01")
    )

    assert total_income == 5000
    assert total_expense == 20

def test_get_money_count_by_month(test_db):
    database.insert_account(
        "工资",
        5000,
        "收入",
        "2026-09-01"
    )

    database.insert_account(
        "工资",
        3000,
        "收入",
        "2026-09-15"
    )

    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-05"
    )

    database.insert_account(
        "购物",
        500,
        "支出",
        "2026-08-20"
    )

    total_income, total_expense = (
        database.get_money_count_by_month("2026-09")
    )

    assert total_income == 8000
    assert total_expense == 20

def test_get_money_count_by_date_range(test_db):
    database.insert_account(
        "工资",
        5000,
        "收入",
        "2026-09-01"
    )

    database.insert_account(
        "工资",
        3000,
        "收入",
        "2026-09-15"
    )

    database.insert_account(
        "购物",
        500,
        "支出",
        "2026-09-10"
    )

    database.insert_account(
        "餐饮",
        100,
        "支出",
        "2026-09-25"
    )

    database.insert_account(
        "其他",
        200,
        "支出",
        "2026-09-26"
    )

    total_income, total_expense = (
        database.get_money_count_by_date_range(
            "2026-09-01",
            "2026-09-25"
        )
    )

    assert total_income == 8000
    assert total_expense == 600

def test_get_account_by_date(test_db):
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

    accounts = database.get_account_by_date("2026-09-01")

    assert len(accounts) == 2
    assert accounts[0].name == "早餐"
    assert accounts[1].name == "午餐"

def test_get_account_by_month(test_db):
    database.insert_account(
        "工资",
        5000,
        "收入",
        "2026-09-01"
    )

    database.insert_account(
        "早餐",
        20,
        "支出",
        "2026-09-15"
    )

    database.insert_account(
        "购物",
        500,
        "支出",
        "2026-08-20"
    )

    accounts = database.get_account_by_month("2026-09")

    assert len(accounts) == 2
    assert accounts[0].date == "2026-09-01"
    assert accounts[1].date == "2026-09-15"

def test_get_money_by_category(test_db):
    database.insert_account(
        "餐饮",
        20,
        "支出",
        "2026-09-01"
    )

    database.insert_account(
        "餐饮",
        30,
        "支出",
        "2026-09-02"
    )

    database.insert_account(
        "购物",
        100,
        "支出",
        "2026-09-03"
    )

    result = database.get_money_by_category("支出")

    assert ("购物", 100) in result
    assert ("餐饮", 50) in result

def test_get_money_by_category_by_month(test_db):
    database.insert_account(
        "餐饮",
        20,
        "支出",
        "2026-09-01"
    )

    database.insert_account(
        "餐饮",
        30,
        "支出",
        "2026-09-10"
    )

    database.insert_account(
        "餐饮",
        100,
        "支出",
        "2026-08-20"
    )

    result = database.get_money_by_category(
        "支出",
        "2026-09"
    )

    assert ("餐饮", 50) in result