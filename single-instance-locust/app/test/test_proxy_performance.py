#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask代理性能测试脚本
用于测试优化后的/proxy端点性能
"""

import time
import requests
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

class ProxyPerformanceTester:
    def __init__(self, base_url="http://localhost:5000", instance_id="test"):
        self.base_url = base_url
        self.instance_id = instance_id
        self.results = []
        
    def single_request(self, path="", method="GET", timeout=30):
        """执行单个代理请求"""
        url = f"{self.base_url}/proxy/{self.instance_id}/{path}"
        start_time = time.time()
        
        try:
            response = requests.request(method, url, timeout=timeout)
            end_time = time.time()
            
            return {
                'success': True,
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'content_length': len(response.content),
                'path': path,
                'method': method
            }
        except requests.exceptions.Timeout:
            end_time = time.time()
            return {
                'success': False,
                'error': 'timeout',
                'response_time': end_time - start_time,
                'path': path,
                'method': method
            }
        except Exception as e:
            end_time = time.time()
            return {
                'success': False,
                'error': str(e),
                'response_time': end_time - start_time,
                'path': path,
                'method': method
            }
    
    def concurrent_test(self, num_requests=50, num_threads=10, paths=None):
        """并发测试"""
        if paths is None:
            paths = ["", "stats/requests", "stats/failures", "exceptions"]
        
        print(f"开始并发测试: {num_requests}个请求, {num_threads}个线程")
        print(f"测试路径: {paths}")
        
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # 提交任务
            futures = []
            for i in range(num_requests):
                path = paths[i % len(paths)]
                future = executor.submit(self.single_request, path)
                futures.append(future)
            
            # 收集结果
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                # 实时显示进度
                if len(results) % 10 == 0:
                    success_count = sum(1 for r in results if r['success'])
                    print(f"已完成: {len(results)}/{num_requests}, 成功率: {success_count/len(results)*100:.1f}%")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        return self.analyze_results(results, total_time)
    
    def analyze_results(self, results, total_time):
        """分析测试结果"""
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        if not successful_results:
            return {
                'total_requests': len(results),
                'successful_requests': 0,
                'failed_requests': len(failed_results),
                'success_rate': 0,
                'total_time': total_time,
                'requests_per_second': 0,
                'errors': [r['error'] for r in failed_results]
            }
        
        response_times = [r['response_time'] for r in successful_results]
        
        analysis = {
            'total_requests': len(results),
            'successful_requests': len(successful_results),
            'failed_requests': len(failed_results),
            'success_rate': len(successful_results) / len(results) * 100,
            'total_time': total_time,
            'requests_per_second': len(results) / total_time,
            'response_time_stats': {
                'min': min(response_times),
                'max': max(response_times),
                'mean': statistics.mean(response_times),
                'median': statistics.median(response_times),
                'p95': self.percentile(response_times, 95),
                'p99': self.percentile(response_times, 99)
            }
        }
        
        if failed_results:
            error_summary = {}
            for result in failed_results:
                error = result.get('error', 'unknown')
                error_summary[error] = error_summary.get(error, 0) + 1
            analysis['error_summary'] = error_summary
        
        return analysis
    
    def percentile(self, data, percentile):
        """计算百分位数"""
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def print_results(self, analysis):
        """打印测试结果"""
        print("\n" + "="*60)
        print("代理性能测试结果")
        print("="*60)
        print(f"总请求数: {analysis['total_requests']}")
        print(f"成功请求数: {analysis['successful_requests']}")
        print(f"失败请求数: {analysis['failed_requests']}")
        print(f"成功率: {analysis['success_rate']:.2f}%")
        print(f"总耗时: {analysis['total_time']:.2f}秒")
        print(f"QPS (每秒请求数): {analysis['requests_per_second']:.2f}")
        
        if 'response_time_stats' in analysis:
            stats = analysis['response_time_stats']
            print(f"\n响应时间统计 (秒):")
            print(f"  最小值: {stats['min']:.3f}")
            print(f"  最大值: {stats['max']:.3f}")
            print(f"  平均值: {stats['mean']:.3f}")
            print(f"  中位数: {stats['median']:.3f}")
            print(f"  95%分位: {stats['p95']:.3f}")
            print(f"  99%分位: {stats['p99']:.3f}")
        
        if 'error_summary' in analysis:
            print(f"\n错误统计:")
            for error, count in analysis['error_summary'].items():
                print(f"  {error}: {count}次")
        
        print("="*60)

def main():
    """主函数"""
    print("Flask代理性能测试工具")
    print("注意: 请确保Flask应用正在运行且有可用的Locust实例")
    
    tester = ProxyPerformanceTester()
    
    # 测试配置
    test_configs = [
        {"name": "轻量级测试", "requests": 20, "threads": 5},
        {"name": "中等负载测试", "requests": 50, "threads": 10},
        {"name": "高负载测试", "requests": 100, "threads": 20}
    ]
    
    for config in test_configs:
        print(f"\n开始 {config['name']}...")
        try:
            analysis = tester.concurrent_test(
                num_requests=config['requests'],
                num_threads=config['threads']
            )
            tester.print_results(analysis)
            
            # 等待一段时间再进行下一个测试
            if config != test_configs[-1]:
                print("\n等待5秒后进行下一个测试...")
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n测试被用户中断")
            break
        except Exception as e:
            print(f"\n测试出错: {e}")

if __name__ == "__main__":
    main()