from account import (
    add_account,
    show_accounts,
    delete_account,
    update_account,
    count_money,
    show_accounts_by_date,
    count_money_by_date
)
from database import create_table

create_table()
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
    print('7.查询日期统计')
    print('8.退出')
    try:
        choice = int(input('需要进行的操作：'))
    except ValueError:
        print('输入错误')
        continue
    if choice == 1:
        show_accounts()
    elif choice == 2:
        add_account()
    elif choice == 3:
        count_money()
    elif choice == 4:
        delete_account()
    elif choice == 5:
        update_account()
    elif choice == 6:
        show_accounts_by_date()
    elif choice == 7:
        count_money_by_date()
    elif choice == 8:
        break
    else:
        print('请输入1-8')





