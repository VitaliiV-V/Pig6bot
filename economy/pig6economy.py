import sqlite3
import logging
import bot.tools as tools

logger = logging.getLogger(__name__)


class Pig6Economy:
    def __init__(self, db_name="pig6economy.db"):
        try:
            self.db = sqlite3.connect(db_name)
            self.cursor = self.db.cursor()
            self.init_db()
        except sqlite3.Error:
            logger.exception("Failed to initialize database (%s)", db_name)
            raise

    def init_db(self):
        try:
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            last_salary TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            name TEXT
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

            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_state (
                id INTEGER PRIMARY KEY,
                available_codes INTEGER DEFAULT 0,
                price REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                price REAL,
                available_codes INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                amount INTEGER,
                total REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            self.db.commit()
        except sqlite3.Error:
            logger.exception("Failed to initialize database schema")
            raise

    def close(self):
        try:
            self.db.close()
        except sqlite3.Error:
            logger.exception("Failed to close database connection")
            raise

    def add_user(self, user_id, name=None, balance=100):
        try:
            self.cursor.execute(
                """
            INSERT OR IGNORE INTO USERS (user_id, balance, name) VALUES (?, ?, ?)
            """,
                (user_id, balance, name),
            )
            self.db.commit()
        except sqlite3.Error:
            logger.exception("add_user(%s) failed", user_id)
            raise

    def remove_user(self, user_id):
        try:
            self.cursor.execute(
                """
            DELETE FROM users WHERE user_id = ?
            """,
                (user_id,),
            )

            self.db.commit()
        except sqlite3.Error:
            logger.exception("remove_user(%s) failed", user_id)
            raise

    def get_all_users(self):
        try:
            self.cursor.execute("""
                SELECT user_id, balance
                FROM users
                """)

            return self.cursor.fetchall()
        except sqlite3.Error:
            logger.exception("get_all_users() failed")
            raise

    def get_balance(self, user_id):
        try:
            self.add_user(user_id)
            self.cursor.execute(
                """
                SELECT balance FROM users WHERE user_id = ?
            """,
                (user_id,),
            )
            result = self.cursor.fetchall()
            return result[0][0] if result else 0
        except sqlite3.Error:
            logger.exception("get_balance(%s) failed", user_id)
            raise

    def get_last_salary(self, user_id):
        try:
            self.add_user(user_id)
            self.cursor.execute(
                """
                    SELECT last_salary FROM users WHERE user_id = ?
                """,
                (user_id,),
            )
            result = self.cursor.fetchall()
            return result[0][0] if result else 0
        except sqlite3.Error:
            logger.exception("get_last_salary(%s) failed", user_id)
            raise

    def add_tokens(self, user_id, amount):
        try:
            self.cursor.execute(
                """
                UPDATE users
                SET balance = balance + ?
                WHERE user_id = ?
                """,
                (amount, user_id),
            )

            self.db.commit()
        except sqlite3.Error:
            logger.exception("add_tokens(%s, %s) failed", user_id, amount)
            raise

    def remove_tokens(self, user_id, amount):
        try:
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
        except sqlite3.Error:
            logger.exception("remove_tokens(%s, %s) failed", user_id, amount)
            raise

    def user_exists(self, user_id):
        try:
            self.cursor.execute(
                """
                SELECT 1 FROM users WHERE user_id = ?
                """,
                (user_id,),
            )

            return self.cursor.fetchone() is not None
        except sqlite3.Error:
            logger.exception("user_exists(%s) failed", user_id)
            raise

    def get_top_users(self, limit: int = 10):
        try:
            self.cursor.execute(
                """
                    SELECT name, balance
                    FROM users
                    WHERE balance > 0
                    ORDER BY balance DESC
                    LIMIT ?
                    """,
                (limit,),
            )

            return self.cursor.fetchall()
        except sqlite3.Error:
            logger.exception("get_top_users(%s) failed", limit)
            raise

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
            logger.info(
                "Transaction committed: sender=%s receiver=%s amount=%s comment=%r",
                sender_id,
                receiver_id,
                amount,
                comment,
            )
            return True

        except sqlite3.Error as e:
            logger.exception(
                "Transaction failed, rolling back: sender=%s receiver=%s amount=%s comment=%r: %s",
                sender_id,
                receiver_id,
                amount,
                comment,
                e,
            )
            self.db.rollback()
            return False

    def create_code(self, code, owner_id=0):
        try:
            self.cursor.execute(
                """
                INSERT OR IGNORE INTO codes (code, owner_id, used)
                VALUES (?, ?, 0)
                """,
                (code, owner_id),
            )

            self.db.commit()
        except sqlite3.Error:
            logger.exception("create_code(owner_id=%s) failed", owner_id)
            raise

    def get_active_codes(self):
        try:
            self.cursor.execute("""
                SELECT id, code, owner_id
                FROM codes
                WHERE used = 0
                """)

            return self.cursor.fetchall()
        except sqlite3.Error:
            logger.exception("get_active_codes() failed")
            raise

    def get_system_codes_count(self):
        try:
            self.cursor.execute("""
                SELECT COUNT(*)
                FROM codes
                WHERE used = 0 AND owner_id = 0
                """)

            return self.cursor.fetchone()[0]
        except sqlite3.Error:
            logger.exception("get_system_codes_count() failed")
            raise

    def get_active_codes_count(self):
        try:
            self.cursor.execute("""
                SELECT COUNT(*)
                FROM codes
                WHERE used = 0
                """)

            return self.cursor.fetchone()[0]
        except sqlite3.Error:
            logger.exception("get_active_codes_count() failed")
            raise

    def get_code_for_user(self, user_id):
        try:
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
        except sqlite3.Error:
            logger.exception("get_code_for_user(%s) failed", user_id)
            raise

    def return_code_to_system(self, user_id):
        try:
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
            new_code = tools.generate_id()

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
        except sqlite3.Error:
            logger.exception("return_code_to_system(%s) failed", user_id)
            raise

    def get_user_codes(self, user_id):
        try:
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
        except sqlite3.Error:
            logger.exception("get_user_codes(%s) failed", user_id)
            raise

    def use_code_from_text(self, text):
        try:
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
                        logger.info("Code redeemed from text (id=%s)", code_id)
                        return True

                    self.db.rollback()
                    return False

            return False
        except sqlite3.Error:
            logger.exception("use_code_from_text() failed")
            raise

    def update_last_salary(self, user_id):
        try:
            self.add_user(user_id)

            self.cursor.execute(
                """
                UPDATE users
                SET last_salary = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (user_id,),
            )

            self.db.commit()
        except sqlite3.Error:
            logger.exception("update_last_salary(%s) failed", user_id)
            raise

    def set_name_if_empty(self, user_id: int, name: str):
        try:
            self.cursor.execute(
                """
                UPDATE users
                SET name = ?
                WHERE user_id = ?
                AND (name IS NULL OR name = '')
                """,
                (f"@{name}", user_id),
            )
            self.db.commit()
        except sqlite3.Error:
            logger.exception("set_name_if_empty(%s) failed", user_id)
            raise

    # ==========================================

    # MARKET API
    # ==========================================

    def save_market_state(self, available_codes, price):
        try:
            self.cursor.execute(
                """
                INSERT INTO market_state
                (id, available_codes, price)
                VALUES (1, ?, ?)
                ON CONFLICT(id)
                DO UPDATE SET
                    available_codes = excluded.available_codes,
                    price = excluded.price,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (available_codes, price),
            )

            self.db.commit()
        except sqlite3.Error:
            logger.exception(
                "save_market_state(available_codes=%s, price=%s) failed",
                available_codes,
                price,
            )
            raise

    def get_market_state(self):
        try:
            self.cursor.execute("""
                SELECT available_codes, price
                FROM market_state
                WHERE id = 1
            """)

            result = self.cursor.fetchone()

            if not result:
                return {"available_codes": 0, "price": 0}

            return {"available_codes": result[0], "price": result[1]}
        except sqlite3.Error:
            logger.exception("get_market_state() failed")
            raise

    def add_market_history(self, price, available_codes):
        try:
            self.cursor.execute(
                """
                INSERT INTO market_history
                (price, available_codes)
                VALUES (?, ?)
            """,
                (price, available_codes),
            )

            self.db.commit()
        except sqlite3.Error:
            logger.exception(
                "add_market_history(price=%s, available_codes=%s) failed",
                price,
                available_codes,
            )
            raise

    def get_market_history(self, limit=50):
        try:
            self.cursor.execute(
                """
                SELECT created_at, price
                FROM market_history
                ORDER BY id DESC
                LIMIT ?
            """,
                (limit,),
            )

            rows = self.cursor.fetchall()

            rows.reverse()

            return [{"timestamp": row[0], "price": row[1]} for row in rows]
        except sqlite3.Error:
            logger.exception("get_market_history(%s) failed", limit)
            raise

    def add_market_operation(self, operation_type, amount, total):
        try:
            self.cursor.execute(
                """
                INSERT INTO market_operations
                (type, amount, total)
                VALUES (?, ?, ?)
            """,
                (operation_type, amount, total),
            )

            self.db.commit()
        except sqlite3.Error:
            logger.exception(
                "add_market_operation(type=%s, amount=%s, total=%s) failed",
                operation_type,
                amount,
                total,
            )
            raise

    def get_market_operations(self, limit=20):
        try:
            self.cursor.execute(
                """
                SELECT type, amount, total, created_at
                FROM market_operations
                ORDER BY id DESC
                LIMIT ?
            """,
                (limit,),
            )

            return [
                {
                    "type": row[0],
                    "amount": row[1],
                    "total": row[2],
                    "created_at": row[3],
                }
                for row in self.cursor.fetchall()
            ]
        except sqlite3.Error:
            logger.exception("get_market_operations(%s) failed", limit)
            raise


economy = Pig6Economy()
economy.add_user(0, "SYSTEM", 0)
