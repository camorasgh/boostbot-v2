import sqlite3
from typing import Tuple, List, Optional


async def setup_database(database_name: str) -> bool:
    """
    Sets up the database with the necessary tables for managing users and boost keys.
    
    :param database_name: Name of the database file.
    :return: True if setup is successful, False otherwise.
    """
    try:
        connection, cursor = await database_connection(database_name)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS boost_keys (
                boost_key TEXT PRIMARY KEY,
                redeemable_boosts INTEGER NOT NULL,
                api_used TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_boost_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                boost_key TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (boost_key) REFERENCES boost_keys (boost_key) ON DELETE CASCADE
            );
        """)
        
        connection.commit()
        connection.close()
        return True
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False


async def database_connection(database_name : str):
    """
    Establishes a connection for the sqlite3 database
    Params:
        :param database_name: Name of the database
    Returns:
        connection: Sqlite3 connection to the database
        cursor:     Sqlite3 connection cursor to the database
    """
    connection = sqlite3.connect(database=database_name)
    cursor = connection.cursor()
    return connection, cursor


async def add_user(user_id: int, database_name: str):
    connection, cursor = await database_connection(database_name)
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?);", (user_id,))
    connection.commit()
    connection.close()


async def add_boost_key(boost_key: str, redeemable_boosts: int, database_name : str, api_used: Optional[str] = None):
    connection, cursor = await database_connection(database_name)
    cursor.execute("""
        INSERT OR IGNORE INTO boost_keys (boost_key, redeemable_boosts, api_used)
        VALUES (?, ?, ?);
    """, (boost_key, redeemable_boosts, api_used))
    connection.commit()
    connection.close()


async def assign_boost_key_to_user(user_id: int, boost_key: str, database_name : str):
    connection, cursor = await database_connection(database_name)
    cursor.execute("""
        INSERT INTO user_boost_keys (user_id, boost_key)
        VALUES (?, ?);
    """, (user_id, boost_key))
    connection.commit()
    connection.close()


async def remove_boost_key_from_user(user_id: int, boost_key: str, database_name : str):
    connection, cursor = await database_connection(database_name)

    cursor.execute("""
        DELETE FROM user_boost_keys
        WHERE user_id = ? AND boost_key = ?;
    """, (user_id, boost_key))

    cursor.execute("""
        SELECT COUNT(*) FROM user_boost_keys WHERE boost_key = ?;
    """, (boost_key,))
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("DELETE FROM boost_keys WHERE boost_key = ?;", (boost_key,))

    connection.commit()
    connection.close()


async def get_boost_keys_for_user(user_id: int, database_name : str) -> List[Tuple[str, int]]:
    connection, cursor = await database_connection(database_name)
    cursor.execute("""
        SELECT bk.boost_key, bk.redeemable_boosts
        FROM boost_keys bk
        INNER JOIN user_boost_keys ubk ON bk.boost_key = ubk.boost_key
        WHERE ubk.user_id = ?;
    """, (user_id,))
    keys = cursor.fetchall()
    connection.close()
    return keys

async def check_user_has_valid_boost_key(user_id: int, database_name : str) -> Optional[Tuple[str, int]]:
    """
    Checks if a user has a valid boost key with at least one boost remaining.

    :param user_id: The ID of the user to check.
    :return: The boost key and remaining boosts if valid, None otherwise.
    """
    connection, cursor = await database_connection(database_name)
    cursor.execute("""
        SELECT bk.boost_key, bk.redeemable_boosts
        FROM boost_keys bk
        INNER JOIN user_boost_keys ubk ON bk.boost_key = ubk.boost_key
        WHERE ubk.user_id = ? AND bk.redeemable_boosts > 0
        LIMIT 1;
    """, (user_id,))
    result = cursor.fetchone()
    connection.close()
    return result

async def remove_boost_from_key(boost_key: str, boosts : int, database_name : str) -> bool:
    """
    Deducts one boost from the specified boost key.

    :param boost_key: The boost key to update.
    :param boosts: The amount of boosts to remove
    :return: True if deduction was successful, False otherwise.
    """
    connection, cursor = await database_connection(database_name)
    cursor.execute("""
        UPDATE boost_keys
        SET redeemable_boosts = redeemable_boosts - ?
        WHERE boost_key = ? AND redeemable_boosts > 0;
    """, (boosts, boost_key))
    success = cursor.rowcount > 0
    connection.commit()
    connection.close()
    return success