from account_manager import AccountManager
from export import export_accounts
from backup import backup_database, restore_database
from database import create_table



create_table()
manager = AccountManager()
actions = {
    "1": manager.show_accounts,
    "2": manager.add_account,
    "3": manager.count_money,
    "4":manager.delete_account,
    "5": manager.update_account,
    "6": manager.show_accounts_by_date,
    "7": manager.show_accounts_by_month,
    "8": manager.count_money_by_date,
    "9": manager.count_money_by_month,
    "10":manager.category_statistics,
    '11':manager.sort_menu,
    "12": manager.search_menu,
    '13':manager.search_accounts_by_date_range,
    '14':export_accounts,
    "15": backup_database,
    "16": restore_database
 }
while True:
    print('=====================')
    print('      我的记账软件      ')
    print('=====================\n')
    print('1.查看账单')
    print('2.添加账单')
    print('3.统计余额')
    print('4.删除账单')
    print('5.修改账单')
    print('6.按日期查看账单')
    print('7.按月份查看账单')
    print('8.按日期统计账单')
    print('9.按月份统计账单')
    print('10.分类统计')
    print('11.排序')
    print('12.搜索账单')
    print('13.日期范围统计')
    print('14.导出账单')
    print('15.备份数据库')
    print('16.恢复数据库')
    print('17.退出')

    choice = input('需要进行的操作：')
    if choice == "16":
        break

    if choice in actions:
        actions[choice]()
    else:
        print("请输入1-17")




