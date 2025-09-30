#!/usr/bin/env python3
"""
300个币种处理能力测试
测试系统在处理大量币种时的性能和稳定性
"""

import requests
import json
import time
import psutil
import os
from datetime import datetime

class Symbol300TestSuite:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': '300-Symbols-Test/1.0'
        })
        
    def log(self, message: str, level: str = "INFO"):
        """记录测试日志"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def get_system_info(self):
        """获取系统信息"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        
        return {
            'memory_mb': memory_info.rss / 1024 / 1024,
            'cpu_percent': cpu_percent,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
    
    def test_get_symbols(self):
        """测试获取币种列表"""
        self.log("测试获取币种列表...")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/multi_timeframe/get_top_symbols", timeout=30)
            end_time = time.time()
            
            if response.status_code != 200:
                self.log(f"获取币种失败，状态码: {response.status_code}", "ERROR")
                return None
                
            data = response.json()
            if not data.get('success'):
                self.log(f"获取币种失败: {data.get('error')}", "ERROR")
                return None
                
            symbols = data.get('symbols', [])
            duration = end_time - start_time
            
            self.log(f"成功获取 {len(symbols)} 个币种，用时 {duration:.2f}秒")
            
            if len(symbols) >= 300:
                self.log(f"[PASS] 币种数量充足: {len(symbols)} >= 300")
                return symbols[:300]  # 只取前300个
            else:
                self.log(f"[WARN] 币种数量不足: {len(symbols)} < 300")
                return symbols
                
        except requests.exceptions.Timeout:
            self.log("获取币种超时", "ERROR")
            return None
        except Exception as e:
            self.log(f"获取币种异常: {e}", "ERROR")
            return None
    
    def test_batch_analysis_performance(self, symbols, batch_size=20):
        """测试批量分析性能"""
        self.log(f"测试批量分析性能 - 批次大小: {batch_size}")
        
        total_batches = (len(symbols) + batch_size - 1) // batch_size
        total_signals = 0
        total_duration = 0
        successful_batches = 0
        failed_batches = 0
        
        system_info_start = self.get_system_info()
        self.log(f"开始时系统状态: {system_info_start['memory_mb']:.1f}MB RAM, {system_info_start['cpu_percent']:.1f}% CPU")
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(symbols))
            batch_symbols = symbols[start_idx:end_idx]
            
            self.log(f"批次 {batch_idx + 1}/{total_batches}: 分析 {len(batch_symbols)} 个币种 ({start_idx + 1}-{end_idx})")
            
            try:
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/multi_timeframe/analyze_multiple_symbols",
                    json={
                        'symbols': batch_symbols,
                        'page': 1,
                        'page_size': 999999  # 获取所有信号
                    },
                    timeout=120  # 2分钟超时
                )
                end_time = time.time()
                
                duration = end_time - start_time
                total_duration += duration
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        signals = data.get('signals', [])
                        total_signals += len(signals)
                        successful_batches += 1
                        
                        self.log(f"  [PASS] 批次 {batch_idx + 1} 成功: {len(signals)} 个信号, 用时 {duration:.1f}s")
                    else:
                        failed_batches += 1
                        self.log(f"  [FAIL] 批次 {batch_idx + 1} 分析失败: {data.get('error')}")
                else:
                    failed_batches += 1
                    self.log(f"  [FAIL] 批次 {batch_idx + 1} HTTP错误: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                failed_batches += 1
                self.log(f"  [TIMEOUT] 批次 {batch_idx + 1} 超时")
            except Exception as e:
                failed_batches += 1
                self.log(f"  [ERROR] 批次 {batch_idx + 1} 异常: {e}")
            
            # 批次间添加短暂延迟
            if batch_idx < total_batches - 1:
                time.sleep(0.5)
                
            # 每10个批次显示进度
            if (batch_idx + 1) % 10 == 0:
                progress = ((batch_idx + 1) / total_batches) * 100
                avg_duration = total_duration / (batch_idx + 1)
                system_info = self.get_system_info()
                self.log(f"  进度: {progress:.1f}% - 平均耗时: {avg_duration:.1f}s/批次 - 内存: {system_info['memory_mb']:.1f}MB")
        
        system_info_end = self.get_system_info()
        
        # 统计总结
        avg_batch_time = total_duration / total_batches if total_batches > 0 else 0
        success_rate = (successful_batches / total_batches) * 100 if total_batches > 0 else 0
        
        self.log("=== 批量分析性能统计 ===")
        self.log(f"总币种数: {len(symbols)}")
        self.log(f"总批次数: {total_batches}")
        self.log(f"成功批次: {successful_batches}")
        self.log(f"失败批次: {failed_batches}")
        self.log(f"成功率: {success_rate:.1f}%")
        self.log(f"总信号数: {total_signals}")
        self.log(f"总耗时: {total_duration:.1f}秒")
        self.log(f"平均批次耗时: {avg_batch_time:.1f}秒")
        self.log(f"处理速率: {len(symbols)/total_duration:.1f} 币种/秒")
        self.log(f"内存使用: {system_info_start['memory_mb']:.1f}MB -> {system_info_end['memory_mb']:.1f}MB")
        
        return {
            'total_symbols': len(symbols),
            'total_batches': total_batches,
            'successful_batches': successful_batches,
            'failed_batches': failed_batches,
            'success_rate': success_rate,
            'total_signals': total_signals,
            'total_duration': total_duration,
            'avg_batch_time': avg_batch_time,
            'processing_rate': len(symbols)/total_duration if total_duration > 0 else 0,
            'memory_usage': {
                'start': system_info_start['memory_mb'],
                'end': system_info_end['memory_mb'],
                'delta': system_info_end['memory_mb'] - system_info_start['memory_mb']
            }
        }
    
    def test_pagination_with_large_dataset(self, symbols):
        """测试大数据集的分页功能"""
        self.log("测试大数据集的分页功能...")
        
        # 先获取所有信号数据
        self.log("获取完整数据集用于分页测试...")
        try:
            response = self.session.post(
                f"{self.base_url}/multi_timeframe/analyze_multiple_symbols",
                json={
                    'symbols': symbols[:50],  # 只用50个币种测试，避免超时
                    'page': 1,
                    'page_size': 999999
                },
                timeout=180
            )
            
            if response.status_code != 200:
                self.log(f"获取测试数据失败: HTTP {response.status_code}", "ERROR")
                return False
                
            data = response.json()
            if not data.get('success'):
                self.log(f"获取测试数据失败: {data.get('error')}", "ERROR")
                return False
                
            total_signals = len(data.get('signals', []))
            pagination_info = data.get('pagination', {})
            
            self.log(f"测试数据集: {total_signals} 个信号")
            self.log(f"分页信息: {pagination_info}")
            
            # 测试不同页面大小
            page_sizes = [10, 25, 50, 100]
            
            for page_size in page_sizes:
                self.log(f"测试页面大小: {page_size}")
                
                expected_pages = (total_signals + page_size - 1) // page_size if total_signals > 0 else 0
                
                # 测试第1页
                response1 = self.session.post(
                    f"{self.base_url}/multi_timeframe/analyze_multiple_symbols",
                    json={
                        'symbols': symbols[:50],
                        'page': 1,
                        'page_size': page_size
                    },
                    timeout=60
                )
                
                if response1.status_code == 200:
                    data1 = response1.json()
                    if data1.get('success'):
                        signals1 = data1.get('signals', [])
                        pagination1 = data1.get('pagination', {})
                        
                        actual_pages = pagination1.get('total_pages', 0)
                        signals_count = len(signals1)
                        
                        self.log(f"  第1页: {signals_count} 个信号, 共 {actual_pages} 页")
                        
                        # 验证分页计算是否正确
                        if actual_pages == expected_pages:
                            self.log(f"  [PASS] 分页计算正确: {actual_pages} 页")
                        else:
                            self.log(f"  [WARN] 分页计算可能有问题: 期望 {expected_pages}, 实际 {actual_pages}")
                        
                        # 测试最后一页（如果有多页）
                        if actual_pages > 1:
                            response_last = self.session.post(
                                f"{self.base_url}/multi_timeframe/analyze_multiple_symbols",
                                json={
                                    'symbols': symbols[:50],
                                    'page': actual_pages,
                                    'page_size': page_size
                                },
                                timeout=60
                            )
                            
                            if response_last.status_code == 200:
                                data_last = response_last.json()
                                if data_last.get('success'):
                                    signals_last = data_last.get('signals', [])
                                    self.log(f"  最后一页: {len(signals_last)} 个信号")
            
            return True
            
        except Exception as e:
            self.log(f"分页测试异常: {e}", "ERROR")
            return False
    
    def test_memory_usage_trend(self, symbols):
        """测试内存使用趋势"""
        self.log("测试内存使用趋势...")
        
        initial_memory = self.get_system_info()['memory_mb']
        memory_samples = [initial_memory]
        
        # 分5个阶段测试，每阶段处理60个币种
        stages = 5
        symbols_per_stage = min(60, len(symbols) // stages)
        
        for stage in range(stages):
            start_idx = stage * symbols_per_stage
            end_idx = min(start_idx + symbols_per_stage, len(symbols))
            stage_symbols = symbols[start_idx:end_idx]
            
            self.log(f"内存测试阶段 {stage + 1}/{stages}: 处理 {len(stage_symbols)} 个币种")
            
            try:
                response = self.session.post(
                    f"{self.base_url}/multi_timeframe/analyze_multiple_symbols",
                    json={
                        'symbols': stage_symbols,
                        'page': 1,
                        'page_size': 100
                    },
                    timeout=120
                )
                
                if response.status_code == 200:
                    current_memory = self.get_system_info()['memory_mb']
                    memory_samples.append(current_memory)
                    memory_delta = current_memory - initial_memory
                    
                    self.log(f"  阶段 {stage + 1} 完成: 内存使用 {current_memory:.1f}MB (+{memory_delta:.1f}MB)")
                else:
                    self.log(f"  阶段 {stage + 1} 失败: HTTP {response.status_code}")
                    
            except Exception as e:
                self.log(f"  阶段 {stage + 1} 异常: {e}")
        
        # 分析内存趋势
        if len(memory_samples) > 1:
            max_memory = max(memory_samples)
            min_memory = min(memory_samples)
            final_memory = memory_samples[-1]
            
            self.log("=== 内存使用趋势分析 ===")
            self.log(f"初始内存: {initial_memory:.1f}MB")
            self.log(f"峰值内存: {max_memory:.1f}MB (+{max_memory - initial_memory:.1f}MB)")
            self.log(f"最低内存: {min_memory:.1f}MB")
            self.log(f"最终内存: {final_memory:.1f}MB (+{final_memory - initial_memory:.1f}MB)")
            self.log(f"内存波动范围: {max_memory - min_memory:.1f}MB")
            
            # 判断内存使用是否合理
            memory_increase = final_memory - initial_memory
            if memory_increase < 100:  # 小于100MB增长认为正常
                self.log("[PASS] 内存使用正常")
            elif memory_increase < 500:  # 小于500MB可接受
                self.log("[WARN] 内存使用较高但可接受")
            else:
                self.log("[FAIL] 内存使用过高，可能存在内存泄漏")
        
        return memory_samples
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        self.log("开始300个币种综合测试")
        self.log("=" * 60)
        
        # 1. 获取币种
        symbols = self.test_get_symbols()
        if not symbols:
            self.log("无法获取币种列表，测试终止", "ERROR")
            return False
        
        actual_count = len(symbols)
        self.log(f"实际测试币种数量: {actual_count}")
        
        # 2. 批量分析性能测试
        performance_result = self.test_batch_analysis_performance(symbols)
        
        # 3. 分页功能测试
        pagination_success = self.test_pagination_with_large_dataset(symbols)
        
        # 4. 内存使用测试
        memory_samples = self.test_memory_usage_trend(symbols)
        
        # 综合评估
        self.log("=" * 60)
        self.log("=== 300个币种测试综合评估 ===")
        
        success_rate = performance_result.get('success_rate', 0)
        processing_rate = performance_result.get('processing_rate', 0)
        total_signals = performance_result.get('total_signals', 0)
        
        self.log(f"处理币种数: {actual_count}")
        self.log(f"成功率: {success_rate:.1f}%")
        self.log(f"处理速率: {processing_rate:.1f} 币种/秒")
        self.log(f"生成信号数: {total_signals}")
        self.log(f"分页功能: {'正常' if pagination_success else '异常'}")
        
        # 综合评分
        overall_score = 0
        if success_rate >= 80:
            overall_score += 30
        elif success_rate >= 60:
            overall_score += 20
        elif success_rate >= 40:
            overall_score += 10
            
        if processing_rate >= 2:
            overall_score += 25
        elif processing_rate >= 1:
            overall_score += 15
        elif processing_rate >= 0.5:
            overall_score += 10
            
        if pagination_success:
            overall_score += 25
            
        if total_signals > 0:
            overall_score += 20
            
        self.log(f"综合评分: {overall_score}/100")
        
        if overall_score >= 80:
            self.log("[EXCELLENT] 系统在300个币种下表现优秀!")
        elif overall_score >= 60:
            self.log("[GOOD] 系统在300个币种下表现良好")
        elif overall_score >= 40:
            self.log("[FAIR] 系统在300个币种下表现一般，建议优化")
        else:
            self.log("[POOR] 系统在300个币种下表现不佳，需要重要优化")
            
        return overall_score >= 60

def main():
    """主函数"""
    print("300个币种处理能力测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    test_suite = Symbol300TestSuite()
    
    try:
        success = test_suite.run_comprehensive_test()
        
        print("-" * 60)
        if success:
            print("[SUCCESS] 300个币种测试通过")
            exit(0)
        else:
            print("[FAILURE] 300个币种测试失败")
            exit(1)
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        exit(2)
    except Exception as e:
        print(f"测试过程中发生意外错误: {e}")
        exit(3)

if __name__ == "__main__":
    main()
