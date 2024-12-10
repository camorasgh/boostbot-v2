import sqlite3
from contextlib import asynccontextmanager
from typing import Tuple, List, Optional


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


@asynccontextmanager
async def database_connection(database_name: str):
    """
    Async context manager for database connections to ensure proper cleanup.
    """
    connection = None
    try:
        connection = sqlite3.connect(database=database_name)
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.cursor()
        yield connection, cursor
    except sqlite3.Error as e:
        raise DatabaseError(f"Database connection failed: {e}")
    finally:
        if connection is not None:
            connection.close()


async def setup_database(database_name: str) -> bool:
    """
    Sets up the database with necessary tables for managing users and boost keys.

    Args:
        database_name (str): Name of the database file

    Returns:
        bool: True if setup successful, False otherwise

    Raises:
        DatabaseError: If table creation fails
    """
    try:
        async with database_connection(database_name) as (connection, cursor):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS boost_keys (
                    boost_key TEXT PRIMARY KEY,
                    redeemable_boosts INTEGER NOT NULL CHECK (redeemable_boosts >= 0),
                    api_used TEXT
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_boost_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    boost_key TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (boost_key) REFERENCES boost_keys (boost_key) ON DELETE CASCADE,
                    UNIQUE(user_id, boost_key)
                );
            """)

            connection.commit()
            return True

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to setup database: {e}")


async def add_user(user_id: int, database_name: str) -> bool:
    """
    Adds a user to the database if they don't already exist.

    Args:
        user_id (int): The unique ID of the user to add
        database_name (str): The database file name

    Returns:
        bool: True if user added or already exists, False on failure

    Raises:
        DatabaseError: If operation fails
    """
    try:
        async with database_connection(database_name) as (connection, cursor):
            cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?);", (user_id,))
            connection.commit()
            return True
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to add user: {e}")


async def add_boost_key(boost_key: str, redeemable_boosts: int, database_name: str,
                        api_used: Optional[str] = None) -> bool:
    """
    Adds a new boost key to the database.

    Args:
        boost_key (str): The boost key to add
        redeemable_boosts (int): Number of boosts available
        database_name (str): The database file name
        api_used (Optional[str]): API identifier if applicable

    Returns:
        bool: True if key added successfully, False otherwise

    Raises:
        ValueError: If invalid input provided
        DatabaseError: If operation fails
    """
    if not isinstance(redeemable_boosts, int) or redeemable_boosts < 0:
        raise ValueError("Redeemable boosts must be a non-negative integer")

    if not boost_key or not isinstance(boost_key, str):
        raise ValueError("Invalid boost key format")

    try:
        async with database_connection(database_name) as (connection, cursor):
            cursor.execute("""
                INSERT OR IGNORE INTO boost_keys (boost_key, redeemable_boosts, api_used)
                VALUES (?, ?, ?);
            """, (boost_key, redeemable_boosts, api_used))
            connection.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to add boost key: {e}")


async def assign_boost_key_to_user(user_id: int, boost_key: str, database_name: str) -> bool:
    """
    Assigns a boost key to a user.

    Args:
        user_id (int): User ID to assign the key to
        boost_key (str): Boost key to assign
        database_name (str): The database file name

    Returns:
        bool: True if assignment successful, False otherwise

    Raises:
        DatabaseError: If operation fails
    """
    try:
        async with database_connection(database_name) as (connection, cursor):
            cursor.execute("""
                INSERT INTO user_boost_keys (user_id, boost_key)
                VALUES (?, ?);
            """, (user_id, boost_key))
            connection.commit()
            return True
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to assign boost key: {e}")


async def remove_boost_from_key(boost_key: str, boosts: int, database_name: str) -> bool:
    """
    Deducts boosts from a boost key with proper transaction handling.
    """
    if not isinstance(boosts, int) or boosts <= 0:
        raise ValueError("Boosts must be a positive integer")

    try:
        async with database_connection(database_name) as (connection, cursor):
            cursor.execute("BEGIN TRANSACTION")

            # Check current boosts
            cursor.execute("""
                SELECT redeemable_boosts 
                FROM boost_keys 
                WHERE boost_key = ?
            """, (boost_key,))

            result = cursor.fetchone()
            if not result or result[0] < boosts:
                cursor.execute("ROLLBACK")
                return False

            # Update boosts
            cursor.execute("""
                UPDATE boost_keys
                SET redeemable_boosts = redeemable_boosts - ?
                WHERE boost_key = ?;
            """, (boosts, boost_key))

            connection.commit()
            return True

    except sqlite3.Error as e:
        if connection:
            cursor.execute("ROLLBACK")
        raise DatabaseError(f"Failed to remove boosts: {e}")



async def get_boost_keys_for_user(user_id: int, database_name: str) -> List[Tuple[str, int]]:
    """
    Retrieves all boost keys assigned to a user.

    Args:
        user_id (int): User ID to get keys for
        database_name (str): The database file name

    Returns:
        List[Tuple[str, int]]: List of (boost_key, redeemable_boosts) tuples

    Raises:
        DatabaseError: If operation fails
    """
    try:
        async with database_connection(database_name) as (connection, cursor):
            cursor.execute("""
                SELECT bk.boost_key, bk.redeemable_boosts
                FROM boost_keys bk
                INNER JOIN user_boost_keys ubk ON bk.boost_key = ubk.boost_key
                WHERE ubk.user_id = ?;
            """, (user_id,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to get boost keys: {e}")


async def check_user_has_valid_boost_key(user_id: int, database_name: str) -> Optional[Tuple[str, int]]:
    """
    Checks if a user has a valid boost key with remaining boosts.

    Args:
        user_id (int): User ID to check
        database_name (str): The database file name

    Returns:
        Optional[Tuple[str, int]]: (boost_key, remaining_boosts) if found, None otherwise

    Raises:
        DatabaseError: If operation fails
    """
    try:
        async with database_connection(database_name) as (connection, cursor):
            cursor.execute("""
                SELECT bk.boost_key, bk.redeemable_boosts
                FROM boost_keys bk
                INNER JOIN user_boost_keys ubk ON bk.boost_key = ubk.boost_key
                WHERE ubk.user_id = ? AND bk.redeemable_boosts > 0
                LIMIT 1;
            """, (user_id,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to check boost key: {e}")





async def transfer_boost_key(sender_id: int, receiver_id: int, boost_key: str, database_name: str) -> bool:
    """
    Transfers a boost key between users with proper transaction handling.
    """
    if sender_id == receiver_id:
        raise ValueError("Sender and receiver cannot be the same user")

    try:
        async with database_connection(database_name) as (connection, cursor):
            cursor.execute("BEGIN TRANSACTION")

            # Verify sender owns key
            cursor.execute("""
                SELECT bk.redeemable_boosts
                FROM boost_keys bk
                JOIN user_boost_keys ubk ON bk.boost_key = ubk.boost_key
                WHERE ubk.user_id = ? AND bk.boost_key = ?
            """, (sender_id, boost_key))

            if not cursor.fetchone():
                cursor.execute("ROLLBACK")
                return False

            # Verify receiver exists
            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (receiver_id,))
            if not cursor.fetchone():
                cursor.execute("ROLLBACK")
                return False

            # Transfer key
            cursor.execute("""
                UPDATE user_boost_keys
                SET user_id = ?
                WHERE user_id = ? AND boost_key = ?
            """, (receiver_id, sender_id, boost_key))

            connection.commit()
            return True

    except sqlite3.Error as e:
        if connection:
            cursor.execute("ROLLBACK")
        raise DatabaseError(f"Failed to transfer boost key: {e}")


async def update_boosts_for_key(boost_key: str, boosts: int, database_name: str, operation: str) -> bool:
    """
    Updates the number of boosts for a key.

    Args:
        boost_key (str): Boost key to update
        boosts (int): Number of boosts to add/remove
        database_name (str): The database file name
        operation (str): Either 'add' or 'remove'

    Returns:
        bool: True if update successful, False otherwise

    Raises:
        ValueError: If invalid operation or boosts value
        DatabaseError: If operation fails
    """
    if operation not in ("add", "remove"):
        raise ValueError("Operation must be 'add' or 'remove'")

    if not isinstance(boosts, int) or boosts < 0:
        raise ValueError("Boosts must be a non-negative integer")

    try:
        async with database_connection(database_name) as (connection, cursor):
            cursor.execute("BEGIN TRANSACTION")

            if operation == "add":
                cursor.execute("""
                    UPDATE boost_keys
                    SET redeemable_boosts = redeemable_boosts + ?
                    WHERE boost_key = ?;
                """, (boosts, boost_key))

            else:  # remove
                cursor.execute("""
                    UPDATE boost_keys
                    SET redeemable_boosts = redeemable_boosts - ?
                    WHERE boost_key = ? AND redeemable_boosts >= ?;
                """, (boosts, boost_key, boosts))

            success = cursor.rowcount > 0
            if success:
                connection.commit()
            else:
                connection.rollback()
            return success

    except sqlite3.Error as e:
        if connection:
            connection.rollback()
        raise DatabaseError(f"Failed to update boosts: {e}")