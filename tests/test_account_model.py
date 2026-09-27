from account_model import Account


def test_account_create():
    account = Account(
        1,
        "早餐",
        15,
        "支出",
        "2026-09-26"
    )

    assert account.id == 1
    assert account.name == "早餐"
    assert account.price == 15
    assert account.type == "支出"
    assert account.date == "2026-09-26"


def test_account_is_income():
    account = Account(
        1,
        "工资",
        5000,
        "收入",
        "2026-09-26"
    )

    assert account.is_income() is True
    assert account.is_expense() is False


def test_account_is_expense():
    account = Account(
        2,
        "早餐",
        15,
        "支出",
        "2026-09-26"
    )

    assert account.is_expense() is True
    assert account.is_income() is False