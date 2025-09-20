import pandas as pd
import numpy as np
import requests
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional

# --- 日志配置 (建议放在文件开头) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MultiTimeframeStrategy:
    def __init__(self):
        self.timeframes = ['4h', '8h', '12h', '1d', '3d', '1w']
        self.ema_periods = [89, 144, 233, 377]  # 89/144/233必须，377可选
        self.bb_period = 20  # 布林带周期
        self.bb_std = 2      # 布林带标准差
        
        # 北京时间时区 (UTC+8)
        self.beijing_tz = timezone(timedelta(hours=8))
        
        # 时间框架对应的止盈时间框架
        self.take_profit_timeframes = {
            '4h': '3m',   # 4小时对应3分钟
            '8h': '5m',   # 8小时对应5分钟
            '12h': '15m', # 12小时对应15分钟 (移除10m，Gate.io不支持)
            '1d': '15m',  # 1天对应15分钟
            '3d': '30m',  # 3天对应30分钟
            '1w': '1h'    # 1周对应1小时
        }
        
        # 记录每个币种每个时间框架的EMA使用情况
        self.ema_usage = {}
        
        # 多线程配置
        self.max_workers = 8  # 最大并发线程数
        self.request_delay = 0.05  # 请求间隔（秒）
        self.batch_size = 20  # 每批处理的币种数量
        
        # 线程锁
        self.lock = threading.Lock()
    
    def get_beijing_time(self):
        """获取北京时间 (UTC+8)"""
        return datetime.now(self.beijing_tz)
        
    def get_klines_data(self, symbol: str, interval: str, limit: int = 1000) -> pd.DataFrame:
        """获取K线数据 - 优先使用Gate.io API"""
        try:
            # 首先尝试Gate.io API
            gate_result = self._get_gate_klines(symbol, interval, limit)
            if gate_result is not None and not gate_result.empty:
                logger.info(f"成功从 Gate.io 获取 {symbol} {interval} 的数据")
                return gate_result
            
            # Gate.io失败时，尝试币安期货API作为备用
            logger.warning(f"Gate.io 获取失败, 尝试使用 Binance Futures API: {symbol} {interval}")
            binance_result = self._get_binance_futures_klines(symbol, interval, limit)
            if binance_result is not None and not binance_result.empty:
                logger.info(f"成功从 Binance Futures API 获取 {symbol} {interval} 的数据")
                return binance_result
            
            # 最后尝试币安现货API
            logger.warning(f"Binance Futures API 获取失败, 尝试使用 Binance Spot API: {symbol} {interval}")
            spot_result = self._get_binance_spot_klines(symbol, interval, limit)
            if spot_result is not None and not spot_result.empty:
                logger.info(f"成功从 Binance Spot API 获取 {symbol} {interval} 的数据")
                return spot_result

            logger.error(f"所有数据源均未能获取到 {symbol} {interval} 的数据")
            return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"在 get_klines_data 中获取 {symbol} {interval} 数据时发生未知异常: {e}")
            return pd.DataFrame()
    
    def _try_multiple_symbol_formats(self, symbol: str, exchange: str) -> List[str]:
        """尝试多种币种格式，返回可能的格式列表"""
        formats = []
        
        # 原始格式
        formats.append(self._normalize_symbol_for_exchange(symbol, exchange))
        
        # 处理1000PEPE -> PEPE的情况
        if symbol.startswith('1000'):
            base_symbol = symbol[4:]  # 去掉1000前缀
            formats.append(self._normalize_symbol_for_exchange(base_symbol, exchange))
        
        # 处理PEPE -> 1000PEPE的情况
        if not symbol.startswith('1000') and len(symbol) <= 6:
            formats.append(self._normalize_symbol_for_exchange(f"1000{symbol}", exchange))
        
        # 去重并返回
        return list(set(formats))

    def _normalize_symbol_for_exchange(self, symbol: str, exchange: str) -> str:
        """标准化币种名称以匹配不同交易所的格式"""
        symbol = symbol.upper()
        
        # 币种名称映射表 - 扩展版本
        symbol_mapping = {
            # 主流币种
            'BNB': 'BNBUSDT', 'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'ADA': 'ADAUSDT', 'DOT': 'DOTUSDT',
            'LINK': 'LINKUSDT', 'LTC': 'LTCUSDT', 'BCH': 'BCHUSDT', 'XLM': 'XLMUSDT', 'EOS': 'EOSUSDT',
            'TRX': 'TRXUSDT', 'XMR': 'XMRUSDT', 'DASH': 'DASHUSDT', 'NEO': 'NEOUSDT', 'IOTA': 'IOTAUSDT',
            'ETC': 'ETCUSDT', 'XEM': 'XEMUSDT', 'ZEC': 'ZECUSDT', 'QTUM': 'QTUMUSDT', 'OMG': 'OMGUSDT',
            
            # 更多主流币种
            'XRP': 'XRPUSDT', 'DOGE': 'DOGEUSDT', 'SHIB': 'SHIBUSDT', 'MATIC': 'MATICUSDT', 'AVAX': 'AVAXUSDT',
            'SOL': 'SOLUSDT', 'ATOM': 'ATOMUSDT', 'FTM': 'FTMUSDT', 'ALGO': 'ALGOUSDT', 'VET': 'VETUSDT',
            'ICP': 'ICPUSDT', 'FIL': 'FILUSDT', 'THETA': 'THETAUSDT', 'AAVE': 'AAVEUSDT', 'UNI': 'UNIUSDT',
            'SUSHI': 'SUSHIUSDT', 'COMP': 'COMPUSDT', 'MKR': 'MKRUSDT', 'YFI': 'YFIUSDT', 'SNX': 'SNXUSDT',
            
            # DeFi币种
            'CRV': 'CRVUSDT', '1INCH': '1INCHUSDT', 'BAL': 'BALUSDT', 'KNC': 'KNCUSDT', 'REN': 'RENUSDT',
            'LRC': 'LRCUSDT', 'ZRX': 'ZRXUSDT', 'BAT': 'BATUSDT', 'ENJ': 'ENJUSDT', 'MANA': 'MANAUSDT',
            'SAND': 'SANDUSDT', 'AXS': 'AXSUSDT', 'CHZ': 'CHZUSDT', 'FLOW': 'FLOWUSDT', 'NEAR': 'NEARUSDT',
            
            # Layer 1币种
            'LUNA': 'LUNAUSDT', 'FTT': 'FTTUSDT', 'ROSE': 'ROSEUSDT', 'HBAR': 'HBARUSDT', 'EGLD': 'EGLDUSDT',
            'KAVA': 'KAVAUSDT', 'BAND': 'BANDUSDT', 'ZIL': 'ZILUSDT', 'ONT': 'ONTUSDT', 'ICX': 'ICXUSDT',
            'WAVES': 'WAVESUSDT', 'RVN': 'RVNUSDT', 'DGB': 'DGBUSDT', 'SC': 'SCUSDT', 'DCR': 'DCRUSDT',
            
            # 新兴币种
            'CAKE': 'CAKEUSDT', 'BAKE': 'BAKEUSDT', 'BURGER': 'BURGERUSDT', 'SXP': 'SXPUSDT', 'ALPHA': 'ALPHAUSDT',
            'BEL': 'BELUSDT', 'BETA': 'BETAUSDT', 'RAMP': 'RAMPUSDT', 'TLM': 'TLMUSDT', 'QUICK': 'QUICKUSDT',
            'COTI': 'COTIUSDT', 'CHR': 'CHRUSDT', 'MDX': 'MDXUSDT', 'STMX': 'STMXUSDT', 'KMD': 'KMDUSDT',
            
            # 更多币种
            'REEF': 'REEFUSDT', 'DENT': 'DENTUSDT', 'WIN': 'WINUSDT', 'MFT': 'MFTUSDT', 'CVC': 'CVCUSDT',
            'REQ': 'REQUSDT', 'DATA': 'DATAUSDT', 'NULS': 'NULSUSDT', 'FUN': 'FUNUSDT', 'NKN': 'NKNUSDT',
            'LINA': 'LINAUSDT', 'PERP': 'PERPUSDT', 'RLC': 'RLCUSDT', 'CTSI': 'CTSIUSDT', 'LIT': 'LITUSDT',
            'BADGER': 'BADGERUSDT', 'FIS': 'FISUSDT', 'OM': 'OMUSDT', 'POND': 'PONDUSDT', 'DEGO': 'DEGOUSDT',
            'ALICE': 'ALICEUSDT', 'LINA': 'LINAUSDT', 'PERP': 'PERPUSDT', 'RLC': 'RLCUSDT', 'CTSI': 'CTSIUSDT',
            
            # 热门币种
            'GALA': 'GALAUSDT', 'ILV': 'ILVUSDT', 'YGG': 'YGGUSDT', 'SYS': 'SYSUSDT', 'DF': 'DFUSDT',
            'FIDA': 'FIDAUSDT', 'FRONT': 'FRONTUSDT', 'CVP': 'CVPUSDT', 'AGLD': 'AGLDUSDT', 'RAD': 'RADUSDT',
            'BETA': 'BETAUSDT', 'RARE': 'RAREUSDT', 'LAZIO': 'LAZIOUSDT', 'ADX': 'ADXUSDT', 'AUCTION': 'AUCTIONUSDT',
            'DAR': 'DARUSDT', 'BNX': 'BNXUSDT', 'RGT': 'RGTUSDT', 'MOVR': 'MOVRUSDT', 'CITY': 'CITYUSDT',
            'ENS': 'ENSUSDT', 'KP3R': 'KP3RUSDT', 'QI': 'QIUSDT', 'PORTO': 'PORTOUSDT', 'POWR': 'POWRUSDT',
            'VGX': 'VGXUSDT', 'JASMY': 'JASMYUSDT', 'AMP': 'AMPUSDT', 'PLA': 'PLAUSDT', 'PYTH': 'PYTHUSDT',
            'RNDR': 'RNDRUSDT', 'ALCX': 'ALCXUSDT', 'SFP': 'SFPUSDT', 'FXS': 'FXSUSDT', 'HOOK': 'HOOKUSDT',
            'MAGIC': 'MAGICUSDT', 'HFT': 'HFTUSDT', 'PHB': 'PHBUSDT', 'PENDLE': 'PENDLEUSDT', 'ARKM': 'ARKMUSDT',
            'MAV': 'MAVUSDT', 'CFX': 'CFXUSDT', 'BLUR': 'BLURUSDT', 'EDU': 'EDUUSDT', 'ID': 'IDUSDT',
            'SUI': 'SUIUSDT', '1000PEPE': '1000PEPEUSDT', 'FLOKI': 'FLOKIUSDT', 'INJ': 'INJUSDT', 'PEPE': 'PEPEUSDT',
            'TIA': 'TIAUSDT', 'SEI': 'SEIUSDT', 'WLD': 'WLDUSDT', 'ARK': 'ARKUSDT', 'JTO': 'JTOUSDT',
            '1000SATS': '1000SATSUSDT', 'BONK': 'BONKUSDT', 'ACE': 'ACEUSDT', 'NFP': 'NFPUSDT', 'AI': 'AIUSDT',
            'XAI': 'XAIUSDT', 'MANTA': 'MANTAUSDT', 'ALT': 'ALTUSDT', 'JUP': 'JUPUSDT', 'PIXEL': 'PIXELUSDT',
            'PORTAL': 'PORTALUSDT', 'PDA': 'PDAUSDT', 'AEVO': 'AEVOUSDT', 'BOME': 'BOMEUSDT', 'ENA': 'ENAUSDT',
            'W': 'WUSDT', 'TAO': 'TAOUSDT', 'SAGA': 'SAGAUSDT', 'BB': 'BBUSDT', 'NOT': 'NOTUSDT',
            'OMNI': 'OMNIUSDT', 'REZ': 'REZUSDT', 'IO': 'IOUSDT', 'ZRO': 'ZROUSDT', 'ZK': 'ZKUSDT',
            'ZKSYNC': 'ZKSYNCUSDT', 'ZK': 'ZKUSDT', 'ZKSYNC': 'ZKSYNCUSDT', 'ZK': 'ZKUSDT', 'ZKSYNC': 'ZKSYNCUSDT'
        }
        
        # 特殊格式处理：处理带斜杠的币种名称
        if '/' in symbol:
            symbol = symbol.replace('/', '')
        
        if exchange == 'gate':
            # Gate.io格式：BTCUSDT -> BTC_USDT
            if symbol.endswith('USDT'):
                base = symbol[:-4]  # 去掉USDT
                return f"{base}_USDT"
            elif symbol in symbol_mapping:
                # 如果是短名称，先转换为完整名称
                full_symbol = symbol_mapping[symbol]
                base = full_symbol[:-4]  # 去掉USDT
                return f"{base}_USDT"
            else:
                # 智能匹配：尝试添加USDT后缀
                if not symbol.endswith('USDT'):
                    return f"{symbol}_USDT"
                return symbol
        elif exchange == 'binance':
            # 币安格式：保持原样，但处理特殊情况
            if symbol in symbol_mapping:
                return symbol_mapping[symbol]
            else:
                # 智能匹配：尝试添加USDT后缀
                if not symbol.endswith('USDT'):
                    return f"{symbol}USDT"
                return symbol
        else:
            return symbol

    def _get_gate_klines(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """
        【已修复】使用Gate.io API获取K线数据
        修复点:
        1. 直接在创建DataFrame时指定正确的列名，解决 'timestamp' not in columns 错误。
        2. 修正了列的顺序以匹配Gate.io API文档: [t, v, c, h, l, o]。
        3. 增加了数据反转 `df.iloc[::-1]`，使数据从新到旧排序。
        4. 统一了返回类型为 Optional[pd.DataFrame]。
        5. 添加了币种名称标准化。
        """
        try:
            gate_symbol = self._normalize_symbol_for_exchange(symbol, 'gate')
            
            interval_map = {
                '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',
                '1d': '1d', '3d': '3d', '1w': '1w'
            }
            gate_interval = interval_map.get(interval)
            if not gate_interval:
                logger.error(f"Gate.io 不支持的时间周期: {interval}")
                return None

            url = "https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': gate_symbol,
                'interval': gate_interval,
                'limit': min(limit, 1000)
            }
            
            with requests.Session() as session:
                response = session.get(url, params=params, timeout=15)
                response.raise_for_status() # 如果状态码不是2xx，则抛出HTTPError

            data = response.json()

            if not isinstance(data, list) or not data:
                logger.warning(f"Gate.io 返回空数据或无效数据格式 for {symbol} on {interval}")
                return pd.DataFrame() # 返回空DataFrame表示币种可能不存在

            # --- 核心修复 ---
            # 1. 根据Gate.io API V4文档，正确指定列名和顺序
            # 格式: [t:timestamp, v:volume, c:close, h:high, l:low, o:open]
            # 先创建DataFrame，再根据实际列数设置列名
            df = pd.DataFrame(data)
            if len(data[0]) == 8:
                df.columns = ['timestamp', 'volume', 'close', 'high', 'low', 'open', 'amount', 'count']
            elif len(data[0]) == 6:
                df.columns = ['timestamp', 'volume', 'close', 'high', 'low', 'open']
            else:
                # 通用格式：前6列固定，后面的列用数字命名
                base_columns = ['timestamp', 'volume', 'close', 'high', 'low', 'open']
                extra_columns = [f'col_{i}' for i in range(6, len(data[0]))]
                df.columns = base_columns + extra_columns
            
            # --- 数据类型转换和处理 ---
            # 转换timestamp列
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='s')
            elif 'timestamp_str' in df.columns:
                df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp_str']), unit='s')
            df = df.astype({
                'open': 'float', 'high': 'float', 'low': 'float',
                'close': 'float', 'volume': 'float'
            })
            
            df.set_index('timestamp', inplace=True)
            
            # 重新排列列顺序以符合通用标准 (OHLCV)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            # 保持数据时间升序，便于正确计算技术指标
            # 不反转数据，技术指标需要时间升序数据才能正确计算
            # 最新数据位于 df.iloc[-1]，历史数据位于 df.iloc[0] 等
            
            return df
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                logger.warning(f"Gate.io 请求失败 (可能是币种不存在): {gate_symbol}, Status: {e.response.status_code}")
            else:
                logger.error(f"Gate.io HTTP Error for {symbol} ({interval}): {e}")
            return pd.DataFrame() # 明确返回空DF
        except requests.exceptions.RequestException as e:
            logger.error(f"Gate.io 网络请求异常 for {symbol} ({interval}): {e}")
            return None # 返回None表示网络问题，可以尝试备用源
        except Exception as e:
            logger.error(f"处理 Gate.io 数据时发生未知错误 for {symbol} ({interval}): {e}")
            return None

    def _get_binance_futures_klines(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """使用币安期货API获取K线数据（备用）"""
        # 尝试多种币种格式
        symbol_formats = self._try_multiple_symbol_formats(symbol, 'binance')
        url = "https://fapi.binance.com/fapi/v1/klines"
        
        for binance_symbol in symbol_formats:
            try:
                params = {'symbol': binance_symbol, 'interval': interval, 'limit': limit}
                
                with requests.Session() as session:
                    response = session.get(url, params=params, timeout=15)
                    response.raise_for_status()

                data = response.json()
                if not data:
                    continue

                # 确保数据有12列
                if len(data[0]) == 12:
                    df = pd.DataFrame(data, columns=[ 
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                        'taker_buy_quote', 'ignore'
                    ])
                else:
                    # 如果列数不匹配，使用通用方法
                    df = pd.DataFrame(data)
                    if len(data[0]) >= 6:
                        # 确保第一列是timestamp
                        base_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                        extra_columns = [f'col_{i}' for i in range(6, len(data[0]))]
                        df.columns = base_columns + extra_columns
                    else:
                        logger.error(f"币安期货API数据列数不足: {len(data[0])} 列")
                        continue
                
                # 检查timestamp列是否存在并转换
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                else:
                    logger.error(f"币安期货API缺少timestamp列，实际列名: {list(df.columns)}")
                    continue
                
                # 转换数值列
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 重新排列列顺序并设置索引
                df = df[['open', 'high', 'low', 'close', 'volume']]
                df.set_index('timestamp', inplace=True)
                logger.info(f"币安期货API成功获取 {binance_symbol} 数据")
                # 保持时间升序，不反转数据
                return df
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400:
                    logger.warning(f"币安期货API币种 {binance_symbol} 不存在，尝试下一个格式")
                    continue
                else:
                    logger.error(f"Binance Futures HTTP Error for {binance_symbol}: {e}")
                    continue
            except requests.exceptions.RequestException as e:
                logger.error(f"Binance Futures API 网络请求异常 for {binance_symbol}: {e}")
                continue
            except Exception as e:
                logger.error(f"处理 Binance Futures 数据时发生未知错误 for {binance_symbol}: {e}")
                continue
        
        # 所有格式都失败了
        logger.warning(f"币安期货API所有格式都失败: {symbol}")
        return pd.DataFrame()

    def _get_binance_spot_klines(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """使用币安现货API获取K线数据（最后备用）"""
        # 尝试多种币种格式
        symbol_formats = self._try_multiple_symbol_formats(symbol, 'binance')
        url = "https://api.binance.com/api/v3/klines"
        
        for binance_symbol in symbol_formats:
            try:
                params = {'symbol': binance_symbol, 'interval': interval, 'limit': limit}

                with requests.Session() as session:
                    response = session.get(url, params=params, timeout=15)
                    response.raise_for_status()
                
                data = response.json()
                if not data:
                    continue
                
                # 确保数据有12列
                if len(data[0]) == 12:
                    df = pd.DataFrame(data, columns=[
                        'open_time', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                        'taker_buy_quote', 'ignore'
                    ])
                else:
                    # 如果列数不匹配，使用通用方法
                    df = pd.DataFrame(data)
                    if len(data[0]) >= 6:
                        # 确保第一列是open_time
                        base_columns = ['open_time', 'open', 'high', 'low', 'close', 'volume']
                        extra_columns = [f'col_{i}' for i in range(6, len(data[0]))]
                        df.columns = base_columns + extra_columns
                    else:
                        logger.error(f"币安现货API数据列数不足: {len(data[0])} 列")
                        continue
                
                # 检查open_time列是否存在并转换为timestamp
                if 'open_time' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
                else:
                    logger.error(f"币安现货API缺少open_time列，实际列名: {list(df.columns)}")
                    continue
                
                # 转换数值列
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # 重新排列列顺序并设置索引
                df = df[['open', 'high', 'low', 'close', 'volume']]
                df.set_index('timestamp', inplace=True)
                logger.info(f"币安现货API成功获取 {binance_symbol} 数据")
                # 保持时间升序，不反转数据
                return df
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400:
                    logger.warning(f"币安现货API币种 {binance_symbol} 不存在，尝试下一个格式")
                    continue
                else:
                    logger.error(f"Binance Spot HTTP Error for {binance_symbol}: {e}")
                    continue
            except requests.exceptions.RequestException as e:
                logger.error(f"Binance Spot API 网络请求异常 for {binance_symbol}: {e}")
                continue
            except Exception as e:
                logger.error(f"处理 Binance Spot 数据时发生未知错误 for {binance_symbol}: {e}")
                continue
        
        # 所有格式都失败了
        logger.warning(f"币安现货API所有格式都失败: {symbol}")
        return pd.DataFrame()
    
    def calculate_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        """【已优化】使用Pandas内置函数计算EMA指标，性能更高"""
        for period in self.ema_periods:
            df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        return df
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std: float = 2) -> pd.DataFrame:
        """【已优化】使用Pandas内置函数计算布林带，性能更高"""
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        df['bb_std'] = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std)
        return df
    
    def is_bullish_trend(self, df: pd.DataFrame) -> bool:
        """判断是否为多头趋势（EMA89 > EMA144 > EMA233，377可选）"""
        required_emas = ['ema89', 'ema144', 'ema233']
        if not all(ema in df.columns for ema in required_emas) or len(df) < 1:
            return False
        # 使用最新数据（时间升序，最新在最后）
        return df['ema89'].iloc[-1] > df['ema144'].iloc[-1] > df['ema233'].iloc[-1]
    
    def is_bearish_trend(self, df: pd.DataFrame) -> bool:
        """判断是否为空头趋势（EMA89 < EMA144 < EMA233，377可选）"""
        required_emas = ['ema89', 'ema144', 'ema233']
        if not all(ema in df.columns for ema in required_emas) or len(df) < 1:
            return False
        # 使用最新数据（时间升序，最新在最后）
        return df['ema89'].iloc[-1] < df['ema144'].iloc[-1] < df['ema233'].iloc[-1]
    
    def find_ema_pullback_levels(self, df: pd.DataFrame, trend: str) -> List[Dict]:
        """改进：加入趋势确认和量能过滤的回踩信号"""
        # 数据现在是时间升序，最新数据在最后 (iloc[-1])
        if len(df) < 20: # 确保有足够数据计算滚动均值
            return []
        
        current_candle = df.iloc[-1]  # 最新K线
        current_price = current_candle['close']
        current_time = self.get_beijing_time()  # 使用北京时间作为信号时间
        # 修复成交量均值计算，使用前一根K线的滚动量
        avg_volume = df['volume'].rolling(window=20).mean().iloc[-2] if len(df) >= 21 else df['volume'].mean()
        available_levels = []

        if trend == 'bullish' and self.is_bullish_trend(df):
            # 优先使用89/144/233，377可选
            required_periods = [89, 144, 233]
            optional_periods = [377]
            
            for period in required_periods + optional_periods:
                ema_value = current_candle.get(f'ema{period}')
                if ema_value is None: continue
                
                # 价格回踩到EMA附近 (放宽条件：价格在EMA的10%范围内)
                price_distance = abs(current_price - ema_value) / ema_value
                if price_distance <= 0.10:  # 10%范围内
                    # 量能确认：当前成交量大于20周期均量
                    if current_candle['volume'] > avg_volume:
                        condition = f"EMA{period}反弹信号 (价格:{current_price:.4f} 接近EMA{period}:{ema_value:.4f})"
                        available_levels.append({
                            'ema_period': period,
                            'ema_value': float(ema_value),
                            'type': 'long',
                            'signal': 'long',
                            'entry_price': float(current_price),  # 使用当前价格作为入场价
                            'price_distance': float(price_distance),
                            'signal_time': current_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(current_time, 'strftime') else str(current_time),
                            'condition': condition,
                            'description': f"牛市趋势中，价格({current_price:.4f})回踩至EMA{period}({ema_value:.4f})附近，距离{price_distance:.2%}，形成反弹买入信号"
                        })
        
        elif trend == 'bearish' and self.is_bearish_trend(df):
            # 优先使用89/144/233，377可选
            required_periods = [89, 144, 233]
            optional_periods = [377]
            
            for period in required_periods + optional_periods:
                ema_value = current_candle.get(f'ema{period}')
                if ema_value is None: continue
                
                # 价格反弹到EMA附近 (放宽条件：价格在EMA的10%范围内)
                price_distance = abs(current_price - ema_value) / ema_value
                if price_distance <= 0.10:  # 10%范围内
                    if current_candle['volume'] > avg_volume:
                        condition = f"EMA{period}拒绝信号 (价格:{current_price:.4f} 接近EMA{period}:{ema_value:.4f})"
                        available_levels.append({
                            'ema_period': period,
                            'ema_value': float(ema_value),
                            'type': 'short',
                            'signal': 'short',
                            'entry_price': float(current_price),  # 使用当前价格作为入场价
                            'price_distance': float(price_distance),
                            'signal_time': current_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(current_time, 'strftime') else str(current_time),
                            'condition': condition,
                            'description': f"熊市趋势中，价格({current_price:.4f})反弹至EMA{period}({ema_value:.4f})附近，距离{price_distance:.2%}，形成拒绝卖出信号"
                        })
        
        return available_levels
    
    def find_ema_crossover_signals(self, df: pd.DataFrame) -> List[Dict]:
        """寻找EMA交叉信号"""
        signals = []
        
        if len(df) < 2:
            return signals
        
        current_candle = df.iloc[-1]  # 最新K线
        previous_candle = df.iloc[-2]  # 前一根K线
        current_time = self.get_beijing_time()  # 使用北京时间作为信号时间
        
        # EMA89与EMA233交叉
        if 'ema89' in current_candle and 'ema233' in current_candle:
            current_89 = current_candle['ema89']
            current_233 = current_candle['ema233']
            prev_89 = previous_candle.get('ema89')
            prev_233 = previous_candle.get('ema233')
            
            if prev_89 is not None and prev_233 is not None:
                # 金叉：EMA89上穿EMA233
                if prev_89 <= prev_233 and current_89 > current_233:
                    condition = f"EMA89金叉EMA233 (89:{current_89:.4f} > 233:{current_233:.4f})"
                    signals.append({
                        'type': 'golden_cross',
                        'signal': 'long',
                        'ema89': float(current_89),
                        'ema233': float(current_233),
                        'strength': 'strong' if current_89 > current_233 * 1.01 else 'weak',
                        'ema_period': 89,  # 基于EMA89和EMA233的交叉
                        'entry_price': float(current_candle['close']),  # 修复：使用当前价格而非EMA值
                        'signal_time': current_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(current_time, 'strftime') else str(current_time),
                        'condition': condition,
                        'description': f"EMA89({current_89:.4f})上穿EMA233({current_233:.4f})，形成金叉买入信号"
                    })
                
                # 死叉：EMA89下穿EMA233
                elif prev_89 >= prev_233 and current_89 < current_233:
                    condition = f"EMA89死叉EMA233 (89:{current_89:.4f} < 233:{current_233:.4f})"
                    signals.append({
                        'type': 'death_cross',
                        'signal': 'short',
                        'ema89': float(current_89),
                        'ema233': float(current_233),
                        'strength': 'strong' if current_89 < current_233 * 0.99 else 'weak',
                        'ema_period': 89,  # 基于EMA89和EMA233的交叉
                        'entry_price': float(current_candle['close']),  # 修复：使用当前价格而非EMA值
                        'signal_time': current_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(current_time, 'strftime') else str(current_time),
                        'condition': condition,
                        'description': f"EMA89({current_89:.4f})下穿EMA233({current_233:.4f})，形成死叉卖出信号"
                    })
        
        return signals
    
    def find_price_breakout_signals(self, df: pd.DataFrame) -> List[Dict]:
        """寻找价格突破信号"""
        signals = []
        
        if len(df) < 2:
            return signals
        
        current_candle = df.iloc[-1]  # 最新K线
        previous_candle = df.iloc[-2]  # 前一根K线
        current_price = current_candle['close']
        current_time = self.get_beijing_time()  # 使用北京时间作为信号时间
        
        # 检查价格突破EMA233
        if 'ema233' in current_candle:
            ema233 = current_candle['ema233']
            prev_high = previous_candle['high']
            prev_low = previous_candle['low']
            
            # 向上突破EMA233
            if prev_high <= ema233 and current_price > ema233:
                condition = f"价格向上突破EMA233 (价格:{current_price:.4f} > EMA233:{ema233:.4f})"
                signals.append({
                    'type': 'breakout',
                    'signal': 'long',
                    'breakout_level': float(ema233),
                    'current_price': float(current_price),
                    'strength': 'strong' if current_price > ema233 * 1.02 else 'weak',
                    'ema_period': 233,  # 基于EMA233的突破
                    'entry_price': float(current_price),
                    'signal_time': current_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(current_time, 'strftime') else str(current_time),
                    'condition': condition,
                    'description': f"价格({current_price:.4f})向上突破EMA233({ema233:.4f})，形成突破买入信号"
                })
            
            # 向下突破EMA233
            elif prev_low >= ema233 and current_price < ema233:
                condition = f"价格向下突破EMA233 (价格:{current_price:.4f} < EMA233:{ema233:.4f})"
                signals.append({
                    'type': 'breakdown',
                    'signal': 'short',
                    'breakdown_level': float(ema233),
                    'current_price': float(current_price),
                    'strength': 'strong' if current_price < ema233 * 0.98 else 'weak',
                    'ema_period': 233,  # 基于EMA233的突破
                    'entry_price': float(current_price),
                    'signal_time': current_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(current_time, 'strftime') else str(current_time),
                    'condition': condition,
                    'description': f"价格({current_price:.4f})向下突破EMA233({ema233:.4f})，形成突破卖出信号"
                })
        
        return signals
    
    def find_support_resistance_signals(self, df: pd.DataFrame) -> List[Dict]:
        """寻找支撑阻力位信号"""
        signals = []
        
        if len(df) < 20:
            return signals
        
        current_candle = df.iloc[-1]  # 最新K线
        current_price = current_candle['close']
        current_time = self.get_beijing_time()  # 使用北京时间作为信号时间
        
        # 寻找最近20根K线的支撑阻力位（使用tail获取最新20根）
        recent_data = df.tail(20)
        highs = recent_data['high'].values
        lows = recent_data['low'].values
        
        # 寻找阻力位（局部高点）
        for i in range(1, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                resistance = highs[i]
                distance = abs(current_price - resistance) / resistance
                if distance <= 0.03:  # 3%范围内
                    condition = f"价格接近阻力位 (价格:{current_price:.4f} 接近阻力:{resistance:.4f})"
                    signals.append({
                        'type': 'resistance',
                        'signal': 'short',
                        'level': float(resistance),
                        'current_price': float(current_price),
                        'distance': float(distance),
                        'ema_period': None,  # 支撑阻力信号不基于EMA
                        'entry_price': float(current_price),
                        'signal_time': current_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(current_time, 'strftime') else str(current_time),
                        'condition': condition,
                        'description': f"价格({current_price:.4f})接近阻力位({resistance:.4f})，距离{distance:.2%}，建议做空"
                    })
        
        # 寻找支撑位（局部低点）
        for i in range(1, len(lows) - 1):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                support = lows[i]
                distance = abs(current_price - support) / support
                if distance <= 0.03:  # 3%范围内
                    condition = f"价格接近支撑位 (价格:{current_price:.4f} 接近支撑:{support:.4f})"
                    signals.append({
                        'type': 'support',
                        'signal': 'long',
                        'level': float(support),
                        'current_price': float(current_price),
                        'distance': float(distance),
                        'ema_period': None,  # 支撑阻力信号不基于EMA
                        'entry_price': float(current_price),
                        'signal_time': current_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(current_time, 'strftime') else str(current_time),
                        'condition': condition,
                        'description': f"价格({current_price:.4f})接近支撑位({support:.4f})，距离{distance:.2%}，建议做多"
                    })
        
        return signals
    
    def analyze_symbol(self, symbol: str) -> Dict:
        """分析单个币种的所有时间框架"""
        logger.info(f"开始分析币种: {symbol}")
        results = []
        
        for timeframe in self.timeframes:
            try:
                # 获取K线数据
                # 由于EMA计算需要历史数据，需要获取比最大EMA周期更多的K线
                required_data_points = 233 + 50  # 只需要233+50=283个数据点，377可选 
                df = self.get_klines_data(symbol, timeframe, required_data_points)
                if df.empty or len(df) < 233:  # 只需要233个数据点
                    results.append({
                        'timeframe': timeframe, 'status': 'error',
                        'message': f'数据不足: 仅获取到 {len(df)} 条'
                    })
                    continue
                
                # 计算技术指标
                df = self.calculate_emas(df)
                df = self.calculate_bollinger_bands(df)
                df.dropna(inplace=True) # 删除计算指标后产生的NaN行
                
                if df.empty:
                    results.append({'timeframe': timeframe, 'status': 'error', 'message': '计算指标后数据为空'})
                    continue

                # 判断趋势 (使用最新的有效数据)
                latest_data = df.iloc[-1]  # 最新数据在最后
                if self.is_bullish_trend(df):
                    trend = 'bullish'
                    trend_strength = 'strong' if latest_data['ema89'] > latest_data['ema144'] * 1.01 else 'weak'
                elif self.is_bearish_trend(df):
                    trend = 'bearish'
                    trend_strength = 'strong' if latest_data['ema89'] < latest_data['ema144'] * 0.99 else 'weak'
                else:
                    trend = 'neutral'
                    trend_strength = 'weak'
                
                # 寻找各种信号
                pullback_levels = self.find_ema_pullback_levels(df, trend)
                crossover_signals = self.find_ema_crossover_signals(df)
                breakout_signals = self.find_price_breakout_signals(df)
                support_resistance_signals = self.find_support_resistance_signals(df)
                
                # 合并所有信号
                all_signals = []
                all_signals.extend(pullback_levels)
                all_signals.extend(crossover_signals)
                all_signals.extend(breakout_signals)
                all_signals.extend(support_resistance_signals)
                
                # 去重信号 - 基于更严格的标识符
                unique_signals = []
                seen_signals = set()
                
                for signal in all_signals:
                    # 创建更严格的唯一标识符
                    ema_period = signal.get('ema_period')
                    if ema_period is None:
                        ema_period = 'None'
                    
                    # 处理None值，确保去重键的一致性
                    level = signal.get('level')
                    if level is None:
                        level = 0
                    
                    distance = signal.get('distance')
                    if distance is None:
                        distance = 0
                    
                    signal_key = (
                        signal.get('signal', ''),  # 信号类型
                        round(signal.get('entry_price', 0), 6),  # 入场价格
                        str(ema_period),  # EMA周期
                        round(level, 6),  # 水平位
                        signal.get('type', ''),  # 信号子类型
                        round(distance, 8)  # 距离
                    )
                    
                    if signal_key not in seen_signals:
                        seen_signals.add(signal_key)
                        unique_signals.append(signal)
                    else:
                        logger.debug(f"策略层去重信号: {signal_key}")
                
                logger.info(f"策略层去重: {len(all_signals)} -> {len(unique_signals)} 个信号")
                all_signals = unique_signals
                
                # 计算止盈目标 - 根据趋势和信号类型智能设置
                take_profit_timeframe = self.take_profit_timeframes.get(timeframe, '15m')
                tp_df = self.get_klines_data(symbol, take_profit_timeframe, 200)
                take_profit_price = None
                if tp_df is not None and not tp_df.empty:
                    tp_df = self.calculate_bollinger_bands(tp_df)
                    tp_df.dropna(inplace=True)
                    if not tp_df.empty:
                        bb_middle = tp_df['bb_middle'].iloc[-1]  # 最新布林带数据
                        bb_lower = tp_df['bb_lower'].iloc[-1]
                        bb_upper = tp_df['bb_upper'].iloc[-1]
                        
                        # 根据趋势和信号类型设置止盈
                        current_price = tp_df['close'].iloc[-1]  # 最新价格
                        
                        if trend == 'bullish':
                            # 多头趋势：使用布林带中轨作为止盈
                            take_profit_price = bb_middle
                        elif trend == 'bearish':
                            # 空头趋势：使用布林带下轨作为止盈
                            take_profit_price = bb_lower
                        else:
                            # 中性趋势：根据当前价格位置智能设置
                            if current_price > bb_middle:
                                # 价格在中轨上方，倾向于做空，使用下轨止盈
                                take_profit_price = bb_lower
                            else:
                                # 价格在中轨下方，倾向于做多，使用中轨止盈
                                take_profit_price = bb_middle
                        
                        # 确保止盈价格的合理性
                        # 对于做空信号，止盈价格应该低于入场价格
                        # 对于做多信号，止盈价格应该高于入场价格
                        entry_price = latest_data['close']
                        
                        # 获取主要信号类型
                        main_signal_type = 'long'  # 默认
                        if all_signals:
                            # 统计信号类型
                            short_count = sum(1 for s in all_signals if s.get('signal') == 'short')
                            long_count = sum(1 for s in all_signals if s.get('signal') == 'long')
                            if short_count > long_count:
                                main_signal_type = 'short'
                        
                        # 根据主要信号类型调整止盈价格
                        if main_signal_type == 'short':
                            # 做空信号：确保止盈价格低于入场价格
                            if take_profit_price >= entry_price:
                                # 如果止盈价格高于入场价格，设置为入场价格的95%
                                take_profit_price = entry_price * 0.95
                        else:
                            # 做多信号：确保止盈价格高于入场价格
                            if take_profit_price <= entry_price:
                                # 如果止盈价格低于入场价格，设置为入场价格的105%
                                take_profit_price = entry_price * 1.05

                results.append({
                    'timeframe': timeframe, 'status': 'success',
                    'trend': trend, 'trend_strength': trend_strength,
                    'current_price': latest_data['close'],
                    'ema89': latest_data.get('ema89'), 'ema144': latest_data.get('ema144'), 
                    'ema233': latest_data.get('ema233'), 'ema377': latest_data.get('ema377'),
                    'pullback_levels': pullback_levels,
                    'crossover_signals': crossover_signals,
                    'breakout_signals': breakout_signals,
                    'support_resistance_signals': support_resistance_signals,
                    'all_signals': all_signals,
                    'take_profit_timeframe': take_profit_timeframe,
                    'take_profit_price': take_profit_price,
                    'signal_count': len(all_signals)
                })
                
            except Exception as e:
                logger.error(f"分析 {symbol} {timeframe} 失败: {e}", exc_info=True)
                results.append({'timeframe': timeframe, 'status': 'error', 'message': str(e)})
        
        return {
            'symbol': symbol,
            'results': results,
            'total_timeframes': len(self.timeframes),
            'successful_timeframes': sum(1 for r in results if r['status'] == 'success')
        }
    
    def analyze_multiple_symbols(self, symbols: List[str], page: int = 1, page_size: int = 20) -> Dict:
        """分析多个币种 - 【修复】现在分析所有币种，分页在API层处理"""
        try:
            # 【修复分页逻辑】不再在策略层分页，而是处理所有传入的币种
            # API层会负责信号级别的分页
            if page_size >= len(symbols):
                # 如果页面大小大于或等于总币种数，处理所有币种
                page_symbols = symbols
                logger.info(f"分析所有币种: {len(page_symbols)}个")
            else:
                # 保持原有的分页逻辑用于向后兼容
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                page_symbols = symbols[start_idx:end_idx]
                logger.info(f"开始分析第{page}页币种: {len(page_symbols)}个 (总计{len(symbols)}个)")
            
            all_results = {}
            
            # 检查是否在生产环境中禁用多线程
            import os
            is_production = os.getenv('FLASK_ENV') == 'production'
            
            if is_production:
                # 生产环境使用单线程处理，避免并发问题
                logger.info("生产环境检测到，使用单线程处理")
                for i, symbol in enumerate(page_symbols):
                    try:
                        result = self._analyze_symbol_with_delay(symbol, i)
                        all_results[symbol] = result['results']
                        
                        # 每完成10个币种输出一次进度
                        if (i + 1) % 10 == 0:
                            logger.info(f"已完成 {i + 1}/{len(page_symbols)} 个币种分析")
                            
                    except Exception as e:
                        logger.error(f"分析币种 {symbol} 时发生异常: {e}", exc_info=True)
                        all_results[symbol] = [{'timeframe': 'all', 'status': 'error', 'message': str(e)}]
            else:
                # 开发环境使用线程池进行并发分析
                try:
                    with ThreadPoolExecutor(max_workers=min(self.max_workers, 4)) as executor:
                        # 提交任务
                        future_to_symbol = {}
                        for i, symbol in enumerate(page_symbols):
                            future = executor.submit(self._analyze_symbol_with_delay, symbol, i)
                            future_to_symbol[future] = symbol
                        
                        # 收集结果
                        completed_count = 0
                        for future in as_completed(future_to_symbol):
                            symbol = future_to_symbol[future]
                            try:
                                result = future.result()
                                all_results[symbol] = result['results']
                                completed_count += 1
                                
                                # 每完成10个币种输出一次进度
                                if completed_count % 10 == 0:
                                    logger.info(f"已完成 {completed_count}/{len(page_symbols)} 个币种分析")
                                    
                            except Exception as e:
                                logger.error(f"分析币种 {symbol} 时发生异常: {e}", exc_info=True)
                                all_results[symbol] = [{'timeframe': 'all', 'status': 'error', 'message': str(e)}]
                except Exception as e:
                    logger.error(f"线程池执行失败，回退到单线程处理: {e}")
                    # 回退到单线程处理
                    for i, symbol in enumerate(page_symbols):
                        try:
                            result = self._analyze_symbol_with_delay(symbol, i)
                            all_results[symbol] = result['results']
                        except Exception as e:
                            logger.error(f"分析币种 {symbol} 时发生异常: {e}", exc_info=True)
                            all_results[symbol] = [{'timeframe': 'all', 'status': 'error', 'message': str(e)}]
            
            logger.info(f"第{page}页分析完成: {len(all_results)}个币种")
            return all_results
            
        except Exception as e:
            logger.error(f"分析多个币种时发生异常: {e}", exc_info=True)
            return {}
    
    def _analyze_symbol_with_delay(self, symbol: str, index: int) -> Dict:
        """带延迟的币种分析"""
        try:
            # 添加延迟避免API频率限制
            if index > 0:
                time.sleep(self.request_delay)
            
            return self.analyze_symbol(symbol)
        except Exception as e:
            logger.error(f"分析币种 {symbol} 失败: {e}")
            return {
                'symbol': symbol,
                'results': [{'timeframe': 'all', 'status': 'error', 'message': str(e)}]
            }
    
    def analyze_all_timeframes(self, symbol: str) -> List[Dict]:
        """分析单个币种的所有时间框架（API兼容方法）"""
        result = self.analyze_symbol(symbol)
        return result['results']
    
    def validate_symbol(self, symbol: str) -> bool:
        """验证币种是否存在"""
        try:
            df = self.get_klines_data(symbol, '1d', 10)
            return df is not None and not df.empty
        except Exception as e:
            logger.error(f"验证币种 {symbol} 失败: {e}")
            return False

