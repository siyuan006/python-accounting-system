import sqlite3

# 数据库连接函数
def get_connection():
    conn = sqlite3.connect("accounts.db")
    # sqlite.3connect意思是打开accounts.db，不存在就创建
    return conn

#
def create_table():
    conn = get_connection()
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
    conn.close()

# CREATE TABLE
# 创建表。
# IF NOT EXISTS
# 如果表已经存在，就不要重复创建。
# PRIMARY KEY
# 主键。
# AUTOINCREMENT
# commit()
# 保存数据库修改

# 添加数据
def insert_account(name, price, account_type, date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO accounts (name, price, type,date)
        VALUES (?, ?, ?,?)
        """,
        (name, price, account_type, date)
    )
    conn.commit()
    conn.close()

# 查询数据
def get_accounts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts")
    accounts = cursor.fetchall()
    conn.close()
    return accounts

def delete_account_db(account_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()

def update_account_db(account_id, name, price, account_type,date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE accounts
        SET name = ?, price = ?, type = ?, date = ?
        WHERE id = ?
        """,
        (name, price, account_type, date, account_id)
    )
    conn.commit()
    result = cursor.rowcount
    conn.close()
    return result

def get_money_count():
    conn = get_connection()
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
    conn.close()
    if total_income is None:
        total_income = 0
    if total_expense is None:
        total_expense = 0
    return total_income, total_expense

def get_account_by_date(date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM accounts WHERE date = ?', (date,)
    )
    account = cursor.fetchall()
    conn.close()
    return account

def get_money_count_by_date(account_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(price) FROM accounts WHERE type = ? and date = ?",('收入',account_date)
    )
    total_income = cursor.fetchone()[0]

    cursor.execute(
        "SELECT SUM(price) FROM accounts WHERE type = ? and date = ?",('支出',account_date)
    )
    total_expense = cursor.fetchone()[0]
    conn.close()
    if total_income is None:
        total_income = 0
    if total_expense is None:
        total_expense = 0
    return total_income, total_expense

if __name__ == "__main__":
    accounts = get_accounts()
    print(accounts)



