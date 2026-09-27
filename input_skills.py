from datetime import datetime,timedelta



class InputSkills:
    # 输入日期函数
    @staticmethod
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

    # 输入价格函数
    @staticmethod
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

    # 输入类型函数
    @staticmethod
    def input_account_type():
        while True:
            account_type = input("请输入类型（收入/支出）：")
            if account_type not in ["收入", "支出"]:
                print("类型只能是收入或支出")
                continue
            return account_type

    # 输入日期函数
    @staticmethod
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
                return InputSkills.input_date()
            else:
                print("请输入 1-3")

    # 更新日期函数
    @staticmethod
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
                return InputSkills.input_date()
            else:
                print("请输入 1-4")

    # 输入月份函数
    @staticmethod
    def input_month():
        while True:
            month = input("请输入月份（YYYY-MM）：")

            try:
                datetime.strptime(month, "%Y-%m")
            except ValueError:
                print("月份格式错误，请使用 YYYY-MM")
                continue

            today = datetime.now().date()

            current_month = today.strftime("%Y-%m")

            if month > current_month:
                print("不能查询未来月份")
                continue

            return month




