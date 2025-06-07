#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式仪表板启动器
"""

import os
import sys
import webbrowser
import http.server
import socketserver
import threading
import time
from pathlib import Path

def check_files():
    """检查必要文件是否存在"""
    required_files = [
        'enhanced_dashboard.html',
        'multi_company_analysis.json'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 缺少必要文件:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True

def find_free_port(start_port=8000):
    """查找可用端口"""
    import socket
    
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    
    return None

def start_server(port=8000):
    """启动HTTP服务器"""
    try:
        # 查找可用端口
        available_port = find_free_port(port)
        if not available_port:
            print(f"❌ 无法找到可用端口 (尝试范围: {port}-{port+99})")
            return None
        
        # 创建服务器
        handler = http.server.SimpleHTTPRequestHandler
        httpd = socketserver.TCPServer(("", available_port), handler)
        
        print(f"✅ 服务器启动成功！")
        print(f"📍 地址: http://localhost:{available_port}")
        print(f"📊 仪表板: http://localhost:{available_port}/enhanced_dashboard.html")
        print(f"🔄 按 Ctrl+C 停止服务器")
        
        # 延迟打开浏览器
        def open_browser():
            time.sleep(1)
            webbrowser.open(f'http://localhost:{available_port}/enhanced_dashboard.html')
        
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # 启动服务器
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
        httpd.shutdown()
    except Exception as e:
        print(f"❌ 启动服务器失败: {e}")
        return None

def main():
    """主函数"""
    print("🚀 企业竞争力分析仪表板启动器")
    print("=" * 50)
    
    # 检查文件
    if not check_files():
        print("\n💡 提示:")
        print("1. 确保 enhanced_dashboard.html 文件存在")
        print("2. 运行 python qa_system.py 生成分析数据")
        print("3. 或者直接打开 enhanced_dashboard.html 文件（无需服务器）")
        return
    
    print("✅ 文件检查通过")
    
    # 提供选择
    print("\n📋 启动选项:")
    print("1. 启动本地服务器 (推荐)")
    print("2. 直接打开HTML文件")
    print("3. 退出")
    
    try:
        choice = input("\n请选择 (1-3): ").strip()
        
        if choice == '1':
            print("\n🌐 启动本地服务器...")
            start_server()
        elif choice == '2':
            html_path = os.path.abspath('enhanced_dashboard.html')
            print(f"\n📂 打开文件: {html_path}")
            webbrowser.open(f'file://{html_path}')
            print("✅ 已在浏览器中打开仪表板")
        elif choice == '3':
            print("👋 再见！")
        else:
            print("❌ 无效选择")
            
    except KeyboardInterrupt:
        print("\n👋 再见！")

if __name__ == "__main__":
    main() 