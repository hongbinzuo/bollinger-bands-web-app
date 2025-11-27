# -*- coding: utf-8 -*-
"""
加密货币分析工具
从多个数据源获取币种信息并进行分析
"""

import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 设置UTF-8输出
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def get_binance_price(symbol):
    """从Binance获取价格数据"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'symbol': symbol,
                'price': float(data['lastPrice']),
                'change_24h': float(data['priceChangePercent']),
                'volume': float(data['volume']),
                'high_24h': float(data['highPrice']),
                'low_24h': float(data['lowPrice']),
                'source': 'Binance'
            }
    except:
        pass
    return None

def get_coingecko_info(symbol):
    """从CoinGecko获取基本信息"""
    try:
        # 搜索币种
        search_url = "https://api.coingecko.com/api/v3/search"
        params = {'query': symbol}
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            coins = data.get('coins', [])
            
            if coins:
                coin_id = coins[0]['id']
                
                # 获取详细信息
                detail_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                detail_response = requests.get(detail_url, timeout=15)
                
                if detail_response.status_code == 200:
                    coin_data = detail_response.json()
                    market_data = coin_data.get('market_data', {})
                    
                    return {
                        'name': coin_data.get('name', symbol),
                        'rank': coin_data.get('market_cap_rank', 999),
                        'market_cap': market_data.get('market_cap', {}).get('usd', 0),
                        'categories': ', '.join(coin_data.get('categories', [])[:3]),
                        'description': coin_data.get('description', {}).get('en', '')[:200],
                        'twitter_followers': coin_data.get('community_data', {}).get('twitter_followers', 0),
                        'github_stars': coin_data.get('developer_data', {}).get('stars', 0),
                        'source': 'CoinGecko'
                    }
    except:
        pass
    return None

def analyze_coins(symbols):
    """分析币种列表"""
    print("="*70, flush=True)
    print("加密货币分析工具", flush=True)
    print("="*70, flush=True)
    print(f"分析币种数量: {len(symbols)}", flush=True)
    print("数据源: Binance + CoinGecko", flush=True)
    print("="*70, flush=True)
    
    results = []
    success_count = 0
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] 分析 {symbol}...", flush=True)
        
        # 获取价格数据
        price_data = get_binance_price(symbol)
        time.sleep(0.5)
        
        # 获取基本信息
        info_data = get_coingecko_info(symbol)
        time.sleep(1)
        
        # 合并数据
        coin_data = {
            'symbol': symbol,
            'price': 0,
            'change_24h': 0,
            'volume': 0,
            'rank': 999,
            'market_cap': 0,
            'categories': 'Unknown',
            'twitter_followers': 0,
            'github_stars': 0,
            'data_source': 'Failed'
        }
        
        if price_data:
            coin_data.update(price_data)
            success_count += 1
            print(f"  ✓ 价格: ${coin_data['price']:.6f} ({coin_data['change_24h']:+.2f}%)", flush=True)
        
        if info_data:
            coin_data.update(info_data)
            print(f"  ✓ 排名: {coin_data['rank']}, 分类: {coin_data['categories']}", flush=True)
        
        results.append(coin_data)
        
        # 每10个显示进度
        if i % 10 == 0:
            print(f"  进度: {i}/{len(symbols)}, 成功: {success_count}", flush=True)
    
    return pd.DataFrame(results)

def generate_analysis_report(df):
    """生成分析报告"""
    
    # 基本统计
    total_coins = len(df)
    successful_coins = len(df[df['data_source'] != 'Failed'])
    
    # 价格表现分析
    df_with_price = df[df['price'] > 0]
    
    report = f"""# 加密货币分析报告

**生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}  
**分析币种数**: {total_coins}  
**成功获取数据**: {successful_coins} ({successful_coins/total_coins*100:.1f}%)

---

## 📊 数据概览

### 基本信息统计
- **总币种数**: {total_coins}
- **成功获取数据**: {successful_coins}
- **数据成功率**: {successful_coins/total_coins*100:.1f}%

"""

    if len(df_with_price) > 0:
        # 涨跌分析
        positive = len(df_with_price[df_with_price['change_24h'] > 0])
        negative = len(df_with_price[df_with_price['change_24h'] < 0])
        
        report += f"""
## 📈 价格表现分析

### 24小时涨跌分布
- **上涨币种**: {positive} 个 ({positive/len(df_with_price)*100:.1f}%)
- **下跌币种**: {negative} 个 ({negative/len(df_with_price)*100:.1f}%)

### 统计指标
- **平均涨跌**: {df_with_price['change_24h'].mean():+.2f}%
- **最大涨幅**: {df_with_price['change_24h'].max():+.2f}%
- **最大跌幅**: {df_with_price['change_24h'].min():+.2f}%

"""

        # TOP 涨幅榜
        report += "### 🚀 TOP 10 涨幅榜\n\n"
        report += "| 排名 | 币种 | 24h涨跌 | 当前价格 | 市值排名 |\n"
        report += "|------|------|---------|----------|----------|\n"
        
        top_gainers = df_with_price.nlargest(10, 'change_24h')
        for i, (_, row) in enumerate(top_gainers.iterrows(), 1):
            report += f"| {i} | **{row['symbol']}** | {row['change_24h']:+7.2f}% | ${row['price']:10.6f} | {row['rank']} |\n"
        
        report += "\n"
        
        # 分类分析
        categories = {}
        for _, row in df_with_price.iterrows():
            if row['categories'] != 'Unknown':
                for cat in row['categories'].split(','):
                    cat = cat.strip()
                    if cat not in categories:
                        categories[cat] = {'count': 0, 'avg_change': 0, 'changes': []}
                    categories[cat]['count'] += 1
                    categories[cat]['changes'].append(row['change_24h'])
        
        # 计算平均涨跌
        for cat in categories:
            categories[cat]['avg_change'] = np.mean(categories[cat]['changes'])
        
        report += "### 🏷️ 赛道表现分析\n\n"
        report += "| 赛道 | 币种数 | 平均涨跌 | 最佳表现 |\n"
        report += "|------|--------|----------|----------|\n"
        
        sorted_cats = sorted(categories.items(), key=lambda x: x[1]['avg_change'], reverse=True)
        for cat, data in sorted_cats[:10]:
            best_change = max(data['changes'])
            report += f"| {cat} | {data['count']} | {data['avg_change']:+.2f}% | {best_change:+.2f}% |\n"
        
        report += "\n"
    
    # 投资建议
    report += """## 💡 投资建议

### 关注标的
基于24小时表现和基本面数据，建议关注：

"""
    
    if len(df_with_price) > 0:
        # 筛选优质标的
        good_coins = df_with_price[
            (df_with_price['change_24h'] > 5) & 
            (df_with_price['rank'] <= 500) &
            (df_with_price['twitter_followers'] > 1000)
        ].nlargest(5, 'change_24h')
        
        for i, (_, row) in enumerate(good_coins.iterrows(), 1):
            report += f"{i}. **{row['symbol']}** (+{row['change_24h']:.2f}%)\n"
            report += f"   - 市值排名: {row['rank']}\n"
            report += f"   - 价格: ${row['price']:.6f}\n"
            report += f"   - 分类: {row['categories']}\n\n"
    
    report += """### 风险提示
- 加密货币投资风险极高
- 24小时数据不代表长期趋势
- 请根据自身风险承受能力决策
- 建议分散投资，控制仓位

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    return report

def get_sample_symbols():
    """获取示例币种列表"""
    return [
        # 第一组
        'AIOT', 'AVNT', 'ZEC', 'Q', 'PUMPBTC', 'IKA', 'HIFI', 'ALPINE', 'TA', 'LA',
        'DOOD', 'VELVET', 'FF', 'WLFI', 'F', 'FLOCK', 'SOON', 'MERL', 'ORDER', 'PTB',
        'ASTER', 'UB', 'OPEN', 'TOMI', 'IDOL', 'PROMPT', 'SAPIEN', 'PUMP', 'HEMI', 'TUT',
        'H', 'NMR', 'LAUNCHCOIN', 'CRO', 'BAKE',
        
        # 第二组  
        'BROCCOLI', 'AIO', 'SOMI', 'STO', 'IP', 'BANK', 'BIO', 'RED', 'AWE', 'DUCK',
        'BID', 'VFY', 'EPT', 'WLD', 'SQD', 'RWA', 'BB', 'BR', 'PYTH', 'SNX',
        'LISTA', 'OKB', 'ROAM', 'SQT', 'SATS', 'HIPPO', 'DOLO', 'ZENT', 'AIN', 'W', 'FTM'
    ]

def main():
    """主函数"""
    symbols = get_sample_symbols()
    
    # 分析币种
    df = analyze_coins(symbols)
    
    # 保存数据
    output_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(output_dir, "加密货币分析数据.csv")
    report_path = os.path.join(output_dir, "加密货币分析报告.md")
    
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ 已保存: {csv_path}", flush=True)
    
    # 生成报告
    report = generate_analysis_report(df)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✓ 已保存: {report_path}", flush=True)
    
    print("\n" + "="*70, flush=True)
    print("✅ 分析完成！", flush=True)
    print("="*70, flush=True)
    print("生成文件:", flush=True)
    print(f"  1. {csv_path}", flush=True)
    print(f"  2. {report_path}", flush=True)
    print("="*70, flush=True)
    
    return df

if __name__ == "__main__":
    main()





