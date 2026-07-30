import sqlite3


class Pig6Economy:
    def __init__(self, db_name="pig6economy.db"):
        self.db = sqlite3.connect(db_name)
        self.cursor = self.db.cursor()
        self.init_db()

    def init_db(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender INTEGER,
        receiver INTEGER,
        amount INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        comment TEXT
        )
        """)

        self.db.commit()

    def close(self):
        self.db.close()

    def add_user(self, user_id, balance):
        self.cursor.execute(
            """
        INSERT OR IGNORE INTO USERS (user_id, balance) VALUES (?,?)
        """,
            (user_id, balance),
        )
        self.db.commit()

    def remove_user(self, user_id):
        self.cursor.execute(
            """
        DELETE FROM users WHERE user_id = ?
        """,
            (user_id,),
        )

        self.db.commit()

    def get_all_users(self):
        self.cursor.execute("""
            SELECT user_id, balance
            FROM users
            """)

        return self.cursor.fetchall()

    def get_balance(self, user_id):
        self.add_user(user_id, 100)
        self.cursor.execute(
            """
            SELECT balance FROM users WHERE user_id = ?
        """,
            (user_id,),
        )
        result = self.cursor.fetchall()
        return result[0][0] if result else 0

    def add_tokens(self, user_id, amount):
        self.cursor.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (amount, user_id),
        )

        self.db.commit()

    def remove_tokens(self, user_id, amount):
        self.cursor.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ? AND balance >= ?
            """,
            (amount, user_id, amount),
        )

        self.db.commit()

        return self.cursor.rowcount > 0

    def user_exists(self, user_id):
        self.cursor.execute(
            """
            SELECT 1 FROM users WHERE user_id = ?
            """,
            (user_id,),
        )

        return self.cursor.fetchone() is not None

    def create_transaction(self, sender_id, receiver_id, amount, comment):
        if sender_id == 0:
            self.add_tokens(sender_id, amount)

        if self.get_balance(sender_id) < amount:
            return False

        if not self.user_exists(receiver_id):
            return False

        try:
            self.cursor.execute(
                """
                UPDATE users
                SET balance = balance - ?
                WHERE user_id = ?
                """,
                (amount, sender_id),
            )

            self.cursor.execute(
                """
                UPDATE users
                SET balance = balance + ?
                WHERE user_id = ?
                """,
                (amount, receiver_id),
            )

            self.cursor.execute(
                """
                INSERT INTO transactions(sender, receiver, amount, comment)
                VALUES (?, ?, ?, ?)
                """,
                (sender_id, receiver_id, amount, comment),
            )

            self.db.commit()
            return True

        except Exception:
            self.db.rollback()
            return False


bd = Pig6Economy()
bd.add_user(0, 0)
