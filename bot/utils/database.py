import sqlite3
import logging
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

def get_db_connection():
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create the chats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    chat_type TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    settings TEXT DEFAULT '{}'
                )
            """)
            
            # Create the media exceptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_exceptions (
                    exception_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    file_unique_id TEXT NOT NULL,
                    UNIQUE(chat_id, file_unique_id)
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.critical(f"Database initialization failed: {e}")
        raise

def add_chat(chat_id: int, chat_type: str):
    """Adds or reactivates a chat in the database."""
    sql = """
        INSERT INTO chats (chat_id, chat_type, is_active)
        VALUES (?, ?, 1)
        ON CONFLICT(chat_id) DO UPDATE SET
        is_active = 1, chat_type = excluded.chat_type;
    """
    try:
        with get_db_connection() as conn:
            conn.execute(sql, (chat_id, chat_type))
            conn.commit()
            logger.info(f"Added/Reactivated chat: {chat_id}")
    except sqlite3.Error as e:
        logger.error(f"Failed to add chat {chat_id}: {e}")

def set_chat_inactive(chat_id: int):
    """Marks a chat as inactive in the database."""
    sql = "UPDATE chats SET is_active = 0 WHERE chat_id = ?;"
    try:
        with get_db_connection() as conn:
            conn.execute(sql, (chat_id,))
            conn.commit()
            logger.info(f"Deactivated chat: {chat_id}")
    except sqlite3.Error as e:
        logger.error(f"Failed to deactivate chat {chat_id}: {e}")

def get_all_active_chats() -> list[int]:
    """Retrieves a list of all active chat IDs for broadcasting."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT chat_id FROM chats WHERE is_active = 1;")
            return [row['chat_id'] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to get active chats: {e}")
        return []

def add_media_exception(chat_id: int, file_unique_id: str) -> bool:
    """Adds a media exception for a specific chat."""
    sql = "INSERT OR IGNORE INTO media_exceptions (chat_id, file_unique_id) VALUES (?, ?);"
    try:
        with get_db_connection() as conn:
            conn.execute(sql, (chat_id, file_unique_id))
            conn.commit()
            logger.info(f"Added exception for file {file_unique_id} in chat {chat_id}")
            return True
    except sqlite3.Error as e:
        logger.error(f"Failed to add exception for file {file_unique_id} in {chat_id}: {e}")
        return False

def check_media_exception(chat_id: int, file_unique_id: str) -> bool:
    """Checks if a media item is in the exception list for a chat."""
    sql = "SELECT 1 FROM media_exceptions WHERE chat_id = ? AND file_unique_id = ?;"
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(sql, (chat_id, file_unique_id))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Failed to check exception for file {file_unique_id} in {chat_id}: {e}")
        return False