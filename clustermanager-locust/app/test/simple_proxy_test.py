#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的代理功能测试脚本
"""

import requests
import time
import json

def test_proxy_endpoint():
    """测试代理端点基本功能"""
    base_url = "http://localhost:8088"
    
    print("🔍 测试代理端点基本功能...")
    
    # 测试主页
    try:
        print("1. 测试主页访问...")
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"   状态码: {response.status_code}")
        print(f"   响应时间: {response.elapsed.total_seconds():.3f}秒")
        
        # 测试健康检查
        print("2. 测试健康检查...")
        response = requests.get(f"{base_url}/ok", timeout=10)
        print(f"   状态码: {response.status_code}")
        print(f"   响应内容: {response.text}")
        
        # 测试实例列表
        print("3. 测试实例列表...")
        response = requests.get(f"{base_url}/instances", timeout=10)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                instances = response.json()
                print(f"   实例数量: {len(instances)}")
                if instances:
                    print(f"   第一个实例: {instances[0]}")
                else:
                    print("   当前没有运行的实例")
            except:
                print("   响应不是有效的JSON格式")
        
        print("\n✅ 基本功能测试完成")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败：请确保Flask应用正在运行")
        return False
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        return False

def test_proxy_performance():
    """测试代理性能"""
    base_url = "http://localhost:8088"
    
    print("\n🚀 测试代理性能...")
    
    # 简单的并发测试
    import threading
    import time
    
    results = []
    
    def make_request():
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}/", timeout=30)
            end_time = time.time()
            
            results.append({
                'success': True,
                'status_code': response.status_code,
                'response_time': end_time - start_time
            })
        except Exception as e:
            results.append({
                'success': False,
                'error': str(e),
                'response_time': time.time() - start_time
            })
    
    # 启动10个并发请求
    threads = []
    start_time = time.time()
    
    for i in range(10):
        thread = threading.Thread(target=make_request)
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 分析结果
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"总请求数: {len(results)}")
    print(f"成功请求: {len(successful)}")
    print(f"失败请求: {len(failed)}")
    print(f"成功率: {len(successful)/len(results)*100:.1f}%")
    print(f"总耗时: {total_time:.3f}秒")
    print(f"QPS: {len(results)/total_time:.2f}")
    
    if successful:
        response_times = [r['response_time'] for r in successful]
        print(f"平均响应时间: {sum(response_times)/len(response_times):.3f}秒")
        print(f"最快响应时间: {min(response_times):.3f}秒")
        print(f"最慢响应时间: {max(response_times):.3f}秒")
    
    if failed:
        print("失败原因:")
        for result in failed:
            print(f"  - {result['error']}")

def main():
    """主函数"""
    print("=" * 50)
    print("Flask代理优化测试")
    print("=" * 50)
    
    # 基本功能测试
    if test_proxy_endpoint():
        # 性能测试
        test_proxy_performance()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == "__main__":
    main()