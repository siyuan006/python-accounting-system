# 这里是备份与恢复数据代码

import shutil
from logger import logger
from config import DATABASE, BACKUP_DIR
import os


def backup_database():
    try:
        backup_file = os.path.join(
            BACKUP_DIR,
            "accounts_backup.db"
        )

        shutil.copy(DATABASE, backup_file)

        logger.info("数据库备份成功")

        print("数据库备份成功！")
        print(f"备份文件：{backup_file}")

    except FileNotFoundError:
        logger.error("找不到数据库文件")
        print("找不到数据库文件")


def restore_database(confirm=True):
    if confirm:
        answer = input(
            "恢复数据库会覆盖当前数据，确定吗？(yes/no)："
        )

        if answer.lower() != "yes":
            print("已取消恢复")
            return

    try:
        backup_file = os.path.join(
            BACKUP_DIR,
            "accounts_backup.db"
        )

        shutil.copy(backup_file, DATABASE)

        logger.info("数据库恢复成功")

        print("数据库恢复成功！")

    except FileNotFoundError:
        logger.error("找不到数据库备份文件")
        print("找不到数据库备份文件")