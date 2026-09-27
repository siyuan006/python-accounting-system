from input_skills import InputSkills
from datetime import datetime
from database import (get_accounts,
    insert_account,
    get_account_by_date,
    get_money_count_by_date,
    get_account_by_month,
    update_account_db,
    delete_account_db,
    get_money_count_by_month,
    get_money_by_category,
    search_accounts,
    get_money_count_by_date_range
                      )



class AccountManager:

    def __init__(self):
        self.accounts = get_accounts()

    # 更新数据库数据函数
    def refresh_accounts(self):
        self.accounts = get_accounts()

    # 查看账单
    def show_accounts(self):
        print("\n======== 账单 ========")
        accounts = get_accounts()
        self.display_accounts(accounts)

# 添加账单
    def add_account(self):
        name = input("请输入账单名称：")
        price = InputSkills.input_price()
        account_type = InputSkills.input_account_type()
        date = InputSkills.input_account_date()
        result = insert_account(
            name,
            price,
            account_type,
            date
        )

        if result:
            self.refresh_accounts()
            print("添加成功！")
        else:
            print("添加失败！")


# 统计余额
    def count_money(self):
        total_income, total_expense = self.calculate_balance()

        self.show_money_result(
            total_income,
            total_expense
        )

    # 删除账单
    def delete_account(self):
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
        account_id = accounts[account_delete - 1].id

        result = delete_account_db(account_id)

        if result:
            self.refresh_accounts()
            print("删除成功")
        else:
            print("删除失败，未找到该账单")

    # 修改账单
    def update_account(self):
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
        account_id = accounts[account_update_index - 1].id
        old_date = accounts[account_update_index - 1].date
        account_update_name = input('名称：')
        account_update_price = InputSkills.input_price()
        account_update_type = InputSkills.input_account_type()
        account_update_date = InputSkills.input_update_date(old_date)
        result = update_account_db(account_id,
                                   account_update_name,
                                   account_update_price,
                                   account_update_type,
                                   account_update_date
                                   )
        if result:
            self.refresh_accounts()
            print('修改成功')
        else:
            print('修改失败，未找到该账单')

    def show_accounts_by_date(self):
        date = InputSkills.input_date()
        print(f"\n======== {date} 账单 ========")
        accounts = get_account_by_date(date)
        self.display_accounts(accounts)

    def count_money_by_date(self):
        date = InputSkills.input_date()
        total_income, total_expense = get_money_count_by_date(date)
        balance = total_income - total_expense
        print(f'\n======== {date} 统计 ========')
        self.show_money_result(
            total_income,
            total_expense
        )

    # 按月份查看账单
    def show_accounts_by_month(self):
        month = InputSkills.input_month()

        print(f"\n======== {month} 账单 ========")

        accounts = get_account_by_month(month)

        self.display_accounts(accounts)

    # 按月份统计金额
    def count_money_by_month(self):
        month = InputSkills.input_month()

        total_income, total_expense = get_money_count_by_month(month)

        balance = total_income - total_expense

        print(f"\n======== {month} 统计 ========")
        self.show_money_result(
            total_income,
            total_expense
        )



        # 统计菜单

    def category_statistics(self):
        while True:
            print("\n======== 分类统计 ========")
            print("1. 所有支出分类")
            print("2. 所有收入分类")
            print("3. 按月份统计支出")
            print("4. 按月份统计收入")
            print("5. 返回")

            choice = input("请选择：")

            if choice == "1":
               self.count_category("支出")

            elif choice == "2":
                self.count_category("收入")

            elif choice == "3":
                month = InputSkills.input_month()
                self.count_category("支出", month)

            elif choice == "4":
                month = InputSkills.input_month()
                self.count_category("收入", month)

            elif choice == "5":
                break

            else:
                print("请输入1-5")

        # 通用显示函数

    def count_category(account_type, account_month=None):
        result = get_money_by_category(account_type, account_month)

        if account_month:
            print(f"\n======== {account_month} {account_type}分类 ========")
        else:
            print(f"\n======== {account_type}分类 ========")

        if not result:
            print("暂无记录")
            return

        for name, total in result:
            print(f"{name}：{total}元")

    # 余额计算方法
    def calculate_balance(self):
        total_income = 0
        total_expense = 0

        for account in self.accounts:
            if account.is_income():
                total_income += account.price
            elif account.is_expense():
                total_expense += account.price

        return total_income, total_expense

# 统计方法
    def show_money_result(self, total_income, total_expense):
        balance = total_income - total_expense

        print(f"总收入：{total_income}")
        print(f"总支出：{total_expense}")
        print(f"余额：{balance}")


    # 显示账单
    def display_accounts(self, accounts):
        if not accounts:
            print("暂无账单")
            return

        for index, account in enumerate(accounts, start=1):
            print(f"{index}.", end="")
            account.show()

    # 排序
    def sort_accounts(self, accounts, sort_type):
        if sort_type == "date_asc":
            return sorted(accounts, key=lambda account: account.date)

        elif sort_type == "date_desc":
            return sorted(
                accounts,
                key=lambda account: account.date,
                reverse=True
            )

        elif sort_type == "price_asc":
            return sorted(accounts, key=lambda account: account.price)

        elif sort_type == "price_desc":
            return sorted(
                accounts,
                key=lambda account: account.price,
                reverse=True
            )

        return accounts

    # 排序菜单
    def sort_menu(self):
        accounts = get_accounts()

        if not accounts:
            print("暂无账单")
            return

        while True:
            print("\n======== 排序账单 ========")
            print("1. 按日期升序")
            print("2. 按日期降序")
            print("3. 按金额升序")
            print("4. 按金额降序")
            print("5. 返回")

            choice = input("请选择：")

            if choice == "1":
                accounts = self.sort_accounts(accounts, "date_asc")
                self.display_accounts(accounts)

            elif choice == "2":
                accounts = self.sort_accounts(accounts, "date_desc")
                self.display_accounts(accounts)

            elif choice == "3":
                accounts = self.sort_accounts(accounts, "price_asc")
                self.display_accounts(accounts)

            elif choice == "4":
                accounts = self.sort_accounts(accounts, "price_desc")
                self.display_accounts(accounts)

            elif choice == "5":
                break

            else:
                print("请输入1-5")

    # 搜索功能
    def search_account(self):
        print("\n======== 搜索账单 ========")

        keyword = input("请输入名称关键词（直接回车跳过）：").strip()

        print("\n类型：")
        print("1. 不限")
        print("2. 收入")
        print("3. 支出")

        type_choice = input("请选择：")

        if type_choice == "1":
            account_type = None
        elif type_choice == "2":
            account_type = "收入"
        elif type_choice == "3":
            account_type = "支出"
        else:
            print("请输入正确的选项")
            return

        account_month = input(
            "请输入月份（YYYY-MM，直接回车跳过）："
        ).strip()

        if account_month:
            try:
                datetime.strptime(account_month, "%Y-%m")
            except ValueError:
                print("月份格式错误")
                return

        accounts = search_accounts(
            keyword if keyword else None,
            account_type,
            account_month if account_month else None
        )

        print("\n======== 搜索结果 ========")

        self.display_accounts(accounts)

    # 日期范围搜索
    def search_menu(self):
        while True:
            print("\n======== 搜索账单 ========")
            print("1. 普通搜索")
            print("2. 日期范围搜索")
            print("3. 返回")

            choice = input("请选择：")

            if choice == "1":
                self.search_account()

            elif choice == "2":
                self.search_accounts_by_date_range()

            elif choice == "3":
                break

            else:
                print("请输入1-3")

    def search_accounts_by_date_range(self):
        print("\n======== 日期范围搜索 ========")

        start_date = InputSkills.input_date()
        end_date = InputSkills.input_date()

        if start_date > end_date:
            print("开始日期不能晚于结束日期")
            return

        print("\n类型：")
        print("1. 不限")
        print("2. 收入")
        print("3. 支出")

        choice = input("请选择：")

        if choice == "1":
            account_type = None

        elif choice == "2":
            account_type = "收入"

        elif choice == "3":
            account_type = "支出"

        else:
            print("请输入正确的选项")
            return

        accounts = search_accounts(
            account_type=account_type,
            start_date=start_date,
            end_date=end_date
        )

        print(
            f"\n======== "
            f"{start_date} 至 {end_date} "
            f"搜索结果 ========"
        )

        self.display_accounts(accounts)

    # 统计某段时间金额方法
    def count_money_by_date_range(self):
        print("\n======== 日期范围统计 ========")

        start_date = InputSkills.input_date()
        end_date = InputSkills.input_date()

        if start_date > end_date:
            print("开始日期不能晚于结束日期")
            return

        total_income, total_expense = get_money_count_by_date_range(
            start_date,
            end_date
        )

        print(
            f"\n======== "
            f"{start_date} 至 {end_date} 统计 ========"
        )

        self.show_money_result(
            total_income,
            total_expense
        )