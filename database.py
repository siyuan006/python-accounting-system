import sqlite3
from logger import logger
from account_model import Account
from config import DATABASE



#创建accounts表
def create_table():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    type TEXT NOT NULL,
                    date TEXT NOT NULL
                )
            """)
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f'创建accounts表失败：{e}')
        print('创建表失败')
        return

# 转换函数
def row_to_account(row):
    return Account(
        row[0],
        row[1],
        row[2],
        row[3],
        row[4]
    )

# 添加数据
def insert_account(name, price, type, date):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO accounts (name, price, type, date)
                VALUES (?, ?, ?, ?)
                """,
                (name, price, type, date)
            )

            conn.commit()

            logger.info(
                f"添加账单成功：{name} | {price} | {type} | {date}"
            )

            return True

    except sqlite3.Error as e:
        logger.error(f"添加账单失败：{e}")
        return False

# 查询数据
def get_accounts():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM accounts")
            rows = cursor.fetchall()

            accounts = []

            for row in rows:
                accounts.append(row_to_account(row))
            return accounts

    except sqlite3.Error as e:
        logger.error(f"查询账单失败：{e}")
        print("数据库查询失败，请稍后重试")
        return []

def delete_account_db(account_id):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM accounts WHERE id = ?",
                (account_id,)
            )

            if cursor.rowcount == 0:
                logger.warning(
                    f"删除账单失败：没有找到 id={account_id} 的账单"
                )
                return False

            conn.commit()

            logger.info(
                f"删除账单成功：id={account_id}"
            )

            return True

    except sqlite3.Error as e:
        logger.error(
            f"删除账单时发生数据库错误：{e}"
        )
        return False

def update_account_db(account_id, name, price, account_type, date):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE accounts
                SET name = ?, price = ?, type = ?, date = ?
                WHERE id = ?
                """,
                (name, price, account_type, date, account_id)
            )

            if cursor.rowcount == 0:
                logger.warning(
                    f"修改账单失败：没有找到 id={account_id} 的账单"
                )
                return False

            conn.commit()

            logger.info(
                f"修改账单成功：id={account_id}"
            )

            return True

    except sqlite3.Error as e:
        logger.error(
            f"修改账单时发生数据库错误：{e}"
        )
        return False

def get_money_count():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT SUM(price) FROM accounts WHERE type = ?",
                ("收入",)
            )
            total_income = cursor.fetchone()[0]

            cursor.execute(
                "SELECT SUM(price) FROM accounts WHERE type = ?",
                ("支出",)
            )
            total_expense = cursor.fetchone()[0]

            if total_income is None:
                total_income = 0

            if total_expense is None:
                total_expense = 0

            return total_income, total_expense

    except sqlite3.Error as e:
        logger.error(f"统计余额失败：{e}")
        print("数据库统计失败，请稍后重试")
        return 0, 0

def get_account_by_date(date):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM accounts WHERE date = ?', (date,)
            )
            rows = cursor.fetchall()

            accounts = []

            for row in rows:
                accounts.append(row_to_account(row))
            return accounts
    except sqlite3.Error as e:
        logger.error(f'查询日期账单失败:{e}')
        print('数据库查询失败，请稍后重试')
        return []

def get_money_count_by_date(account_date):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT SUM(price)
                FROM accounts
                WHERE type = ? AND date = ?
                """,
                ("收入", account_date)
            )

            total_income = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT SUM(price)
                FROM accounts
                WHERE type = ? AND date = ?
                """,
                ("支出", account_date)
            )

            total_expense = cursor.fetchone()[0]

            if total_income is None:
                total_income = 0

            if total_expense is None:
                total_expense = 0

            return total_income, total_expense

    except sqlite3.Error as e:
        logger.error(
            f"按日期统计失败：{e}"
        )
        print("数据库统计失败，请稍后重试")
        return 0, 0

def get_account_by_month(account_month):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                    SELECT * FROM accounts
                    WHERE date LIKE?
                    ORDER BY date
                    """,
        (account_month + "%",)
            )
            accounts = []
            rows = cursor.fetchall()
            for row in rows:
                accounts.append(row_to_account(row))
            return accounts
    except sqlite3.Error as e:
        logger.error(f'按月份查询账单失败:{e}')
        print("数据库统计失败，请稍后重试")
        return []



# 按月份统计金额
def get_money_count_by_month(account_month):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(
            """
            SELECT SUM(price)
            FROM accounts
            WHERE type = ? AND date LIKE ?
            """,
            ("收入", account_month + "%")
        )
            total_income = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT SUM(price)
                FROM accounts
                WHERE type = ? AND date LIKE ?
                """,
                ("支出", account_month + "%")
            )
            total_expense = cursor.fetchone()[0]
            if total_income is None:
                total_income = 0
            if total_expense is None:
                total_expense = 0
            return total_income, total_expense
    except sqlite3.Error as e:
        logger.error(f'按月份统计金额失败：{e}')
        print("数据库统计失败，请稍后重试")
        return []


# 代码重构（账单类型与时间查询）
def get_money_by_category(account_type, account_month=None):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            if account_month is None:
                cursor.execute(
                    """
                    SELECT name, SUM(price)
                    FROM accounts
                    WHERE type = ?
                    GROUP BY name
                    ORDER BY SUM(price) DESC
                    """,
                    (account_type,)
                )
            else:
                cursor.execute(
                    """
                    SELECT name, SUM(price)
                    FROM accounts
                    WHERE type = ? AND date LIKE ?
                    GROUP BY name
                    ORDER BY SUM(price) DESC
                    """,
                    (account_type, account_month + "%")
                )
            result = cursor.fetchall()
            return result
    except sqlite3.Error as e:
        logger.error(f'账单类型与时间查询失败：{e}')
        print("数据库统计失败，请稍后重试")
        return []

# 模糊搜索功能
def search_accounts(
        keyword=None,
        account_type=None,
        account_month=None,
        start_date=None,
        end_date=None
):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            sql = """
                SELECT *
                FROM accounts
                WHERE 1 = 1
            """

            params = []

            # 名称关键词
            if keyword:
                sql += " AND name LIKE ?"
                params.append(f"%{keyword}%")

            # 收入 / 支出
            if account_type:
                sql += " AND type = ?"
                params.append(account_type)

            # 月份
            if account_month:
                sql += " AND date LIKE ?"
                params.append(f"{account_month}%")

            # 日期范围
            if start_date and end_date:
                sql += " AND date BETWEEN ? AND ?"
                params.append(start_date)
                params.append(end_date)

            sql += " ORDER BY date DESC"

            cursor.execute(sql, params)

            rows = cursor.fetchall()

            accounts = []

            for row in rows:
                accounts.append(
                    Account(
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4]
                    )
                )

            return accounts

    except sqlite3.Error as e:
        logger.error(f"搜索账单失败：{e}")
        print("数据库查询失败，请稍后重试")
        return []

#     统计某段时间金额方法
def get_money_count_by_date_range(start_date, end_date):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT SUM(price)
                FROM accounts
                WHERE type = ?
                AND date BETWEEN ? AND ?
                """,
                ("收入", start_date, end_date)
            )

            total_income = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT SUM(price)
                FROM accounts
                WHERE type = ?
                AND date BETWEEN ? AND ?
                """,
                ("支出", start_date, end_date)
            )

            total_expense = cursor.fetchone()[0]

            if total_income is None:
                total_income = 0

            if total_expense is None:
                total_expense = 0

            return total_income, total_expense

    except sqlite3.Error as e:
        logger.error(
            f"按日期范围统计失败：{e}"
        )
        print("数据库统计失败，请稍后重试")
        return 0, 0

def get_accounts_by_date_range(start_date, end_date):
    try:
        with sqlite3.connect("accounts.db") as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT *
                FROM accounts
                WHERE date BETWEEN ? AND ?
                ORDER BY date
                """,
                (start_date, end_date)
            )

            rows = cursor.fetchall()

            accounts = []

            for row in rows:
                accounts.append(
                    Account(
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4]
                    )
                )

            return accounts

    except sqlite3.Error as e:
        logger.error(f"按日期范围查询失败：{e}")
        return []


if __name__ == "__main__":
    pass