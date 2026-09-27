

class Account:
    def __init__(self,account_id,name,price,account_type,date):
        self.id = account_id
        self.name = name
        self.price = price
        self.type = account_type
        self.date = date

    def show(self):
        print(
            f'{self.name} |'
            f'{self.price}元 |'
            f'{self.type} |'
            f'{self.date}'
        )

    def is_income(self):
        return self.type == "收入"

    def is_expense(self):
        return self.type == "支出"
