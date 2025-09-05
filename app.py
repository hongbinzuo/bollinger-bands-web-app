from flask import Flask, render_template, request, jsonify, send_file
import requests
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, date
from typing import List, Dict
import json
import os
from io import StringIO
import pickle

# 导入日内交易模块
from intraday_api import intraday_bp
from ultra_short_api import ultra_short_bp
from logs_api import logs_bp

app = Flask(__name__)

# 注册日内交易蓝图
app.register_blueprint(intraday_bp)
app.register_blueprint(ultra_short_bp)
app.register_blueprint(logs_bp)

# 设置日志
import logging
from logging.handlers import RotatingFileHandler
import os

# 创建logs目录
if not os.path.exists('logs'):
    os.makedirs('logs')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('logs/app.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 缓存文件路径
CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "bollinger_cache.pkl")

class BollingerBandsAnalyzer:
    def __init__(self):
        """初始化布林带分析器"""
        # Binance API
        self.binance_url = "https://api.binance.com/api/v3"
        # Gate.io API
        self.gate_url = "https://api.gateio.ws/api/v4"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 确保缓存目录存在
        os.makedirs(CACHE_DIR, exist_ok=True)
        
    def get_binance_klines(self, symbol: str, interval: str = '12h', limit: int = 100) -> pd.DataFrame:
        """从Binance获取K线数据"""
        try:
            url = f"{self.binance_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # 创建DataFrame
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 转换数据类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # 只保留需要的列
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            return df
            
        except Exception as e:
            logger.error(f"Binance获取 {symbol} K线数据失败: {e}")
            return pd.DataFrame()
    
    def get_gate_klines(self, symbol: str, interval: str = '12h', limit: int = 100) -> pd.DataFrame:
        """从Gate.io获取K线数据"""
        try:
            # Gate.io的interval格式转换
            interval_map = {
                '12h': '12h',
                '4h': '4h',
                '1d': '1d'
            }
            gate_interval = interval_map.get(interval, '12h')
            
            url = f"{self.gate_url}/spot/candlesticks"
            params = {
                'currency_pair': symbol,
                'interval': gate_interval,
                'limit': limit
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return pd.DataFrame()
            
            # 创建DataFrame - Gate.io返回8个字段
            df = pd.DataFrame(data, columns=[
                'timestamp', 'volume', 'close', 'high', 'low', 'open', 'extra1', 'extra2'
            ])
            
            # 转换数据类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            
            # 重新排列列顺序
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            return df
            
        except Exception as e:
            logger.error(f"Gate.io获取 {symbol} K线数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2) -> Dict:
        """计算布林带"""
        try:
            if len(df) < period:
                return None
            
            # 计算移动平均线（中轨）
            middle_band = df['close'].rolling(window=period).mean()
            
            # 计算标准差
            std = df['close'].rolling(window=period).std()
            
            # 计算上轨和下轨
            upper_band = middle_band + (std * std_dev)
            lower_band = middle_band - (std * std_dev)
            
            # 获取最新值
            current_price = df['close'].iloc[-1]
            current_middle = middle_band.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            return {
                'current_price': current_price,
                'middle_band': current_middle,
                'upper_band': current_upper,
                'lower_band': current_lower
            }
            
        except Exception as e:
            logger.error(f"计算布林带失败: {e}")
            return None
    
    def calculate_order_price(self, current_price: float, middle_band: float, upper_band: float, lower_band: float) -> str:
        """计算挂单价格"""
        try:
            # 如果当前币价在中轨和下轨之间，则挂单价格=下轨
            if lower_band <= current_price <= middle_band:
                return f"{lower_band:.6f}"
            
            # 如果当前币价在中轨与（中轨*1.02）的区间，则挂单价格=下轨
            upper_threshold = middle_band * 1.02
            if middle_band <= current_price <= upper_threshold:
                return f"{lower_band:.6f}"
            
            # 如果价格在上轨与中轨之间则挂单价格=中轨
            elif middle_band <= current_price <= upper_band:
                return f"{middle_band:.6f}"
            
            # 如果价格在下轨下方，则挂单价格=已破下轨
            elif current_price < lower_band:
                return "已破下轨"
            
            # 其他情况挂单价格=中轨
            else:
                return f"{middle_band:.6f}"
            
        except Exception as e:
            logger.error(f"计算挂单价格失败: {e}")
            return "计算失败"
    
    def analyze_symbol(self, symbol: str, force_refresh: bool = False) -> Dict:
        """分析单个币种"""
        try:
            logger.info(f"分析 {symbol}")
            
            # 检查缓存
            if not force_refresh:
                cached_result = self.get_cached_result(symbol)
                if cached_result:
                    logger.info(f"使用缓存数据: {symbol}")
                    return cached_result
            
            # 首先尝试Binance
            df = self.get_binance_klines(symbol, '12h', 100)
            
            if df.empty:
                # 如果Binance失败，尝试Gate.io
                logger.info(f"Binance获取失败，尝试Gate.io...")
                gate_symbol = symbol.replace('USDT', '_USDT')
                df = self.get_gate_klines(gate_symbol, '12h', 100)
                data_source = "Gate.io"
            else:
                data_source = "Binance"
            
            if df.empty:
                result = {
                    'symbol': symbol,
                    'current_price': None,
                    'middle_band': None,
                    'lower_band': None,
                    'order_price': None,
                    'status': '✗ 失败',
                    'data_source': 'None',
                    'cache_date': datetime.now().isoformat()
                }
                self.save_to_cache(symbol, result)
                return result
            
            # 计算布林带
            bb_data = self.calculate_bollinger_bands(df)
            
            if bb_data is None:
                result = {
                    'symbol': symbol,
                    'current_price': None,
                    'middle_band': None,
                    'lower_band': None,
                    'order_price': None,
                    'status': '✗ 计算失败',
                    'data_source': data_source,
                    'cache_date': datetime.now().isoformat()
                }
                self.save_to_cache(symbol, result)
                return result
            
            # 计算挂单价格
            order_price = self.calculate_order_price(
                bb_data['current_price'],
                bb_data['middle_band'],
                bb_data['upper_band'],
                bb_data['lower_band']
            )
            
            result = {
                'symbol': symbol,
                'current_price': bb_data['current_price'],
                'middle_band': bb_data['middle_band'],
                'lower_band': bb_data['lower_band'],
                'order_price': order_price,
                'status': '✓ 成功',
                'data_source': data_source,
                'cache_date': datetime.now().isoformat()
            }
            
            # 保存到缓存
            self.save_to_cache(symbol, result)
            return result
            
        except Exception as e:
            logger.error(f"分析 {symbol} 时出错: {e}")
            result = {
                'symbol': symbol,
                'current_price': None,
                'middle_band': None,
                'lower_band': None,
                'order_price': None,
                'status': '✗ 错误',
                'data_source': 'None',
                'cache_date': datetime.now().isoformat()
            }
            self.save_to_cache(symbol, result)
            return result
    
    def get_cached_result(self, symbol: str) -> Dict:
        """获取缓存结果"""
        try:
            if not os.path.exists(CACHE_FILE):
                return None
            
            with open(CACHE_FILE, 'rb') as f:
                cache_data = pickle.load(f)
            
            if symbol in cache_data:
                cached_result = cache_data[symbol]
                cache_date = datetime.fromisoformat(cached_result['cache_date'])
                current_date = datetime.now().date()
                
                # 检查是否是今天的数据
                if cache_date.date() == current_date:
                    return cached_result
            
            return None
            
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
            return None
    
    def save_to_cache(self, symbol: str, result: Dict):
        """保存结果到缓存"""
        try:
            cache_data = {}
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'rb') as f:
                    cache_data = pickle.load(f)
            
            cache_data[symbol] = result
            
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(cache_data, f)
                
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def clear_cache(self):
        """清除缓存"""
        try:
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)
                logger.info("缓存已清除")
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")

# 币种存储文件
SYMBOLS_FILE = os.path.join(CACHE_DIR, "custom_symbols.json")

# 默认币种列表
DEFAULT_SYMBOLS = [
    'ROAMUSDT', 'SAGAUSDT', 'SQDUSDT', 'SUNUSDT', 'USUALUSDT', 'KAVAUSDT', 'AERGOUSDT', 'LAYERUSDT', 'AVAAIUSDT', 'KAITOUSDT',
    'FISUSDT', 'MOCAUSDT', 'XCNUSDT', 'WALUSDT', 'DUCKUSDT', 'JUPUSDT', 'ZBCNUSDT', 'PENDLEUSDT', 'CETUSUSDT', 'HAEDALUSDT',
    'JOEUSDT', 'SPKUSDT', 'KASUSDT', 'EIGENUSDT', 'THEUSDT', 'BANKUSDT', 'ZRCUSDT', 'IKAUSDT', 'DOGEUSDT', 'PNUTUSDT',
    'MOODENGUSDT', 'HYPEUSDT', 'USELESSUSDT', 'JSTUSDT', 'CYBERUSDT', 'COOKIEUSDT', '1000BONKUSDT', '1000CATUSDT', 'B3USDT', 'HIFIUSDT', 'BLURUSDT',
    'SUPERUSDT', 'FORMUSDT', 'FUNUSDT', 'ANIMEUSDT', 'PARTIUSDT', 'SOPHUSDT', 'LAUSDT', 'DEGENUSDT', 'DENTUSDT', 'BABYUSDT',
    'MAGICUSDT', 'COSUSDT', 'ALICEUSDT', 'HEIUSDT', 'FIDAUSDT', 'TACUSDT', 'PIPPINUSDT', 'STOUSDT', 'DFUSDT', 'TAUSDT',
    'CAKEUSDT', 'IDUSDT', 'FUELUSDT', 'ASPUSDT', 'DOODUSDT', 'LOOKSUSDT', 'VELVETUSDT', 'SUNDOGUSDT', 'KERNELUSDT', 'ERAUSDT',
    'HUSDT', 'DBRUSDT', 'NXPCUSDT', 'LISTAUSDT', 'SYRUPUSDT', 'KATOUSDT', 'FLMUSDT', 'JASMYUSDT', 'SANTOSUSDT', 'SLPUSDT',
    'MAJORUSDT', 'TRUMPUSDT', 'HIPPOUSDT', 'KAIAUSDT', 'DIAUSDT', 'LSKUSDT', 'MERLUSDT', 'XRPUSDT', 'BTCUSDT', 'ETHUSDT',
    'LDOUSDT', 'ESUSDT', 'HUMAUSDT', 'PUMPUSDT', 'RAYUSDT', 'SOLUSDT', 'UNIUSDT', 'HBARUSDT', 'XLMUSDT', 'ICXUSDT',
    'XDCUSDT', 'BERAUSDT', 'ZORAUSDT', 'IPUSDT', 'LINKUSDT', 'ENAUSDT', 'SCRUSDT', 'MYROUSDT', 'UMAUSDT', 'TAGUSDT',
    'TOSHIUSDT', 'SOONUSDT', 'ICNTUSDT', 'IDOLUSDT', 'INITUSDT', 'CATIUSDT', 'ALPINEUSDT', 'PROVEUSDT', 'LUNAUSDT', 'A2ZUSDT',
    'BIDUSDT', 'DEEPUSDT', 'RADUSDT', 'RWAUSDT', 'IOUSDT', 'PONKEUSDT', 'GTCUSDT', 'KUSDT', 'HMSTRUSDT'
]

def load_custom_symbols():
    """加载自定义币种列表"""
    try:
        if os.path.exists(SYMBOLS_FILE):
            with open(SYMBOLS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('symbols', [])
        return []
    except Exception as e:
        logger.error(f"加载自定义币种失败: {e}")
        return []

def save_custom_symbols(symbols):
    """保存自定义币种列表"""
    try:
        data = {
            'symbols': symbols,
            'updated_at': datetime.now().isoformat()
        }
        with open(SYMBOLS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"自定义币种已保存，共 {len(symbols)} 个")
    except Exception as e:
        logger.error(f"保存自定义币种失败: {e}")

def get_all_symbols():
    """获取所有币种（默认 + 自定义）"""
    custom_symbols = load_custom_symbols()
    all_symbols = list(set(DEFAULT_SYMBOLS + custom_symbols))  # 去重
    return all_symbols

# 记录应用启动信息
logger.info("=== 布林带策略系统启动 ===")
all_symbols = get_all_symbols()
custom_symbols = load_custom_symbols()
logger.info(f"默认币种数量: {len(DEFAULT_SYMBOLS)}")
logger.info(f"自定义币种数量: {len(custom_symbols)}")
logger.info(f"总币种数量: {len(all_symbols)}")
logger.info("日志文件位置: logs/app.log")
logger.info(f"前10个币种: {all_symbols[:10]}")

# 全局分析器实例
analyzer = BollingerBandsAnalyzer()

def validate_symbols(symbols_str: str) -> List[str]:
    """验证币种格式"""
    try:
        # 分割并清理
        symbols = [s.strip().upper() for s in symbols_str.split(',') if s.strip()]
        
        # 验证格式：只允许字母和数字
        valid_symbols = []
        for symbol in symbols:
            if symbol and symbol.isalnum() and len(symbol) <= 10:
                valid_symbols.append(symbol)
            else:
                logger.warning(f"无效币种格式: {symbol}")
        
        return valid_symbols
    except Exception as e:
        logger.error(f"验证币种格式失败: {e}")
        return []

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/get_default_symbols', methods=['GET'])
def get_default_symbols():
    """获取默认币种列表"""
    all_symbols = get_all_symbols()
    logger.info(f"获取币种列表请求，总币种数量: {len(all_symbols)}")
    return jsonify({
        'symbols': all_symbols,
        'count': len(all_symbols)
    })

@app.route('/add_symbols', methods=['POST'])
def add_symbols():
    """新增币种"""
    try:
        data = request.get_json()
        new_symbols = data.get('symbols', [])
        
        if not new_symbols:
            return jsonify({
                'success': False,
                'error': '请提供要新增的币种'
            })
        
        # 验证币种格式
        valid_symbols = []
        for symbol in new_symbols:
            symbol = symbol.strip().upper()
            if symbol and symbol.isalnum() and len(symbol) <= 10:
                # 确保币种以USDT结尾
                if not symbol.endswith('USDT'):
                    symbol += 'USDT'
                valid_symbols.append(symbol)
            else:
                logger.warning(f"无效币种格式: {symbol}")
        
        if not valid_symbols:
            return jsonify({
                'success': False,
                'error': '没有有效的币种格式'
            })
        
        # 加载现有自定义币种
        existing_custom_symbols = load_custom_symbols()
        
        # 合并新币种（去重）
        all_custom_symbols = list(set(existing_custom_symbols + valid_symbols))
        
        # 保存更新后的币种列表
        save_custom_symbols(all_custom_symbols)
        
        # 获取总币种数量
        total_symbols = len(get_all_symbols())
        
        logger.info(f"新增币种成功: {valid_symbols}, 当前总币种数量: {total_symbols}")
        
        return jsonify({
            'success': True,
            'added_symbols': valid_symbols,
            'total_symbols': total_symbols,
            'message': f'成功新增 {len(valid_symbols)} 个币种'
        })
        
    except Exception as e:
        logger.error(f"新增币种失败: {e}")
        return jsonify({
            'success': False,
            'error': f'新增币种失败: {str(e)}'
        })

@app.route('/debug/symbols', methods=['GET'])
def debug_symbols():
    """调试页面：显示当前币种列表"""
    logger.info("访问调试页面")
    all_symbols = get_all_symbols()
    custom_symbols = load_custom_symbols()
    symbols_without_usdt = [s.replace('USDT', '') for s in all_symbols]
    custom_symbols_without_usdt = [s.replace('USDT', '') for s in custom_symbols]
    
    return f"""
    <html>
    <head><title>调试页面 - 币种列表</title></head>
    <body>
        <h1>调试页面 - 当前币种列表</h1>
        <p><strong>默认币种数量:</strong> {len(DEFAULT_SYMBOLS)}</p>
        <p><strong>自定义币种数量:</strong> {len(custom_symbols)}</p>
        <p><strong>总币种数量:</strong> {len(all_symbols)}</p>
        
        <h2>自定义币种:</h2>
        <p>{', '.join(custom_symbols_without_usdt) if custom_symbols_without_usdt else '无'}</p>
        
        <h2>前20个币种:</h2>
        <ul>
            {''.join([f'<li>{s}</li>' for s in symbols_without_usdt[:20]])}
        </ul>
        <p><strong>完整列表:</strong></p>
        <textarea rows="20" cols="80">{', '.join(symbols_without_usdt)}</textarea>
        <br><br>
        <a href="/">返回主页</a>
    </body>
    </html>
    """

@app.route('/analyze', methods=['POST'])
def analyze():
    """分析币种"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])  # 获取前端传来的币种列表
        force_refresh = data.get('force_refresh', False)
        
        # 如果没有提供币种列表，使用所有币种列表
        if not symbols:
            all_symbols = get_all_symbols()
            symbols = [s.replace('USDT', '') for s in all_symbols]  # 移除USDT后缀用于处理
        
        # 确保所有币种都有USDT后缀
        symbols_with_usdt = []
        for symbol in symbols:
            if not symbol.endswith('USDT'):
                symbols_with_usdt.append(f"{symbol}USDT")
            else:
                symbols_with_usdt.append(symbol)
        
        results = []
        for i, symbol in enumerate(symbols_with_usdt):
            try:
                logger.info(f"处理 {symbol} ({i+1}/{len(symbols_with_usdt)})")
                
                result = analyzer.analyze_symbol(symbol, force_refresh)
                results.append(result)
                
                # 延迟控制
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"处理 {symbol} 时出错: {e}")
                continue
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        })
        
    except Exception as e:
        logger.error(f"分析请求失败: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/clear_cache', methods=['POST'])
def clear_cache():
    """清除缓存"""
    try:
        analyzer.clear_cache()
        return jsonify({
            'success': True,
            'message': '缓存已清除'
        })
        
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_csv', methods=['POST'])
def download_csv():
    """下载CSV文件"""
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({'error': '没有数据可下载'}), 400
        
        # 创建CSV数据
        csv_data = []
        for result in results:
            symbol = result['symbol'].replace('USDT', '')  # 去掉USDT后缀
            current_price = result['current_price']
            middle_band = result['middle_band']
            lower_band = result['lower_band']
            order_price = result['order_price']
            status = result['status']
            data_source = result['data_source']
            cache_date = result.get('cache_date', '')
            
            if current_price is not None and middle_band is not None and lower_band is not None and order_price is not None:
                csv_data.append({
                    '币种': symbol,
                    '当前价格': f"{current_price:.6f}",
                    '中轨': f"{middle_band:.6f}",
                    '下轨': f"{lower_band:.6f}",
                    '挂单价格': order_price,
                    '状态': status,
                    '数据源': data_source,
                    '缓存时间': cache_date
                })
            else:
                csv_data.append({
                    '币种': symbol,
                    '当前价格': '获取失败',
                    '中轨': '获取失败',
                    '下轨': '获取失败',
                    '挂单价格': '获取失败',
                    '状态': status,
                    '数据源': data_source,
                    '缓存时间': cache_date
                })
        
        # 创建DataFrame并转换为CSV
        df = pd.DataFrame(csv_data)
        csv_string = df.to_csv(index=False, encoding='utf-8-sig')
        
        # 创建文件对象
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bollinger_bands_analysis_{timestamp}.csv"
        
        return jsonify({
            'success': True,
            'filename': filename,
            'csv_data': csv_string
        })
        
    except Exception as e:
        logger.error(f"下载CSV失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # 创建templates目录
    os.makedirs('templates', exist_ok=True)
    
    # 运行应用
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
