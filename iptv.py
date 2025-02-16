#!/opt/iptv_env/bin/python3
# -*- coding: utf-8 -*-

import sys
import requests
import concurrent.futures
from urllib.parse import urlparse, parse_qs
import os
import socket
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
from collections import Counter
import warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_network_capabilities():
    """检查当前网络环境的能力"""
    capabilities = {
        'ipv4': {'available': False, 'speed': 0},
        'ipv6': {'available': False, 'speed': 0}
    }
    
    # 检查IPv4连接和速度
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(('8.8.8.8', 53))
        capabilities['ipv4']['available'] = True
        capabilities['ipv4']['speed'] = 1 / (time.time() - start_time)
    except:
        pass
    finally:
        sock.close()
    
    # 检查IPv6连接和速度
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(('2001:4860:4860::8888', 53))
        capabilities['ipv6']['available'] = True
        capabilities['ipv6']['speed'] = 1 / (time.time() - start_time)
    except:
        pass
    finally:
        sock.close()
    
    # 自动决定IP偏好
    if capabilities['ipv4']['available'] and capabilities['ipv6']['available']:
        if capabilities['ipv4']['speed'] > capabilities['ipv6']['speed']:
            capabilities['preference'] = 'ipv4'
        else:
            capabilities['preference'] = 'ipv6'
    elif capabilities['ipv4']['available']:
        capabilities['preference'] = 'ipv4'
    elif capabilities['ipv6']['available']:
        capabilities['preference'] = 'ipv6'
    else:
        capabilities['preference'] = None
        
    return capabilities

def is_valid_url(url):
    """检查是否是有效的URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_epg_data():
    """从EPG网站获取频道信息"""
    try:
        print("\n请选择EPG数据源:")
        print("1. 使用默认EPG源")
        print("2. 使用自定义EPG源")
        print("3. 不使用EPG数据")
        print("4. 使用本地缓存EPG数据")  # 新增选项
        
        while True:
            choice = input("\n请选择 (1-4): ").strip()
            
            if choice == '3':
                print("将不使用EPG数据")
                return {}
                
            if choice == '4':
                cache_file = 'epg_cache.json'
                if os.path.exists(cache_file):
                    try:
                        import json
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            channels = json.load(f)
                        print(f"成功加载本地缓存的EPG数据 ({len(channels)} 个频道)")
                        return channels
                    except:
                        print("本地缓存数据加载失败")
                else:
                    print("未找到本地缓存数据")
                return {}
                
            if choice == '1':
                # 添加多个备用EPG源
                urls = [
                    'https://epg.112114.xyz/pp.xml',
                    'https://epg.112114.xyz/e.xml',
                    'http://epg.51zmt.top:8000/api/diyp/',
                    'http://epg.51zmt.top:8000/e.xml'
                ]
                
                for url in urls:
                    try:
                        print(f"\n正在尝试获取EPG数据 ({url})...")
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                        response = requests.get(url, 
                                             timeout=15,  # 增加超时时间
                                             verify=False,  # 禁用SSL验证
                                             headers=headers)  # 添加请求头
                        response.raise_for_status()
                        response.encoding = 'utf-8'
                        content = response.text
                        
                        channels = {}
                        # 根据不同格式解析数据
                        if url.endswith('.txt') or url.endswith('/diyp/'):
                            # 解析txt格式
                            for line in content.splitlines():
                                if ',' in line:
                                    parts = line.split(',')
                                    if len(parts) >= 2:
                                        channel_id = parts[0].strip()
                                        name = parts[1].strip()
                                        channels[name] = {
                                            'id': channel_id,
                                            'name': name
                                        }
                        elif url.endswith('.xml'):
                            # 解析xml格式
                            try:
                                import xml.etree.ElementTree as ET
                                from io import StringIO
                                tree = ET.parse(StringIO(content))
                                root = tree.getroot()
                                for channel in root.findall('.//channel'):
                                    channel_id = channel.get('id', '')
                                    name_elem = channel.find('display-name')
                                    if name_elem is not None and channel_id:
                                        name = name_elem.text.strip()
                                        channels[name] = {
                                            'id': channel_id,
                                            'name': name
                                        }
                            except ET.ParseError as e:
                                print(f"XML解析错误: {e}")
                                continue
                        
                        if channels:
                            print(f"成功获取 {len(channels)} 个频道的EPG信息")
                            # 保存到本地缓存
                            try:
                                import json
                                with open('epg_cache.json', 'w', encoding='utf-8') as f:
                                    json.dump(channels, f, ensure_ascii=False, indent=2)
                                print("EPG数据已保存到本地缓存")
                            except:
                                print("保存本地缓存失败")
                            return channels
                            
                    except requests.RequestException as e:
                        print(f"获取EPG数据失败: {e}")
                        continue
                    except Exception as e:
                        print(f"处理EPG数据时出错: {e}")
                        continue
                
                print("所有EPG源都无法访问")
                print("尝试使用本地缓存...")
                
                # 尝试使用本地缓存
                cache_file = 'epg_cache.json'
                if os.path.exists(cache_file):
                    try:
                        import json
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            channels = json.load(f)
                        print(f"成功加载本地缓存的EPG数据 ({len(channels)} 个频道)")
                        return channels
                    except:
                        print("本地缓存数据加载失败")
                
                return {}
                    
            elif choice == '2':
                print("暂时跳过自定义EPG源，将不使用EPG数据")
                return {}
            else:
                print("无效的选择，请重新输入")
                
    except Exception as e:
        print(f"警告: 无法获取EPG数据: {str(e)}")
        print("将不使用EPG数据")
        return {}

def check_stream(url):
    """检查流媒体链接是否可用"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Range': 'bytes=0-4095'  # 请求前4KB数据
        }

        # 直接使用GET请求并检查内容
        response = requests.get(
            url,
            timeout=5,  # 增加超时时间
            headers=headers,
            stream=True,
            verify=False
        )
        
        if response.status_code not in [200, 206]:  # 检查状态码（包括部分内容响应）
            return {
                'status': 'fail',
                'error': f'HTTP状态码错误: {response.status_code}'
            }

        # 读取一段数据进行分析
        content = next(response.iter_content(4096), None)
        
        if not content:
            return {
                'status': 'fail',
                'error': '无法读取流数据'
            }

        # 检查数据特征
        # 常见的流媒体格式特征
        stream_signatures = [
            b'FLV', b'G@', b'\x47',  # FLV, TS流特征
            b'ID3', b'#EXTM3U',      # MP3, M3U特征
            b'RIFF',                  # AVI特征
            b'\x00\x00\x00\x1c',     # H264特征
            b'\x00\x00\x01',         # MPEG特征
        ]

        # 检查内容是否包含任何已知的流媒体格式特征
        is_valid_stream = any(sig in content for sig in stream_signatures)
        
        if is_valid_stream:
            return {
                'status': 'ok',
                'response_time': f"{response.elapsed.total_seconds():.2f}秒",
                'status_code': response.status_code,
                'content_type': response.headers.get('Content-Type', 'unknown')
            }
        else:
            # 如果没有找到特征，但服务器返回了正确的Content-Type
            content_type = response.headers.get('Content-Type', '').lower()
            valid_types = ['video/', 'audio/', 'application/octet-stream', 'application/vnd.apple.mpegurl']
            
            if any(t in content_type for t in valid_types):
                return {
                    'status': 'ok',
                    'response_time': f"{response.elapsed.total_seconds():.2f}秒",
                    'status_code': response.status_code,
                    'content_type': content_type
                }
            
            return {
                'status': 'fail',
                'error': f'未识别的流媒体格式 (Content-Type: {content_type})'
            }

    except requests.exceptions.Timeout:
        return {
            'status': 'fail',
            'error': '连接超时'
        }
    except requests.exceptions.ConnectionError:
        return {
            'status': 'fail',
            'error': '连接错误'
        }
    except requests.exceptions.TooManyRedirects:
        return {
            'status': 'fail',
            'error': '重定向次数过多'
        }
    except requests.exceptions.RequestException as e:
        return {
            'status': 'fail',
            'error': str(e)
        }

def parse_channel_info(extinf_line):
    """解析EXTINF行的频道信息"""
    channel_info = {}
    
    # 获取频道名称
    name_match = re.search(r'tvg-name="([^"]*)"', extinf_line) or \
                re.search(r'group-title="[^"]*",\s*([^,]+)$', extinf_line) or \
                re.search(r',([^,]+)$', extinf_line)
    
    if name_match:
        channel_info['name'] = name_match.group(1).strip()
    
    # 解析分辨率
    resolution = 0
    if '4K' in extinf_line or '2160P' in extinf_line.upper():
        resolution = 2160
    elif '1080P' in extinf_line.upper() or 'FHD' in extinf_line.upper():
        resolution = 1080
    elif '720P' in extinf_line.upper() or 'HD' in extinf_line.upper():
        resolution = 720
    elif '576P' in extinf_line.upper() or 'SD' in extinf_line.upper():
        resolution = 576
    elif '480P' in extinf_line.upper():
        resolution = 480
    channel_info['resolution'] = resolution
    
    return channel_info

def load_m3u_content(source):
    """加载m3u内容,支持URL和本地文件"""
    try:
        if is_valid_url(source):
            print(f"正在从URL下载m3u文件: {source}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            # 尝试多次下载
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # 禁用SSL验证警告
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        response = requests.get(
                            source, 
                            timeout=30,
                            headers=headers,
                            verify=False,
                            allow_redirects=True
                        )
                    response.raise_for_status()
                    
                    # 检查内容类型
                    if 'text/plain' in response.headers.get('Content-Type', ''):
                        response.encoding = 'utf-8'
                    else:
                        # 尝试检测编码
                        response.encoding = response.apparent_encoding or 'utf-8'
                    
                    content = response.text
                    if '#EXTM3U' in content:  # 验证是否是有效的M3U文件
                        return content
                    else:
                        print(f"警告: 下载的内容可能不是有效的M3U文件")
                        print("尝试继续处理...")
                        return content
                        
                except requests.RequestException as e:
                    if attempt < max_retries - 1:
                        print(f"下载失败，正在重试 ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(2)  # 等待2秒后重试
                        continue
                    else:
                        raise
            
        else:
            if not os.path.exists(source):
                raise FileNotFoundError(f"找不到文件: {source}")
            print(f"正在读取本地文件: {source}")
            with open(source, 'r', encoding='utf-8') as f:
                content = f.read()
                if '#EXTM3U' in content:
                    return content
                else:
                    print(f"警告: 文件可能不是有效的M3U文件")
                    print("尝试继续处理...")
                    return content
                    
    except requests.exceptions.RequestException as e:
        print(f"下载m3u文件失败: {e}")
        print("提示: 如果您可以在浏览器中访问该URL，可以先下载到本地再使用本地文件路径")
        return None
    except Exception as e:
        print(f"读取m3u文件失败: {e}")
        return None

def is_ipv6_url(url):
    """检查是否是IPv6地址的URL"""
    try:
        host = urlparse(url).netloc.split(':')[0]
        # 检查是否包含IPv6的特征（多个冒号）
        return ':' in host or any(c in host for c in '[]')
    except:
        return False

def check_all_streams(source):
    """检查所有流的可用性"""
    content = load_m3u_content(source)
    if not content:
        print("无法加载M3U内容")
        return

    # 创建输出目录
    output_dir = "m3u_check_result"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    lines = content.splitlines()
    
    # 分别存储IPv4和IPv6的流
    ipv4_working = ["#EXTM3U\n"]
    ipv4_failed = ["#EXTM3U\n"]
    ipv6_working = ["#EXTM3U\n"]
    ipv6_failed = ["#EXTM3U\n"]
    # 添加总的汇总列表
    all_working = ["#EXTM3U\n"]
    all_failed = ["#EXTM3U\n"]
    
    total_streams = sum(1 for line in lines if line.strip().startswith('http'))
    working_count = 0
    ipv4_working_count = 0
    ipv6_working_count = 0
    ipv4_total = 0
    ipv6_total = 0
    current = 0

    print(f"\n开始检查，共发现 {total_streams} 个流媒体链接")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        current_extinf = None
        channel_info = None
        futures = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('#EXTINF:'):
                current_extinf = line
                channel_info = parse_channel_info(line)
                continue
                
            if line.startswith('http'):
                is_ipv6 = is_ipv6_url(line)
                if is_ipv6:
                    ipv6_total += 1
                else:
                    ipv4_total += 1
                futures.append((executor.submit(check_stream, line), current_extinf, line, channel_info, is_ipv6))

        for future in concurrent.futures.as_completed([f[0] for f in futures]):
            current += 1
            
            for f, extinf, url, info, is_ipv6 in futures:
                if f == future:
                    result = future.result()
                    if result['status'] == 'ok':
                        working_count += 1
                        if is_ipv6:
                            ipv6_working_count += 1
                            if extinf:
                                ipv6_working.append(f"{extinf}\n")
                                all_working.append(f"{extinf}\n")
                            ipv6_working.append(f"{url}\n")
                            all_working.append(f"{url}\n")
                        else:
                            ipv4_working_count += 1
                            if extinf:
                                ipv4_working.append(f"{extinf}\n")
                                all_working.append(f"{extinf}\n")
                            ipv4_working.append(f"{url}\n")
                            all_working.append(f"{url}\n")
                    else:
                        if is_ipv6:
                            if extinf:
                                ipv6_failed.append(f"{extinf}\n")
                                all_failed.append(f"{extinf}\n")
                            ipv6_failed.append(f"{url}\n")
                            all_failed.append(f"{url}\n")
                        else:
                            if extinf:
                                ipv4_failed.append(f"{extinf}\n")
                                all_failed.append(f"{extinf}\n")
                            ipv4_failed.append(f"{url}\n")
                            all_failed.append(f"{url}\n")
                    break
            
            print(f"\r检查进度: {current}/{total_streams} ({(current/total_streams*100):.1f}%) "
                  f"IPv4可用: {ipv4_working_count}/{ipv4_total} "
                  f"IPv6可用: {ipv6_working_count}/{ipv6_total}", end='')

    # 保存结果文件
    # 保存总的汇总文件
    all_working_file = os.path.join(output_dir, f"全部_可用_{working_count}个.m3u")
    all_failed_file = os.path.join(output_dir, f"全部_不可用_{total_streams - working_count}个.m3u")
    with open(all_working_file, 'w', encoding='utf-8') as f:
        f.writelines(all_working)
    with open(all_failed_file, 'w', encoding='utf-8') as f:
        f.writelines(all_failed)

    # 保存IPv4文件
    if ipv4_total > 0:
        ipv4_working_file = os.path.join(output_dir, f"IPv4_可用_{ipv4_working_count}个.m3u")
        ipv4_failed_file = os.path.join(output_dir, f"IPv4_不可用_{ipv4_total - ipv4_working_count}个.m3u")
        with open(ipv4_working_file, 'w', encoding='utf-8') as f:
            f.writelines(ipv4_working)
        with open(ipv4_failed_file, 'w', encoding='utf-8') as f:
            f.writelines(ipv4_failed)

    # 保存IPv6文件
    if ipv6_total > 0:
        ipv6_working_file = os.path.join(output_dir, f"IPv6_可用_{ipv6_working_count}个.m3u")
        ipv6_failed_file = os.path.join(output_dir, f"IPv6_不可用_{ipv6_total - ipv6_working_count}个.m3u")
        with open(ipv6_working_file, 'w', encoding='utf-8') as f:
            f.writelines(ipv6_working)
        with open(ipv6_failed_file, 'w', encoding='utf-8') as f:
            f.writelines(ipv6_failed)

    print(f"\n\n检查完成!")
    print(f"总计: {total_streams} 个流")
    print(f"总可用: {working_count} 个")
    print(f"IPv4: 总共 {ipv4_total} 个，可用 {ipv4_working_count} 个")
    print(f"IPv6: 总共 {ipv6_total} 个，可用 {ipv6_working_count} 个")

    print(f"\n结果已保存到目录: {output_dir}")
    print(f"全部可用流: 全部_可用_{working_count}个.m3u")
    print(f"全部不可用流: 全部_不可用_{total_streams - working_count}个.m3u")
    if ipv4_total > 0:
        print(f"IPv4可用流: IPv4_可用_{ipv4_working_count}个.m3u")
        print(f"IPv4不可用流: IPv4_不可用_{ipv4_total - ipv4_working_count}个.m3u")
    if ipv6_total > 0:
        print(f"IPv6可用流: IPv6_可用_{ipv6_working_count}个.m3u")
        print(f"IPv6不可用流: IPv6_不可用_{ipv6_total - ipv6_working_count}个.m3u")

    # 添加继续/退出选项
    while True:
        choice = input("\n是否继续检测其他文件？(y/n): ").lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        else:
            print("无效的选择，请输入 y 或 n")

def get_m3u_source():
    """获取m3u源"""
    while True:
        print("\n请选择m3u源类型:")
        print("1. 输入m3u文件URL")
        print("2. 输入本地m3u文件路径")
        print("3. 使用默认本地文件(./iptv.m3u)")
        print("4. 检测全部节点可用性")
        print("5. 退出程序")  # 新增退出选项
        
        choice = input("\n请选择 (1-5): ").strip()
        
        if choice == '5':
            print("程序已退出")
            sys.exit(0)
            
        if choice == '4':
            source = input("请输入m3u文件路径或URL: ").strip()
            if is_valid_url(source) or os.path.exists(source):
                continue_check = check_all_streams(source)
                if not continue_check:
                    print("程序已退出")
                    sys.exit(0)
                continue
            print("无效的文件路径或URL，请重新输入")
            continue
        
        if choice == '1':
            url = input("请输入m3u文件URL: ").strip()
            if is_valid_url(url):
                return url
            print("无效的URL,请重新输入")
        
        elif choice == '2':
            path = input("请输入本地m3u文件路径: ").strip()
            if os.path.exists(path):
                return path
            print("文件不存在,请重新输入")
        
        elif choice == '3':
            default_path = './iptv.m3u'
            if os.path.exists(default_path):
                return default_path
            print("默认文件不存在,请选择其他选项")
        
        else:
            print("无效的选择,请重新输入")

def main():
    # 检查网络环境
    print("正在检查网络环境...")
    network_info = check_network_capabilities()
    
    if network_info['ipv4']['available']:
        print(f"√ IPv4 网络可用 (速度评分: {network_info['ipv4']['speed']:.2f})")
    if network_info['ipv6']['available']:
        print(f"√ IPv6 网络可用 (速度评分: {network_info['ipv6']['speed']:.2f})")
    
    print(f"\n将优先使用 {network_info['preference'].upper()} 网络")
    
    # 获取EPG数据
    epg_data = get_epg_data()
    
    # 获取m3u源
    m3u_source = get_m3u_source()
    if not m3u_source:  # 如果返回None，说明已经完成了全部检测
        return
        
    # ... 其余代码保持不变 ...

if __name__ == "__main__":
    main() 
