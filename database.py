import os
import sqlite3
from contextlib import contextmanager
import logging

# 可选导入pymysql，如果没有安装则跳过MySQL支持
try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False
    pymysql = None

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_type = os.getenv('DATABASE_TYPE', 'sqlite')  # 'mysql' or 'sqlite'
        
        # 如果请求MySQL但pymysql不可用，回退到SQLite
        if self.db_type == 'mysql' and not PYMYSQL_AVAILABLE:
            logger.warning("MySQL requested but pymysql not available, falling back to SQLite")
            self.db_type = 'sqlite'
        
        self.mysql_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'bollinger_strategy'),
            'charset': 'utf8mb4',
            'autocommit': True
        }
        self.sqlite_path = os.getenv('SQLITE_PATH', 'bollinger_strategy.db')
        
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        if self.db_type == 'mysql' and PYMYSQL_AVAILABLE:
            try:
                conn = pymysql.connect(**self.mysql_config)
                yield conn
                conn.close()
            except Exception as e:
                logger.error(f"MySQL连接失败: {e}")
                raise
        else:
            try:
                conn = sqlite3.connect(self.sqlite_path)
                conn.row_factory = sqlite3.Row
                yield conn
                conn.close()
            except Exception as e:
                logger.error(f"SQLite连接失败: {e}")
                raise
    
    def init_database(self):
        """初始化数据库表"""
        if self.db_type == 'mysql' and PYMYSQL_AVAILABLE:
            self._init_mysql_tables()
        else:
            self._init_sqlite_tables()
    
    def _init_mysql_tables(self):
        """初始化MySQL表"""
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            current_price DECIMAL(20,8),
            order_price DECIMAL(20,8),
            status VARCHAR(50),
            timeframe VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_symbol (symbol),
            INDEX idx_status (status),
            INDEX idx_timeframe (timeframe)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            price DECIMAL(20,8) NOT NULL,
            amount DECIMAL(20,8) NOT NULL,
            status VARCHAR(50) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_symbol (symbol),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        
        CREATE TABLE IF NOT EXISTS positions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            size DECIMAL(20,8) NOT NULL,
            price DECIMAL(20,8) NOT NULL,
            type ENUM('long', 'short') NOT NULL,
            current_price DECIMAL(20,8),
            pnl DECIMAL(10,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_symbol (symbol),
            INDEX idx_type (type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for statement in create_tables_sql.split(';'):
                    if statement.strip():
                        cursor.execute(statement)
    
    def _init_sqlite_tables(self):
        """初始化SQLite表"""
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            current_price REAL,
            order_price REAL,
            status TEXT,
            timeframe TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        """
        
        with self.get_connection() as conn:
            conn.executescript(create_tables_sql)
    
    def save_analysis_result(self, result):
        """保存分析结果"""
        if self.db_type == 'mysql':
            sql = """
            INSERT INTO analysis_results (symbol, current_price, order_price, status, timeframe)
            VALUES (%s, %s, %s, %s, %s)
            """
        else:
            sql = """
            INSERT INTO analysis_results (symbol, current_price, order_price, status, timeframe)
            VALUES (?, ?, ?, ?, ?)
            """
        
        with self.get_connection() as conn:
            if self.db_type == 'mysql':
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        result['symbol'],
                        result.get('current_price'),
                        result.get('order_price'),
                        result.get('status'),
                        result.get('timeframe', '1d')
                    ))
            else:
                cursor = conn.cursor()
                try:
                    cursor.execute(sql, (
                        result['symbol'],
                        result.get('current_price'),
                        result.get('order_price'),
                        result.get('status'),
                        result.get('timeframe', '1d')
                    ))
                    conn.commit()  # SQLite需要显式提交
                finally:
                    cursor.close()
    
    def get_analysis_results(self, limit=100):
        """获取分析结果"""
        if self.db_type == 'mysql':
            sql = "SELECT * FROM analysis_results ORDER BY created_at DESC LIMIT %s"
            params = (limit,)
        else:
            sql = "SELECT * FROM analysis_results ORDER BY created_at DESC LIMIT ?"
            params = (limit,)
        
        with self.get_connection() as conn:
            if self.db_type == 'mysql':
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.fetchall()
            else:
                cursor = conn.cursor()
                try:
                    cursor.execute(sql, params)
                    return cursor.fetchall()
                finally:
                    cursor.close()
    
    def save_order(self, order):
        """保存挂单"""
        if self.db_type == 'mysql':
            sql = """
            INSERT INTO orders (symbol, price, amount, status)
            VALUES (%s, %s, %s, %s)
            """
        else:
            sql = """
            INSERT INTO orders (symbol, price, amount, status)
            VALUES (?, ?, ?, ?)
            """
        
        with self.get_connection() as conn:
            if self.db_type == 'mysql':
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        order['symbol'],
                        order['price'],
                        order['amount'],
                        order.get('status', 'active')
                    ))
            else:
                cursor = conn.cursor()
                try:
                    cursor.execute(sql, (
                        order['symbol'],
                        order['price'],
                        order['amount'],
                        order.get('status', 'active')
                    ))
                    conn.commit()
                finally:
                    cursor.close()
    
    def get_orders(self):
        """获取所有挂单"""
        sql = "SELECT * FROM orders WHERE status = 'active' ORDER BY created_at DESC"
        
        with self.get_connection() as conn:
            if self.db_type == 'mysql':
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    return cursor.fetchall()
            else:
                cursor = conn.cursor()
                try:
                    cursor.execute(sql)
                    return cursor.fetchall()
                finally:
                    cursor.close()
    
    def save_position(self, position):
        """保存仓位"""
        if self.db_type == 'mysql':
            sql = """
            INSERT INTO positions (symbol, size, price, type, current_price, pnl)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
        else:
            sql = """
            INSERT INTO positions (symbol, size, price, type, current_price, pnl)
            VALUES (?, ?, ?, ?, ?, ?)
            """
        
        with self.get_connection() as conn:
            if self.db_type == 'mysql':
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        position['symbol'],
                        position['size'],
                        position['price'],
                        position['type'],
                        position.get('current_price'),
                        position.get('pnl', 0)
                    ))
            else:
                cursor = conn.cursor()
                try:
                    cursor.execute(sql, (
                        position['symbol'],
                        position['size'],
                        position['price'],
                        position['type'],
                        position.get('current_price'),
                        position.get('pnl', 0)
                    ))
                    conn.commit()
                finally:
                    cursor.close()
    
    def get_positions(self):
        """获取所有仓位"""
        sql = "SELECT * FROM positions ORDER BY created_at DESC"
        
        with self.get_connection() as conn:
            if self.db_type == 'mysql':
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    return cursor.fetchall()
            else:
                cursor = conn.cursor()
                try:
                    cursor.execute(sql)
                    return cursor.fetchall()
                finally:
                    cursor.close()

# 全局数据库管理器实例
db_manager = DatabaseManager()



