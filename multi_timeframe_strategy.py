import pandas as pd
import numpy as np
import requests
import logging
import time
from datetime import datetime, timedelta
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
            
            # --- 重要：反转数据，使其从新到旧 ---
            df = df.iloc[::-1].copy()
            
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
                return df.iloc[::-1].copy() # 币安数据也是从旧到新，需要反转
                
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
                return df.iloc[::-1].copy() # 币安数据也是从旧到新，需要反转
                
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
        return df['ema89'].iloc[0] > df['ema144'].iloc[0] > df['ema233'].iloc[0]
    
    def is_bearish_trend(self, df: pd.DataFrame) -> bool:
        """判断是否为空头趋势（EMA89 < EMA144 < EMA233，377可选）"""
        required_emas = ['ema89', 'ema144', 'ema233']
        if not all(ema in df.columns for ema in required_emas) or len(df) < 1:
            return False
        return df['ema89'].iloc[0] < df['ema144'].iloc[0] < df['ema233'].iloc[0]
    
    def find_ema_pullback_levels(self, df: pd.DataFrame, trend: str) -> List[Dict]:
        """改进：加入趋势确认和量能过滤的回踩信号"""
        # 因为数据已反转，最新数据在第一行 (iloc[0])
        if len(df) < 20: # 确保有足够数据计算滚动均值
            return []
        
        current_candle = df.iloc[0]
        current_price = current_candle['close']
        avg_volume = df['volume'].rolling(window=20).mean().iloc[1] # 使用前一根K线的滚动量
        available_levels = []

        if trend == 'bullish' and self.is_bullish_trend(df):
            # 优先使用89/144/233，377可选
            required_periods = [89, 144, 233]
            optional_periods = [377]
            
            for period in required_periods + optional_periods:
                ema_value = current_candle.get(f'ema{period}')
                if ema_value is None: continue
                
                # 价格回踩到EMA附近 (放宽条件：价格在EMA的5%范围内)
                price_distance = abs(current_price - ema_value) / ema_value
                if price_distance <= 0.05:  # 5%范围内
                    # 量能确认：当前成交量大于20周期均量
                    if current_candle['volume'] > avg_volume:
                        available_levels.append({
                            'ema_period': period,
                            'ema_value': ema_value,
                            'type': 'long',
                            'entry_price': current_price,  # 使用当前价格作为入场价
                            'price_distance': price_distance
                        })
        
        elif trend == 'bearish' and self.is_bearish_trend(df):
            # 优先使用89/144/233，377可选
            required_periods = [89, 144, 233]
            optional_periods = [377]
            
            for period in required_periods + optional_periods:
                ema_value = current_candle.get(f'ema{period}')
                if ema_value is None: continue
                
                # 价格反弹到EMA附近 (放宽条件：价格在EMA的5%范围内)
                price_distance = abs(current_price - ema_value) / ema_value
                if price_distance <= 0.05:  # 5%范围内
                    if current_candle['volume'] > avg_volume:
                        available_levels.append({
                            'ema_period': period,
                            'ema_value': ema_value,
                            'type': 'short',
                            'entry_price': current_price,  # 使用当前价格作为入场价
                            'price_distance': price_distance
                        })
        
        return available_levels
    
    def find_ema_crossover_signals(self, df: pd.DataFrame) -> List[Dict]:
        """寻找EMA交叉信号"""
        signals = []
        
        if len(df) < 2:
            return signals
        
        current_candle = df.iloc[0]
        previous_candle = df.iloc[1]
        
        # EMA89与EMA233交叉
        if 'ema89' in current_candle and 'ema233' in current_candle:
            current_89 = current_candle['ema89']
            current_233 = current_candle['ema233']
            prev_89 = previous_candle.get('ema89')
            prev_233 = previous_candle.get('ema233')
            
            if prev_89 is not None and prev_233 is not None:
                # 金叉：EMA89上穿EMA233
                if prev_89 <= prev_233 and current_89 > current_233:
                    signals.append({
                        'type': 'golden_cross',
                        'signal': 'long',
                        'ema89': current_89,
                        'ema233': current_233,
                        'strength': 'strong' if current_89 > current_233 * 1.01 else 'weak'
                    })
                
                # 死叉：EMA89下穿EMA233
                elif prev_89 >= prev_233 and current_89 < current_233:
                    signals.append({
                        'type': 'death_cross',
                        'signal': 'short',
                        'ema89': current_89,
                        'ema233': current_233,
                        'strength': 'strong' if current_89 < current_233 * 0.99 else 'weak'
                    })
        
        return signals
    
    def find_price_breakout_signals(self, df: pd.DataFrame) -> List[Dict]:
        """寻找价格突破信号"""
        signals = []
        
        if len(df) < 2:
            return signals
        
        current_candle = df.iloc[0]
        previous_candle = df.iloc[1]
        current_price = current_candle['close']
        
        # 检查价格突破EMA233
        if 'ema233' in current_candle:
            ema233 = current_candle['ema233']
            prev_high = previous_candle['high']
            prev_low = previous_candle['low']
            
            # 向上突破EMA233
            if prev_high <= ema233 and current_price > ema233:
                signals.append({
                    'type': 'breakout',
                    'signal': 'long',
                    'breakout_level': ema233,
                    'current_price': current_price,
                    'strength': 'strong' if current_price > ema233 * 1.02 else 'weak'
                })
            
            # 向下突破EMA233
            elif prev_low >= ema233 and current_price < ema233:
                signals.append({
                    'type': 'breakdown',
                    'signal': 'short',
                    'breakdown_level': ema233,
                    'current_price': current_price,
                    'strength': 'strong' if current_price < ema233 * 0.98 else 'weak'
                })
        
        return signals
    
    def find_support_resistance_signals(self, df: pd.DataFrame) -> List[Dict]:
        """寻找支撑阻力位信号"""
        signals = []
        
        if len(df) < 20:
            return signals
        
        current_candle = df.iloc[0]
        current_price = current_candle['close']
        
        # 寻找最近20根K线的支撑阻力位
        recent_data = df.head(20)
        highs = recent_data['high'].values
        lows = recent_data['low'].values
        
        # 寻找阻力位（局部高点）
        for i in range(1, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                resistance = highs[i]
                distance = abs(current_price - resistance) / resistance
                if distance <= 0.03:  # 3%范围内
                    signals.append({
                        'type': 'resistance',
                        'signal': 'short',
                        'level': resistance,
                        'current_price': current_price,
                        'distance': distance
                    })
        
        # 寻找支撑位（局部低点）
        for i in range(1, len(lows) - 1):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                support = lows[i]
                distance = abs(current_price - support) / support
                if distance <= 0.03:  # 3%范围内
                    signals.append({
                        'type': 'support',
                        'signal': 'long',
                        'level': support,
                        'current_price': current_price,
                        'distance': distance
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
                latest_data = df.iloc[0]
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
                
                # 计算止盈目标
                take_profit_timeframe = self.take_profit_timeframes.get(timeframe, '15m')
                tp_df = self.get_klines_data(symbol, take_profit_timeframe, 200)
                take_profit_price = None
                if tp_df is not None and not tp_df.empty:
                    tp_df = self.calculate_bollinger_bands(tp_df)
                    tp_df.dropna(inplace=True)
                    if not tp_df.empty:
                        take_profit_price = tp_df['bb_middle'].iloc[0]

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
    
    def analyze_multiple_symbols(self, symbols: List[str]) -> Dict:
        """分析多个币种 - 添加请求间隔控制"""
        all_results = {}
        
        for i, symbol in enumerate(symbols):
            try:
                logger.info(f"--- 开始分析币种: {symbol} ({i+1}/{len(symbols)}) ---")
                
                # 添加请求间隔，避免API频率限制 (第一个币种前不延迟)
                if i > 0:
                    time.sleep(0.5)
                
                result = self.analyze_symbol(symbol)
                all_results[symbol] = result['results']
                
                # 每10个币种后增加额外延迟
                if (i + 1) % 10 == 0 and i + 1 < len(symbols):
                    logger.info(f"已处理10个币种，休息2秒...")
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"分析币种 {symbol} 时发生顶层异常: {e}", exc_info=True)
                all_results[symbol] = [{'timeframe': 'all', 'status': 'error', 'message': str(e)}]
        
        return all_results
    
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

