from database import (
    get_accounts,
    insert_account,
    delete_account_db,
    update_account_db,
    get_money_count,
    get_account_by_date,
    get_money_count_by_date
)
from datetime import datetime,timedelta

# 查看账单
def show_accounts():
    print("\n======== 账单 ========")
    accounts = get_accounts()
    if not accounts:
        print("暂无账单")
        return
    for index, account in enumerate(accounts, start=1):
        print(
            f"{index}.{account[1]} | {account[2]}元 | {account[3]} | {account[4]}"
        )


# 添加账单
def add_account():
    name = input("请输入账单名称：")
    price = input_price()
    account_type = input_account_type()
    account_date = input_account_date()
    insert_account(name, price, account_type, account_date)
    print("添加成功！")

# 统计余额
def count_money():
    total_income, total_expense = get_money_count()
    balance = total_income - total_expense
    print(f"总收入：{total_income}")
    print(f"总支出：{total_expense}")
    print(f"余额：{balance}")

#删除账单
def delete_account():
    accounts = get_accounts()
    if not accounts:
        print('暂无账单')
        return
    account_delete = 0
    while True:
        try:
            account_delete = int(input("需要删除的账单："))
        except ValueError:
            print("请输入正确的数字序号")
            continue
        if not 1 <= account_delete <= len(accounts):
            print("未找到该账单")
            continue
        break
    account_id = accounts[account_delete - 1][0]
    delete_account_db(account_id)
    print("删除成功")

# 修改账单
def update_account():
    accounts = get_accounts()
    account_update_index = 0
    while True:
        try:
            account_update_index = int(input('修改的序号：'))
        except ValueError:
            print('请输入序号')
            continue
        if not 1 <= account_update_index <= len(accounts):
            print("请输入正确的账单序号")
            continue
        break
    account_id = accounts[account_update_index - 1][0]
    old_date = accounts[account_update_index - 1][4]
    account_update_name = input('名称：')
    account_update_price = input_price()
    account_update_type = input_account_type()
    account_update_date = input_update_date(old_date)
    result = update_account_db(account_id, account_update_name, account_update_price, account_update_type,account_update_date)
    if result == 1:
        print('修改成功')
    else:
        print('修改失败')

def show_accounts_by_date():
    date = input_date()
    print(f"\n======== {date} 账单 ========")
    accounts = get_account_by_date(date)
    if not accounts:
        print("暂无账单")
        return
    for index, account in enumerate(accounts, start=1):
        print(
            f"{index}.{account[1]} | {account[2]}元 | {account[3]} | {account[4]}"
        )

def count_money_by_date():
    date = input_date()
    total_income, total_expense = get_money_count_by_date(date)
    balance = total_income - total_expense
    print(f'\n======== {date} 统计 ========')
    print(f'总收入：{total_income}')
    print(f'总支出：{total_expense}')
    print(f'余额：{balance}')

def input_date():
    while True:
        date = input("请输入日期（YYYY-MM-DD）：")
        try:
            parsed_date = datetime.strptime(
                date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            print("日期格式错误，请使用 YYYY-MM-DD")
            continue
        today = datetime.now().date()
        if parsed_date > today:
            print("不能添加未来日期的账单")
            continue
        return date

# 代码重构（减少重复代码）
def input_price():
    while True:
        try:
            price = float(input("请输入金额："))
        except ValueError:
            print("金额必须是数字")
            continue
        if price <= 0:
            print("金额必须大于 0")
            continue
        return price

def input_account_type():
    while True:
        account_type = input("请输入类型（收入/支出）：")
        if account_type not in ["收入", "支出"]:
            print("类型只能是收入或支出")
            continue
        return account_type

def input_account_date():
    while True:
        print("1. 今天")
        print("2. 昨天")
        print("3. 自定义日期")
        choice = input("请选择日期方式：")
        if choice == "1":
            return datetime.now().strftime("%Y-%m-%d")
        elif choice == "2":
            return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        elif choice == "3":
            return input_date()
        else:
            print("请输入 1-3")

def input_update_date(old_date):
    while True:
        print("1. 保持原日期")
        print("2. 今天")
        print("3. 昨天")
        print("4. 自定义日期")
        choice = input("请选择日期：")
        if choice == "1":
            return old_date
        elif choice == "2":
            return datetime.now().strftime("%Y-%m-%d")
        elif choice == "3":
            return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        elif choice == "4":
            return input_date()
        else:
            print("请输入 1-4")









