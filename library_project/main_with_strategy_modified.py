"""
wytworcza, singleton
dekorator, adapter(do pobierania z isbn)
strategia, iterator

run in terminal(not run): python main.py
"""
import datetime
import random
from typing import Self
from abc import ABC, abstractmethod
import sqlite3
import typer
from rich import print
from rich.console import Console, RenderResult
from rich.markup import escape
from rich.text import Text
from rich.theme import Theme


app = typer.Typer()

themes = Theme({
    "default": "green",
    "warning": "yellow",
    "error": "red"
})


console = Console(theme=themes)


external_database = {
    "9791111111111": {
        "title": "The Sigma Protocol",
        "author": "Robert Ludlum",
        "year": 2001,
        "genre": "Mystery",
        "copies": 300,
    },
    "9792222222222": {
        "title": "Hobbit",
        "author": "JRR Tolkien",
        "year": 1937,
        "genre": "Fantasy",
        "copies": 851,
    },
    "9793333333333": {
        "title": "Assassin's Creed: Renaissance",
        "author": "Oliver Bowden",
        "year": 2009,
        "genre": "Fantasy",
        "copies": 999,
    },
    "9794444444444": {
        "title": "Apokalipsa Z: Początek końca",
        "author": "Manel Loureiro",
        "year": 2013,
        "genre": "Horror",
        "copies": 1200,
    },
    "9795555555555": {
        "title": "Władca Pierścieni",
        "author": "JRR Tolkien",
        "year": 1954,
        "genre": "Fantasy",
        "copies": 600,
    },
    "9796666666666": {
        "title": "To",
        "author": "Stephen King",
        "year": 1986,
        "genre": "Horror",
        "copies": 950,
    }
}


def generate_isbn():
    isbn = "978"
    for i in range(9):
        isbn += str(random.randint(0, 9))

    s = 0
    mult = [1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3]

    for i in range(12):
        s += int(isbn[i]) * mult[i]

    r = s % 10
    control_number = 10 - r

    if control_number == 10:
        control_number = 0

    isbn += str(control_number)

    return isbn


class DatabaseConnection:  # singleton
    _instance: Self = None

    def __new__(cls, *args, **kwargs) -> Self:
        if cls._instance is None:
            instance = super().__new__(cls) # , *args, **kwargs
            cls._instance = instance

        return cls._instance

    def __init__(self, database_name):
        self.database_name = database_name
        self.mydb = sqlite3.connect(self.database_name)  # commit
        self.cursor = self.mydb.cursor()  # mysql commands

        if self.cursor.execute("select name from sqlite_master where type='table'").fetchall() == []:
            # table creation
            self.cursor.execute("create table users(username varchar(255) primary key, password varchar(255), "
                                "name varchar(20), surname varchar(50), role varchar(255), logged_in int)")

            self.cursor.execute("create table notifications(username varchar(255), notification varchar(255))")

            self.cursor.execute("create table books(title varchar(255), author varchar(255), year int unsigned, "
                                "genre varchar(255), copies int unsigned, isbn varchar(13))")

            self.cursor.execute("create table in_possession(username varchar(255), title varchar(255))")

            self.cursor.execute("create table reservations(username varchar(255), title varchar(255))")
            # the same table as in_possession but works differently

            self.cursor.execute("create table history(id integer primary key autoincrement, username varchar(255), action varchar(20), title varchar(255), "
                                "author varchar(255), sql_command varchar(1000), reverse_sql_command varchar(1000))") # action = borrow/return

            # save tables/changes to db
            self.mydb.commit()
            console.print(f"Database {self.database_name} created", style="default")  # :boom:")
        else:
            console.print("Server has been successfully connected", style="default")
            pass

    def select(self, what: list, table: str, condition: dict = None) -> list:
        columns = ""
        for i in range(len(what)):
            if i == 0:
                columns = f"{what[i]}"
            else:
                columns += f", {what[i]}"

        if condition is not None and not ("distinct" in condition.keys() or ("distinct" in condition.values())):
            cond = ""
            n = 0
            for i in condition.keys():
                if i != "distinct":
                    if n == 0:
                        cond = f"{i} = ?"
                        n += 1
                    else:
                        cond += f" and {i} = ?"

            values = tuple(condition.values())
            selection = self.cursor.execute(f"select {columns} from {table} where {cond}", values).fetchall()

        elif condition is not None and ("distinct" in condition.keys() or ("distinct" in condition.values())):
            cond = ""
            n = 0
            for i in condition.keys():
                if i != "distinct":
                    if n == 0:
                        cond = f"{i} = ?"
                        n += 1
                    else:
                        cond += f" and {i} = ?"

            selection = self.cursor.execute(f"select distinct {columns} from {table}").fetchall()

        else:
            selection = self.cursor.execute(f"select {columns} from {table}").fetchall()
        return selection

    def update(self, what: list, values: list, table: str, condition: dict = None) -> None:
        columns = ""
        for i in range(len(what)):
            if i == 0:
                columns = f"{what[i]} = ?"
            else:
                columns += f", {what[i]} = ?"

        if condition is not None:
            cond = ""
            n = 0
            for i in condition.keys():
                if n == 0:
                    cond = f"{i} = ?"
                    n += 1
                else:
                    cond += f" and {i} = ?"

            all_values = tuple(values) + tuple(condition.values())

            self.cursor.execute(f"update {table} set {columns} where {cond}", all_values)
        else:
            self.cursor.execute(f"update {table} set {columns}", tuple(values))

        self.mydb.commit()

    def insert(self, what: list, table: str):
        increment = False
        if table == "books":

            increment = self.cursor.execute(f"select count(*) from {table} where title = ? and author = ? and year = ? and genre = ?",(what[0], what[1], what[2], what[3])).fetchone()[0] > 0

        if not increment:
            qm = ""
            for i in range(len(what)):
                if i == 0:
                    qm = "?"
                else:
                    qm += ", ?"

            if table == "books":
                if len(what) == 5:
                    qm += ", ?"

                    isbn = generate_isbn()
                    invalid = True
                    while invalid:
                        if self.cursor.execute(f"select * from books where isbn=?", (isbn,)).fetchone() == None:
                            invalid = False
                        else:
                            isbn = generate_isbn()

                    what.append(isbn)

                self.cursor.execute(f"insert into {table} values ({qm})", tuple(what))
            elif table == "history":
                self.cursor.execute(f"insert into {table} (username, action, title, author, sql_command, reverse_sql_command) values ({qm})", tuple(what))
            else:
                self.cursor.execute(f"insert into {table} values ({qm})", tuple(what))
        else:
            copies = self.cursor.execute("select copies from books where title=? and author=? and year=? and genre=?", (what[0], what[1], what[2], what[3])).fetchone()[0]
            self.update(["copies"], [int(copies) + int(what[4])], "books", {"title":what[0], "author":what[1], "year":what[2], "genre":what[3]})

        self.mydb.commit()

    def remove(self, table: str, condition: dict = None):
        if condition is not None:
            cond = ""
            n = 0
            for i in condition.keys():
                if n == 0:
                    cond = f"{i} = ?"
                    n += 1
                else:
                    cond += f" and {i} = ?"

            self.cursor.execute(f"delete from {table} where {cond}", tuple(condition.values()))
        else:
            self.cursor.execute(f"delete from {table}")

        self.mydb.commit()

    def commit(self) -> None:
        self.mydb.commit()


class DatabaseAdapter:
    def __init__(self, database_connection: DatabaseConnection):
        self.db = database_connection

    def select(self, what: list, table: str, condition: dict = None) -> list:
        return self.db.select(what, table, condition)

    def insert(self, what: list, table: str):
        self.db.insert(what, table)

    def update(self, what: list, values: list, table: str, condition: dict = None):
        self.db.update(what, values, table, condition)

    def remove(self, table: str, condition: dict = None):
        self.db.remove(table, condition)

    def commit(self):
        self.db.commit()


def verify_permissions(fn: callable) -> callable:
    def verification(self, *args: list, **kwargs: dict):
        found = False

        for p in self.permissions:
            if str(fn).__contains__(p):
                found = True

        if not found:
            raise RuntimeError("[red]You are not authorized to do this[/red]")

        return fn(self, *args, **kwargs)

    return verification


class User(ABC):
    @abstractmethod
    def get_logged_in(self) -> bool:
        pass

    @abstractmethod
    def set_logged_in(self) -> bool:
        pass

    @abstractmethod
    def get_permissions(self) -> list:
        pass

    @abstractmethod
    def borrow_book(self, title: str, author: str) -> None:
        pass

    @abstractmethod
    def return_book(self, title: str, author: str) -> None:
        pass

    @abstractmethod
    def reserve_book(self, title: str, author: str) -> None:
        pass

    @abstractmethod
    def add_book(self, title: str, author: str, year: int, genre: str, copies: int) -> None:
        pass

    @abstractmethod
    def edit_book(self, title_old: str, author_old: str, year_old: int, genre_old: str, copies_old: int, title: str, author: str, year: int, genre: str, copies: int) -> None:
        pass

    @abstractmethod
    def remove_book(self, title: str, author: str, year: int, copies: int) -> None:
        pass

    @abstractmethod
    def get_notification(self):
        pass

    @abstractmethod
    def set_notification(self, notif) -> None:
        pass

    @abstractmethod
    def revert_last_action(self):
        pass

    @abstractmethod
    def show_history(self):
        pass

    @abstractmethod
    def get_username(self):
        pass

    @abstractmethod
    def get_role(self):
        pass

    @abstractmethod
    def pull_data_by_isbn(self, isbn: str, external_db: dict):
        pass

class LibraryUser(User):
    def __init__(self, username: str, password: str, name: str, surname: str, role: str, database: DatabaseAdapter) -> None:
        self.username = username
        self.password = password
        self.name = name
        self.surname = surname
        self.role = role
        self.logged_in = False
        self.permissions = ["borrow_book", "return_book", "reserve_book", "revert_last_action"]
        self.database = database
        self.notification = None

    def get_logged_in(self) -> bool:
        return self.logged_in

    def set_logged_in(self) -> None:
        if self.logged_in:
            self.logged_in = False
        else:
            self.logged_in = True

    def get_permissions(self) -> list:
        return self.permissions

    @verify_permissions
    def borrow_book(self, title: str, author: str) -> None:  # ???????????
        has_book = self.database.select(["count(*)"], "in_possession", {"username":self.get_username(), "title":title})[0][0]

        if has_book != 0:
            raise RuntimeError("[yellow]You already have this book[/yellow]")
        else:

            self.database.insert([self.get_username(), title], "in_possession")

            normal_sql = f"insert into in_possession (username, title) values (?, ?)"
            reversed_sql = f"delete from in_possession where username=? and title=?"

            self.database.insert([self.username, "borrow", title, author, normal_sql, reversed_sql], "history")
            number_of_copies = self.database.select(["copies"], "books", {"title": title, "author": author})[0]
            self.database.update(["copies"], [number_of_copies[0]-1], "books", {"title": title, "author": author})

    @verify_permissions
    def return_book(self, title: str, author: str) -> None:

        self.database.remove("in_possession", {"username": self.get_username(), "title": title})

        reversed_sql = f"insert into in_possession (username, title) values (?, ?)"
        normal_sql = f"delete from in_possession where username=? and title=?"

        self.database.insert([self.username, "return", title, author, normal_sql, reversed_sql], "history")
        number_of_copies = self.database.select(["copies"], "books", {"title": title, "author": author})[0]
        self.database.update(["copies"], [number_of_copies[0] + 1], "books", {"title": title, "author": author})

        # notification
        try:
            username = self.database.select(["username"], "reservations", {"title": title})[0][0]
            self.database.remove("reservations", {"username": username, "title": title})
            self.database.insert([username, f"Book {title} by {author} is now available"], "notifications")
        except IndexError:
            pass

    @verify_permissions
    def reserve_book(self, title: str, author: str) -> None:
        if self.database.select(["count(*)"], "books", {"title":title, "author":author})[0][0] > 0:
            self.database.insert([self.username, title], "reservations")

    @verify_permissions
    def edit_book(self, title_old: str, author_old: str, year_old: int, genre_old: str, copies_old: int, title: str, author: str, year: int, genre: str, copies: int) -> None:
        pass

    @verify_permissions
    def add_book(self, title: str, author: str, year: int, genre: str, copies: int) -> None:
        pass

    @verify_permissions
    def remove_book(self, title: str, author: str, year: int, copies: int) -> None:
        pass

    def get_notification(self):
        return self.notification

    def set_notification(self, notif) -> None:
        self.notification = notif

    def get_username(self):
        return self.username

    @verify_permissions
    def revert_last_action(self):
        operations = self.database.select(["*"], "history", {"username":self.username})
        if operations != []:
            last_action, title, author = operations[len(operations)-1][2], operations[len(operations)-1][3], operations[len(operations)-1][4]

            if last_action == "borrow":
                self.return_book(title, author)
            if last_action == "return":
                self.borrow_book(title, author)

        else:
            raise RuntimeError("[yellow]No action to revert.[/yellow]")

    @verify_permissions
    def pull_data_by_isbn(self, isbn: str, external_db: dict):
        pass

    def show_history(self):  # shows from most recent
        history = self.database.select(["*"], "history", {"username":self.username})
        if len(history) != 0:
            action_history = f"Your history(from most recent):"
            for h, i in zip(reversed(history), range(len(history))):
                action_history += f"\n{i+1}. {h[2]}ed book '{h[3]}' by {h[4]}"
            return action_history
        else:
            raise RuntimeError("[yellow]No history to show.[/yellow]")

    def get_role(self):
        return self.role

    def __str__(self):
        return f"{self.role}: {self.username} - {self.name} {self.surname}"

    def __rich_console__(self, console, options):
        text = Text()

        text.append(f"{self.role}", style="bold green")
        text.append(": ")
        text.append(self.username, style="white")
        text.append(" - ")
        text.append(f"{self.name} {self.surname}", style="cyan")

        yield text


class LibraryAdmin(User):
    def __init__(self, username: str, password: str, name: str, surname: str, role: str, database: DatabaseAdapter) -> None:
        self.username = username
        self.password = password
        self.name = name
        self.surname = surname
        self.role = role
        self.logged_in = False
        self.permissions = ["add_book", "edit_book", "remove_book", "pull_data_by_isbn"]
        self.database = database

    def get_logged_in(self) -> bool:
        return self.logged_in

    def set_logged_in(self) -> None:
        if self.logged_in:
            self.logged_in = False
        else:
            self.logged_in = True

    def get_permissions(self) -> list:
        return self.permissions

    @verify_permissions
    def borrow_book(self, title: str, author: str) -> None:
        pass

    @verify_permissions
    def return_book(self, title: str, author: str) -> None:
        pass

    @verify_permissions
    def reserve_book(self, title: str, author: str) -> None:
        pass

    @verify_permissions
    def edit_book(self, title_old: str, author_old: str, year_old: int, genre_old: str, copies_old: int, title: str, author: str, year: int, genre: str, copies: int) -> None:
        self.database.update(["title", "author", "year", "genre", "copies"], [title, author, year, genre, copies], "books", {"title":title_old, "author":author_old, "year":year_old, "genre":genre_old})

    @verify_permissions
    def add_book(self, title: str, author: str, year: int, genre: str, copies: int) -> None:
        self.database.insert([title, author, year, genre, copies], "books")

    @verify_permissions
    def remove_book(self, title: str, author: str, year: int, copies: int) -> None:
        self.database.remove("books", {"title":title, "author":author, "year":year})

    def get_username(self):
        return self.username

    def get_notification(self):
        pass

    def set_notification(self, notif) -> None:
        pass

    @verify_permissions
    def revert_last_action(self):
        pass

    def show_history(self):
        pass

    def get_role(self):
        return self.role

    @verify_permissions
    def pull_data_by_isbn(self, isbn: str, external_db: dict):
        if external_db.get(isbn) is not None:
            title = external_db.get(isbn)["title"]
            author = external_db.get(isbn)["author"]
            genre = external_db.get(isbn)["genre"]
            year = external_db.get(isbn)["year"]
            copies = external_db.get(isbn)["copies"]

            self.database.insert([title, author, year, genre, copies, isbn], "books")
            return f"Successfully pulled book data with isbn:{isbn} from external database"
        else:
            return f"Failed to pull book data from external database. Book with isbn:{isbn} does not exist"

    def __str__(self):
        return f"[bold red]{self.role}[/bold red]: {self.username} - {self.name} {self.surname}"

    def __rich_console__(self, console, options):
        text = Text()

        text.append(f"{self.role}", style="bold green")
        text.append(": ")
        text.append(self.username, style="white")
        text.append(" - ")
        text.append(f"{self.name} {self.surname}", style="cyan")

        yield text


class UserFactory(ABC):
    @abstractmethod
    def create_user(self, username: str, password: str, name: str, surname: str, role: str, database: DatabaseAdapter) -> User:
        pass


class LibraryUserFactory(UserFactory):
    def create_user(self, username: str, password: str, name: str, surname: str, role: str, database: DatabaseAdapter) -> User:
        return LibraryUser(username, password, name, surname, role, database)


class LibraryAdminFactory(UserFactory):
    def create_user(self, username: str, password: str, name: str, surname: str, role: str, database: DatabaseAdapter) -> User:
        return LibraryAdmin(username, password, name, surname, role, database)

class Factory:
    _factories: dict

    def __init__(self, database: DatabaseAdapter) -> None:
        self._factories = {
            "user": LibraryUserFactory,
            "admin": LibraryAdminFactory,
        }
        self.database = database

    def create_user(self, username: str, password: str, name: str, surname: str, role: str, register: bool) -> User:
        if register:
            if role == "admin" or role == "user":
                if self.database.select(["*"], "users", {"username": username}) == []:
                    new_user = self._factories[role]().create_user(username, password, name, surname, role, self.database)
                    self.database.insert([username, password, name, surname, role, False], "users")
                    self.database.commit()

                else:
                    raise ValueError(f"User {username} already exists")
                return new_user
            else:
                raise ValueError(f"Invalid role: {role}")
        else:
            user = self._factories[role]().create_user(username, password, name, surname, role, self.database)
            user.set_logged_in()
            self.database.update(["logged_in"], [1], "users", {"username": username, "password": password})
            self.database.commit()
            return user


class Book:
    def __init__(self, title: str, author: str, year: int, genre: str, copies: int) -> None:
        self.title = title
        self.author = author
        self.year = year
        self.genre = genre
        self.copies = copies
        self.isbn = None

    def get_title(self):
        return self.title

    def set_title(self, title: str):
        self.title = title

    def get_author(self):
        return self.author

    def set_author(self, author: str):
        self.author = author

    def get_year(self):
        return self.year

    def set_year(self, year: str):
        self.year = year

    def get_genre(self):
        return self.genre

    def set_genre(self, genre: str):
        self.genre = genre

    def get_copies(self):
        return self.copies

    def set_copies(self, copies: str):
        self.copies = copies

    def get_isbn(self):
        return self.isbn

    def set_isbn(self, isbn: str):
        self.isbn = isbn

    def full_str(self):
        return f"{self.title} by {self.author} written in {self.year}, available copies: {self.copies}, isbn: {self.get_isbn()}"

    def owned_str(self):
        return f"{self.title} by {self.author} written in {self.year}, isbn: {self.get_isbn()}"

    def __str__(self):
        return f"{self.title} by {self.author} written in {self.year}, available copies: {self.copies}, isbn: {self.get_isbn()}"


class BookIterator:
    books: list
    n: int
    limit: int

    def __init__(self, database: DatabaseAdapter) -> None:
        self.books = []
        self.database = database
        self.n = 0
        self.limit = 0

    def find_books_by_genre(self, genre: str):
        self.books = []
        if genre is not None:
            self.books = self.database.select(["*"], "books", {"genre": genre})
        else:
            self.books = self.database.select(["*"], "books", None)

        self.n = 0
        self.limit = len(self.books)

    def find_books_by_isbn(self, isbn: str):
        self.books = []
        if isbn is not None:
            self.books = self.database.select(["*"], "books", {"isbn": isbn})
        else:
            self.books = self.database.select(["*"], "books", None)

        self.n = 0
        self.limit = len(self.books)

    def find_owned_books(self, user: User):
        self.books = []

        in_possession = self.database.select(["title"], "in_possession", {"username": user.get_username()})

        for i in in_possession:
            self.books.append(self.database.select(["*"], "books", {"title": i[0]})[0])

        self.n = 0
        self.limit = len(self.books)

    def search_strategy(self, genre: str, isbn: str, user: User):
        if genre is not None:
            self.find_books_by_genre(genre)
        elif isbn is not None:
            self.find_books_by_isbn(isbn)
        elif user is not None:
            self.find_owned_books(user)
        else:
            self.find_books_by_genre(None)

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Book:
        if self.n < self.limit:
            book = self.books[self.n]
            self.n += 1
            b = Book(book[0], book[1], book[2], book[3], book[4])
            b.set_isbn(book[5])
            return b

        raise StopIteration


def register_user(user_factory: Factory):
    name = input("Enter your name> ")
    surname = input("Enter your surname> ")
    username = input("Enter your username> ")
    password = input("Enter your password> ")
    role = input("Enter your role(admin or user)> ")
    try:
        user_factory.create_user(username, password, name, surname, role, True)
    except ValueError as e:
        console.print(f"{e}", style="error")


def log_in_user(user_factory: Factory, db_adapter: DatabaseAdapter):
    username = input("Enter your username> ")
    password = input("Enter your password> ")
    user_data = db_adapter.select(["name", "surname", "role"], "users", {"username": username, "password": password})

    if user_data == []:
        return None, "[red]Invalid username or password[/red]"
    else:
        name, surname, role = user_data[0]
        user = user_factory.create_user(username, password, name, surname, role, False)
        user.set_logged_in()
        db_adapter.update(["logged_in"], [1], "users", {"username":f"{user.get_username()}"})
        notif = db_adapter.select(["notification"], "notifications", {"username": username})
        if notif == []:
            return user, "Logged in"
        else:
            db_adapter.remove("notifications", {"notification": notif[0][0], "username": user.get_username()})
            return user, f"Logged in\n{notif[0][0]}"


def log_out(user: User, db_adapter: DatabaseAdapter):
    db_adapter.update(["logged_in"], [0], "users", {"username": f"{user.get_username()}"})
    user.set_logged_in()
    return None, f"Logged out"

def list_books(user: User, iterator: BookIterator, genre: str, isbn: str, owned: bool):
    loop1 = True
    while loop1:
        if isbn is None and genre is None and not owned:
            iterator.search_strategy(None, None, None)
        elif isbn is not None and genre is None and not owned:
            iterator.search_strategy(None, isbn, None)
            if iterator.limit == 0:
                console.print(f"There is no book with isbn: {isbn}", style="warning")
                break
        elif genre is not None and isbn is None and not owned:
            iterator.search_strategy(genre, None, None)
        elif genre is None and isbn is None and owned:
            iterator.search_strategy(None, None, user)

        b = iterator.books
        books = {}

        for i, j in zip(range(iterator.limit), iterator):
            if not owned:
                console.print(f"{i + 1}) {j}", style="default")
            else:
                console.print(f"{i + 1}) {j.owned_str()}", style="default")
            books[f"{i + 1}"] = b[i]
        console.print("0) Back\n", style="default")

        choice2 = input("> ")
        if choice2 in books:
            b = Book(books[choice2][0], books[choice2][1], books[choice2][2], books[choice2][3], books[choice2][4])
            b.set_isbn(books[choice2][5])
            if not owned:
                if b.get_copies() > 0:
                    loop2 = True
                    while loop2:
                        console.print(f"{b}\n1 - Borrow book\n2 - Edit book\n3 - Remove book\n0 - Back\n", style="default")
                        choice3 = input("> ")

                        if choice3 == "1":
                            try:
                                user.borrow_book(b.get_title(), b.get_author())
                            except RuntimeError as e:
                                console.print(f"{e}", style="error")

                            loop2 = False
                            loop1 = False

                        elif choice3 == "2":
                            new_title = input("Enter book new title> ")
                            new_author = input("Enter book new author> ")
                            new_genre = input("Enter book new genre> ")

                            year_change = True
                            while year_change:
                                try:
                                    new_year = int(input("Enter book new year> "))
                                    year_change = False
                                except ValueError:
                                    console.print("Year has to be an integer", style="error")

                            copies_change = True
                            while copies_change:
                                try:
                                    new_copies = int(input("Enter book new copies> "))
                                    copies_change = False
                                except ValueError:
                                    console.print("Copies has to be an integer", style="error")

                            try:
                                user.edit_book(b.get_title(), b.get_author(), b.get_year(), b.get_genre(), b.get_copies(), new_title, new_author, new_year, new_genre, new_copies)
                            except RuntimeError as e:
                                console.print(f"{e}", style="error")

                            loop2 = False
                            loop1 = False

                        elif choice3 == "3":
                            try:
                                user.remove_book(b.get_title(), b.get_author(), b.get_year(), b.get_copies())
                            except RuntimeError as e:
                                console.print(f"{e}", style="error")

                            loop2 = False
                            loop1 = False

                        elif choice3 == "0":
                            loop2 = False

                        else:
                            console.print("Invalid choice", style="error")
                else:
                    loop2 = True
                    while loop2:
                        console.print(f"{b}\n1 - Reserve book\n2 - Edit book\n3 - Remove book\n0 - Back\n", style="default")
                        choice3 = input("> ")

                        if choice3 == "1":
                            try:
                                user.reserve_book(b.get_title(), b.get_author())
                            except RuntimeError as e:
                                console.print(f"{e}", style="error")

                            loop2 = False
                            loop1 = False

                        elif choice3 == "2":
                            new_title = input("Enter book new title> ")
                            new_author = input("Enter book new author> ")
                            new_genre = input("Enter book new genre> ")

                            year_change = True
                            while year_change:
                                try:
                                    new_year = int(input("Enter book new year> "))
                                    year_change = False
                                except ValueError:
                                    console.print("Year has to be an integer", style="error")

                            copies_change = True
                            while copies_change:
                                try:
                                    new_copies = int(input("Enter book new copies> "))
                                    copies_change = False
                                except ValueError:
                                    console.print("Copies has to be an integer", style="error")

                            try:
                                user.edit_book(b.get_title(), b.get_author(), b.get_year(), b.get_genre(), b.get_copies(), new_title, new_author, new_year, new_genre, new_copies)
                            except RuntimeError as e:
                                console.print(f"{e}", style="error")

                            loop2 = False
                            loop1 = False

                        elif choice3 == "3":
                            try:
                                user.remove_book(b.get_title(), b.get_author(), b.get_year(), b.get_copies())
                            except RuntimeError as e:
                                console.print(f"{e}", style="error")

                            loop2 = False
                            loop1 = False

                        elif choice3 == "0":
                            loop2 = False

                        else:
                            console.print("Invalid choice", style="error")
            else:
                loop2 = True
                while loop2:
                    console.print(f"{b.owned_str()}\n1 - Return book\n0 - Back\n", style="default")
                    choice3 = input("> ")

                    if choice3 == "1":
                        try:
                            user.return_book(b.get_title(), b.get_author())
                        except RuntimeError as e:
                            console.print(f"{e}", style="error")

                        loop2 = False
                        loop1 = False

                    elif choice3 == "0":
                        loop2 = False

                    else:
                        console.print("Invalid choice", style="error")

        elif choice2 == "0":
            loop1 = False
        else:
            console.print("Invalid choice", style="error")


def options(user: User, user_factory: Factory, db_adapter: DatabaseAdapter, iterator: BookIterator):
    if user is None:
        console.print("1 - Log in\n2 - Register user\n0 - Quit\n", style="default")
        choice = input("> ")

        match(choice):
            case "1":
                user, note = log_in_user(user_factory, db_adapter)
                console.print(note, style="warning")
                return user
            case "2":
                register_user(user_factory)
            case "0":
                console.print("Goodbye!", style="warning")
                quit(0)
            case _:
                console.print("Invalid input", style="error")

        return None

    elif user is not None:
        #print(f"{user.get_role()}: {user.get_username()}")
        print(f"{user}")
        console.print("1 - List all books\n2 - Search book by genre\n3 - Search book by isbn\n4 - Revert last action\n5 - Show history\n6 - Show your books\n7 - Add book\n8 - Pull book data by isbn\n0 - Log out\n", style="default")
        choice = input("> ")

        match(choice):
            case "1":
                list_books(user, iterator, None, None, False)
                return user

            case "2":
                genre = db_adapter.select(["genre"], "books", {"distinct":"distinct"})
                # print(genre)
                if genre != []:
                    loop1 = True
                    while loop1:
                        for i in range(len(genre)):
                            console.print(f"{i + 1}) {genre[i][0]}", style="default")
                        console.print("0) Back\n", style="default")

                        choice2 = input("> ")

                        try:
                            choice2 = int(choice2)

                            if not 0 <= choice2 <= len(genre):
                                raise ValueError("Invalid choice")
                            else:
                                if choice2 == 0:
                                    loop1 = False
                                else:
                                    genre = genre[choice2-1][0]
                                    loop1 = False

                        except ValueError as e:
                            console.print(f"{e}", style="error")

                    if choice2 == 0:
                        pass
                    else:
                        list_books(user, iterator, genre, None, False)
                    """
                    iterator.find_books_by_genre(genre)

                    for i, j in zip(range(iterator.limit), iterator):
                        print(f"{i + 1}) {j}")
                    """

                else:
                    console.print("There are no books", style="warning")

                return user

            case "3":
                choice2 = input("Enter isbn> ")

                list_books(user, iterator, None, choice2, False)
                return user
                """
                iterator.find_books_by_isbn(choice2)

                if iterator.limit == 0:
                    print(f"There is no book with isbn: {choice2}")
                else:
                    for i, j in zip(range(iterator.limit), iterator):
                        print(f"{i + 1}) {j}")
                """
            case "4":
                try:
                    user.revert_last_action()
                except RuntimeError as e:
                    console.print(f"{e}", style="error")

                return user

            case "5":
                try:
                    console.print(user.show_history(), style="default")
                except RuntimeError as e:
                    console.print(f"{e}", style="error")
                return user

            case "6":
                list_books(user, iterator, None, None, True)
                return user

            case "7":
                new_title = input("Enter book title> ")
                new_author = input("Enter book author> ")
                new_genre = input("Enter book genre> ")

                year_change = True
                while year_change:
                    try:
                        new_year = int(input("Enter book year> "))
                        year_change = False
                    except ValueError:
                        console.print("Year has to be an integer", style="error")

                copies_change = True
                while copies_change:
                    try:
                        new_copies = int(input("Enter book copies> "))
                        copies_change = False
                    except ValueError:
                        console.print("Copies has to be an integer", style="error")

                try:
                    user.add_book(new_title, new_author, new_year, new_genre, new_copies)
                except RuntimeError as e:
                    console.print(f"{e}", style="error")

                return user

            case "8":
                isbn = input("Enter isbn> ")
                try:
                    note = user.pull_data_by_isbn(isbn, external_database)
                    console.print(note, style="default")
                except RuntimeError as e:
                    console.print(f"{e}", style="error")

                return user

            case "0":
                user, notif = log_out(user, db_adapter)
                console.print(notif, style="warning")
                return user

            case _:
                console.print("Invalid input", style="error")
                return user


@app.command()
def run():
    mydb = DatabaseConnection("library_database.db")
    db_adapter = DatabaseAdapter(mydb)
    user_factory = Factory(db_adapter)
    iterator = BookIterator(db_adapter)
    user = None
    # db_adapter.insert(["1", "notif"], "notifications")

    while True:
        if user is None:
            user = options(user, user_factory, db_adapter, iterator)
        else:
            user = options(user, user_factory, db_adapter, iterator)

if __name__ == "__main__":
    app()
