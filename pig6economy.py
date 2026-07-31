import sqlite3
import tools


class Pig6Economy:
    def __init__(self, db_name="pig6economy.db"):
        self.db = sqlite3.connect(db_name)
        self.cursor = self.db.cursor()
        self.init_db()

    def init_db(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        last_salary TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS codes (
            id INTEGER PRIMARY KEY,
            code TEXT,
            owner_id INTEGER,
            used BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP
            )
            """)

        self.db.commit()

    def close(self):
        self.db.close()

    def add_user(self, user_id, balance=100):
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
        self.add_user(user_id)
        self.cursor.execute(
            """
            SELECT balance FROM users WHERE user_id = ?
        """,
            (user_id,),
        )
        result = self.cursor.fetchall()
        return result[0][0] if result else 0

    def get_last_salary(self, user_id):
        self.add_user(user_id)
        self.cursor.execute(
            """
                SELECT last_salary FROM users WHERE user_id = ?
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

        self.add_user(receiver_id, 100)

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

    def create_code(self, code, owner_id=0):
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO codes (code, owner_id, used)
            VALUES (?, ?, 0)
            """,
            (code, owner_id),
        )

        self.db.commit()

    def get_active_codes(self):
        self.cursor.execute("""
            SELECT id, code, owner_id
            FROM codes
            WHERE used = 0
            """)

        return self.cursor.fetchall()

    def get_system_codes_count(self):
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM codes
            WHERE used = 0 AND owner_id = 0
            """)

        return self.cursor.fetchone()[0]

    def get_active_codes_count(self):
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM codes
            WHERE used = 0
            """)

        return self.cursor.fetchone()[0]

    def get_code_for_user(self, user_id):
        self.add_user(user_id)

        self.cursor.execute("""
            SELECT id, code
            FROM codes
            WHERE owner_id = 0 AND used = 0
            LIMIT 1
            """)

        result = self.cursor.fetchone()

        if not result:
            return None

        code_id, code = result

        self.cursor.execute(
            """
            UPDATE codes
            SET owner_id = ?
            WHERE id = ? AND owner_id = 0 AND used = 0
            """,
            (user_id, code_id),
        )

        if self.cursor.rowcount != 1:
            self.db.rollback()
            return None

        self.db.commit()

        return code

    def return_code_to_system(self, user_id):
        self.cursor.execute(
            """
            SELECT id
            FROM codes
            WHERE owner_id = ? AND used = 0
            ORDER BY id
            LIMIT 1
            """,
            (user_id,),
        )

        result = self.cursor.fetchone()

        if not result:
            return None

        code_id = result[0]
        new_code = tools.generate_code()

        self.cursor.execute(
            """
            UPDATE codes
            SET code = ?, owner_id = 0
            WHERE id = ? AND owner_id = ? AND used = 0
            """,
            (new_code, code_id, user_id),
        )

        if self.cursor.rowcount != 1:
            self.db.rollback()
            return None

        self.db.commit()

        return new_code

    def get_user_codes(self, user_id):
        self.cursor.execute(
            """
            SELECT code
            FROM codes
            WHERE owner_id = ? AND used = 0
            ORDER BY id
            """,
            (user_id,),
        )

        return [row[0] for row in self.cursor.fetchall()]

    def use_code_from_text(self, text):
        self.cursor.execute("""
            SELECT id, code
            FROM codes
            WHERE used = 0
            """)

        codes = self.cursor.fetchall()

        for code_id, code in codes:
            if code in text:
                self.cursor.execute(
                    """
                    UPDATE codes
                    SET used = 1,
                        used_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND used = 0
                    """,
                    (code_id,),
                )

                if self.cursor.rowcount == 1:
                    self.db.commit()
                    return True

                self.db.rollback()
                return False

        return False


economy = Pig6Economy()
economy.add_user(0, 0)
