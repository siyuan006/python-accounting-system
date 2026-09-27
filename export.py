import csv
import os

from database import get_accounts
from logger import logger
from config import EXPORT_DIR


def export_accounts():
    try:
        file_path = os.path.join(
            EXPORT_DIR,
            "accounts.csv"
        )

        accounts = get_accounts()

        with open(
            file_path,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "ID",
                "名称",
                "金额",
                "类型",
                "日期"
            ])

            for account in accounts:
                writer.writerow([
                    account.id,
                    account.name,
                    account.price,
                    account.type,
                    account.date
                ])

        logger.info("账单导出成功")

        print("账单导出成功！")
        print(f"导出文件：{file_path}")

    except OSError as e:
        logger.error(f"账单导出失败：{e}")
        print("账单导出失败")