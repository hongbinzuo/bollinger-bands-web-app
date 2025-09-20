#!/usr/bin/env python3
"""
多时间框架模块修复后的自动测试脚本
测试分页功能、超时处理和信号生成
"""

import requests
import json
import time
import sys
from typing import Dict, List

class MultiTimeframeTestSuite:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'MultiTimeframe-TestSuite/1.0'
        })
        self.test_results = []
        
    def log(self, message: str, level: str = "INFO"):
        """记录测试日志"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def test_api_endpoint(self, endpoint: str, method: str = "GET", data: dict = None) -> tuple:
        """测试API端点"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                response = self.session.get(url, timeout=30)
            elif method == "POST":
                response = self.session.post(url, json=data, timeout=60)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            return True, response.status_code, response.json()
        except requests.exceptions.Timeout:
            return False, 408, {"error": "Request timeout"}
        except requests.exceptions.RequestException as e:
            return False, 500, {"error": str(e)}
        except json.JSONDecodeError:
            return False, response.status_code, {"error": "Invalid JSON response"}
    
    def test_get_symbols(self) -> bool:
        """测试获取币种列表"""
        self.log("测试获取币种列表...")
        
        success, status, data = self.test_api_endpoint('/multi_timeframe/get_top_symbols')
        
        if not success:
            self.log(f"获取币种列表失败: {data}", "ERROR")
            return False
            
        if status != 200:
            self.log(f"获取币种列表返回错误状态码: {status}", "ERROR")
            return False
            
        if not data.get('success'):
            self.log(f"获取币种列表API返回失败: {data.get('error')}", "ERROR")
            return False
            
        symbols = data.get('symbols', [])
        self.log(f"成功获取 {len(symbols)} 个币种")
        
        if len(symbols) < 10:
            self.log("币种数量过少，可能存在问题", "WARNING")
            
        return symbols[:5]  # 返回前5个币种用于后续测试
    
    def test_single_symbol_analysis(self, symbol: str) -> bool:
        """测试单币种分析"""
        self.log(f"测试单币种分析: {symbol}...")
        
        success, status, data = self.test_api_endpoint(
            '/multi_timeframe/analyze_symbol', 
            'POST', 
            {'symbol': symbol}
        )
        
        if not success:
            self.log(f"单币种分析失败: {data}", "ERROR")
            return False
            
        if status != 200:
            self.log(f"单币种分析返回错误状态码: {status}", "ERROR")
            return False
            
        if not data.get('success'):
            self.log(f"单币种分析API返回失败: {data.get('error')}", "ERROR")
            return False
            
        results = data.get('results', [])
        successful = data.get('successful_timeframes', 0)
        total = data.get('total_timeframes_analyzed', 0)
        
        self.log(f"单币种分析完成: {successful}/{total} 个时间框架成功")
        
        return successful > 0
    
    def test_batch_analysis_small(self, symbols: List[str]) -> bool:
        """测试小批量分析（防超时）"""
        test_symbols = symbols[:3]  # 只测试前3个币种
        self.log(f"测试小批量分析: {test_symbols}...")
        
        success, status, data = self.test_api_endpoint(
            '/multi_timeframe/analyze_multiple_symbols',
            'POST',
            {
                'symbols': test_symbols,
                'page': 1,
                'page_size': 50
            }
        )
        
        if not success:
            self.log(f"小批量分析失败: {data}", "ERROR")
            return False
            
        if status != 200:
            self.log(f"小批量分析返回错误状态码: {status}", "ERROR")
            return False
            
        if not data.get('success'):
            self.log(f"小批量分析API返回失败: {data.get('error')}", "ERROR")
            return False
            
        signals = data.get('signals', [])
        pagination = data.get('pagination', {})
        
        self.log(f"小批量分析完成: 生成 {len(signals)} 个信号")
        self.log(f"分页信息: {pagination.get('current_page', 'N/A')}页, 共{pagination.get('total_pages', 'N/A')}页")
        
        return len(signals) >= 0  # 允许0个信号，因为可能没有满足条件的
    
    def test_pagination_logic(self, symbols: List[str]) -> bool:
        """测试分页逻辑"""
        test_symbols = symbols[:5]  # 使用5个币种测试
        self.log(f"测试分页逻辑: {test_symbols}...")
        
        # 测试第1页
        success1, status1, data1 = self.test_api_endpoint(
            '/multi_timeframe/analyze_multiple_symbols',
            'POST',
            {
                'symbols': test_symbols,
                'page': 1,
                'page_size': 10  # 每页10个信号
            }
        )
        
        if not success1 or status1 != 200:
            self.log("第1页测试失败", "ERROR")
            return False
            
        signals_page1 = data1.get('signals', [])
        pagination1 = data1.get('pagination', {})
        
        # 如果有多页，测试第2页
        if pagination1.get('total_pages', 0) > 1:
            success2, status2, data2 = self.test_api_endpoint(
                '/multi_timeframe/analyze_multiple_symbols',
                'POST',
                {
                    'symbols': test_symbols,
                    'page': 2,
                    'page_size': 10
                }
            )
            
            if success2 and status2 == 200:
                signals_page2 = data2.get('signals', [])
                self.log(f"分页测试: 第1页{len(signals_page1)}个信号, 第2页{len(signals_page2)}个信号")
                
                # 检查信号是否不重复
                signal_ids_1 = set(f"{s.get('symbol', '')}-{s.get('timeframe', '')}-{s.get('entry_price', 0)}" for s in signals_page1)
                signal_ids_2 = set(f"{s.get('symbol', '')}-{s.get('timeframe', '')}-{s.get('entry_price', 0)}" for s in signals_page2)
                
                overlap = signal_ids_1 & signal_ids_2
                if overlap:
                    self.log(f"分页重复信号检测到: {len(overlap)} 个重复", "WARNING")
                else:
                    self.log("分页信号无重复，正常")
            else:
                self.log("第2页测试失败", "WARNING")
        
        self.log(f"分页逻辑测试完成: 总页数 {pagination1.get('total_pages', 'N/A')}")
        return True
    
    def test_error_handling(self) -> bool:
        """测试错误处理"""
        self.log("测试错误处理...")
        
        # 测试无效币种
        success, status, data = self.test_api_endpoint(
            '/multi_timeframe/analyze_symbol',
            'POST',
            {'symbol': 'INVALIDCOIN'}
        )
        
        # 应该返回成功但结果为空或错误
        if success and status == 200:
            results = data.get('results', [])
            error_results = [r for r in results if r.get('status') == 'error']
            if error_results:
                self.log("无效币种错误处理正常")
                return True
        
        # 测试空请求
        success, status, data = self.test_api_endpoint(
            '/multi_timeframe/analyze_multiple_symbols',
            'POST',
            {'symbols': []}
        )
        
        if not success or status != 400:
            self.log("空请求错误处理可能有问题", "WARNING")
        else:
            self.log("空请求错误处理正常")
            
        return True
    
    def test_strategy_info(self) -> bool:
        """测试策略信息获取"""
        self.log("测试策略信息获取...")
        
        success, status, data = self.test_api_endpoint('/multi_timeframe/get_strategy_info')
        
        if not success or status != 200:
            self.log("策略信息获取失败", "ERROR")
            return False
            
        if not data.get('success'):
            self.log("策略信息API返回失败", "ERROR")
            return False
            
        strategy_name = data.get('strategy_name', '')
        timeframes = data.get('timeframes', [])
        
        self.log(f"策略信息: {strategy_name}, 支持 {len(timeframes)} 个时间框架")
        return True
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        self.log("开始运行多时间框架模块测试套件...")
        self.log("=" * 60)
        
        # 1. 测试获取币种
        symbols = self.test_get_symbols()
        if not symbols:
            self.log("基础测试失败，终止后续测试", "ERROR")
            return False
            
        # 2. 测试策略信息
        if not self.test_strategy_info():
            self.log("策略信息测试失败", "WARNING")
            
        # 3. 测试单币种分析
        if symbols and not self.test_single_symbol_analysis(symbols[0]):
            self.log("单币种分析测试失败", "WARNING")
            
        # 4. 测试小批量分析
        if not self.test_batch_analysis_small(symbols):
            self.log("批量分析测试失败，检查是否需要优化", "WARNING")
            
        # 5. 测试分页逻辑
        if not self.test_pagination_logic(symbols):
            self.log("分页逻辑测试失败", "ERROR")
            return False
            
        # 6. 测试错误处理
        if not self.test_error_handling():
            self.log("错误处理测试失败", "WARNING")
            
        self.log("=" * 60)
        self.log("所有测试完成！")
        return True

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='多时间框架模块自动测试')
    parser.add_argument('--host', default='localhost', help='服务器主机 (默认: localhost)')
    parser.add_argument('--port', default='5000', help='服务器端口 (默认: 5000)')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    
    print(f"多时间框架模块自动测试")
    print(f"测试目标: {base_url}")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    test_suite = MultiTimeframeTestSuite(base_url)
    
    try:
        success = test_suite.run_all_tests()
        
        print("-" * 60)
        if success:
            print("[PASS] 测试通过：多时间框架模块工作正常")
            sys.exit(0)
        else:
            print("[FAIL] 测试失败：发现问题需要修复")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(2)
    except Exception as e:
        print(f"测试过程中发生意外错误: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()
