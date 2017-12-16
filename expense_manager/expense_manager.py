from datetime import datetime
from uuid import uuid4
import pathlib
from os.path import join, exists, isdir
import os
import sys
from getpass import getpass

from cmd2 import Cmd
import dataset
from sqlalchemy.exc import OperationalError
from colorama import init, Fore, Back, Style, deinit
from termcolor import colored
from tabulate import tabulate

class ExpenseManager(Cmd):
    intro = colored('Welcome to your personal Expense Manager!\n', 'blue')
    prompt = colored('Expense Manager () >>> ', attrs=['bold'])
    timing = False

    def _col(self, s, *args, **kwargs):
        print(colored(s, *args, **kwargs))

    def _update_prompt(self):
        total_tab = self.db['totals']
        total = total_tab.find_one(account_name=self.account_name)['amount']
        total = round(total, 2)
        if total > 0:
            total = str(colored(f'{total}', 'green'))
        else:
            total = str(colored(f'{total}', 'red'))
        self.prompt = colored(f'Expense Manager ({self.account_name}, {total}) >>> ',
                          attrs=['bold'])

    def _pretty_print_info(self, rows=0):
        res = []
        tab = self.db[self.account_name]
        if rows == 0: # everything
            for i in tab.find(order_by='timestamp'):
                res.append((i['id'],
                            i['timestamp'],
                            i['amount'],
                            i['comment'],))
        else: # limit to n rows
            for i in tab.find(order_by='-timestamp', _limit=rows):
                res.append((i['id'],
                            i['timestamp'],
                            i['amount'],
                            i['comment'],))
        self._col(
            tabulate(
                res,
                headers=['id', 'time', 'amount', 'comment'],
                tablefmt='fancy_grid',
            ),
           'yellow',
            #attrs=['bold'],
        )

    def preloop(self, *args, **kwargs):
        init() # colorama startup
        self.account_name = ''
        self.db_path = join(str(pathlib.Path.home()), 'expense_manager')
        try:
            pathlib.Path(self.db_path).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(e)
            sys.exit('Failed to create the data directory!')
        self.db_name = str(input('Username: ')).lower() + '_expense_manager.db'
        url = 'sqlite+pysqlcipher://:{}@/{}?cipher=aes-256-cfb&kdf_iter=64000'.format(
            getpass(),
            join(self.db_path, self.db_name),
        )
        self.db = dataset.connect(url)
        self.db.create_table('totals')

        return super().preloop(*args, **kwargs)

    def postloop(self, *args, **kwargs):
        self.db.engine.dispose()
        deinit() # colorama shutdown

        return super().postloop(*args, **kwargs)

    def do_use(self, arg):
        'Makes the given account active.'
        arg = arg.split()
        if arg:
            if not self.db['totals'].find_one(account_name=arg[0]):
                self._col('Creating a new account named: {arg[0]}')
                self.db['totals'].insert(dict(
                    amount=0,
                    account_name=arg[0],
                    timestamp=datetime.now()
                ))
            self.account_name = arg[0]
            self._update_prompt()
        else:
            self._col('You must provide an account name!', 'red')

    def do_add(self, arg):
        'Adds a transaction for the active account.'
        arg = arg.split()
        if self.account_name:
            totals_tab = self.db['totals']
            prev = totals_tab.find_one(account_name=self.account_name)['amount']
            self.db.begin() # transaction start
            amount = float(arg[0])
            self.db[self.account_name].insert(dict(
                amount=amount,
                timestamp=datetime.now(),
                comment=' '.join(arg[1:])
            ))
            totals_tab.upsert(dict(
                account_name=self.account_name,
                timestamp=datetime.now(),
                amount=round(prev + amount, 2)
            ), ['account_name'])
            self.db.commit() # transaction end
            if amount > 0:
                amount = colored(str(amount), 'green', attrs=['bold'])
            else:
                amount = colored(str(amount), 'red', attrs=['bold'])
            self._col('Added ' + amount + f' in {self.account_name}.')
            self._update_prompt()

    def do_show(self, arg):
        'Prints brief infos on the latest transactions of the active account.'
        arg = arg.split()
        res = []
        if self.account_name:
            try:
                if arg[0] == 'all':
                    self._pretty_print_info()
                else:
                    self._pretty_print_info(rows=arg[0])
            except IndexError: # no arg provided
                self._col('Number not valid!', 'red', attrs=['bold'])
        else:
            self._col('No account selected.', 'red', attrs=['bold'])

    def do_list_accounts(self, arg):
        'Lists the name of the created accounts for the logged in username.'
        arg = arg.split()
        accounts = []
        for i in self.db['totals']:
            accounts.append(i['account_name'])
        self._col(accounts, 'yellow')

    def do_inspect(self, arg):
        'Checks amount of transactions for the active account.'
        arg = arg.split()
        if arg:
            length = str(len(self.db[arg[0]]))
            self._col(length + f" transactions on account '{arg[0]}'.")
        elif self.account_name:
            length = str(len(self.account_name))
            self._col(length + f" transactions on account '{self.account_name}'.")
        else:
            self._col('No account selected.')

    def do_out(self, arg):
        'Exits selected account.'
        if self.account_name:
            do_use('')
        else:
            self._col('No account selected. Nothing to do.', 'red')

    def do_delete(self, arg):
        'Deletes the provided transaction ID.'
        arg = arg.split()
        if self.account_name:
            table = self.db[self.account_name]
            totals_tab = self.db['totals']
            row = table.find_one(id=arg[0])
            if row:
                prev = totals_tab.find_one(account_name=self.account_name)
                self.db.begin() # transaction start
                totals_tab.update(dict(
                    account_name=self.account_name,
                    amount=prev['amount'] - row['amount'],
                ), ['account_name'])
                table.delete(id=arg[0])
                self.db.commit() # transaction end
        self._update_prompt()

def start():
    ExpenseManager().cmdloop()

if __name__ == '__main__':
    ExpenseManager().cmdloop()
