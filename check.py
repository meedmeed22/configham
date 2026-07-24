#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import time
import socket
import concurrent.futures
import urllib.parse
import os
import tempfile
import re
import statistics
from typing import Dict, List, Tuple, Optional, Any
import requests

# تنظیمات کلی
XRAY_EXE = "xray.exe"
LINKS_FILE = "trojan_port443.txt"
OUTPUT_FILE = "best_configs.txt"
CONFIG_FILE = "config.json"  # فایل تنظیمات GitHub
TEST_URL = "https://www.google.com"
TIMEOUT_CONNECT = 8
TIMEOUT_READ = 10
PROXY_READY_TIMEOUT = 10
INBOUND_PORT_START = 10800
MAX_WORKERS = 10
PING_COUNT = 2
MAX_LINKS_TO_TEST = 700

WEIGHT_TTFB = 0.6
WEIGHT_LOSS = 0.4

def load_github_config():
    """
    بارگذاری تنظیمات GitHub از فایل config.json
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('github_token', ''), config.get('github_username', ''), config.get('github_repo', '')
        except:
            pass
    return '', '', ''

def read_links_from_file(filename: str) -> List[str]:
    """
    خواندن لینک‌های Trojan از فایل
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"فایل {filename} یافت نشد.")
    
    links = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if 'trojan://' in line:
                matches = re.findall(r'trojan://[^\s]+', line)
                links.extend(matches)
    
    valid_links = []
    seen = set()
    for link in links:
        if link not in seen:
            seen.add(link)
            if is_link_valid(link):
                valid_links.append(link)
    
    return valid_links

def is_link_valid(link: str) -> bool:
    """
    بررسی اولیه اعتبار لینک
    """
    if not link.startswith('trojan://'):
        return False
    
    rest = link[9:]
    
    if '#' in rest:
        rest = rest.split('#')[0]
    if '?' in rest:
        rest = rest.split('?')[0]
    
    if '@' not in rest or ':' not in rest:
        return False
    
    try:
        password, host_port = rest.split('@', 1)
        host, port_str = host_port.rsplit(':', 1)
        port_str = re.sub(r'[^0-9]', '', port_str)
        if not port_str:
            return False
        port = int(port_str)
        if port < 1 or port > 65535:
            return False
        return True
    except:
        return False

def parse_trojan_link(link: str) -> Optional[Dict[str, Any]]:
    """
    تجزیه لینک Trojan با مدیریت خطا
    """
    try:
        if not link.startswith("trojan://"):
            return None
        
        rest = link[9:]
        
        name = ""
        if '#' in rest:
            rest, name = rest.split('#', 1)
        
        query = {}
        if '?' in rest:
            rest, query_str = rest.split('?', 1)
            query = urllib.parse.parse_qs(query_str)
        
        if '@' not in rest:
            return None
        
        password, host_port = rest.split('@', 1)
        
        if ':' not in host_port:
            return None
        
        host, port_str = host_port.rsplit(':', 1)
        
        port_str = re.sub(r'[^0-9]', '', port_str)
        if not port_str:
            return None
        
        port = int(port_str)
        if port < 1 or port > 65535:
            return None
        
        sni = query.get('sni', [None])[0]
        if not sni:
            sni = query.get('host', [None])[0]
        
        security = query.get('security', ['tls'])[0]
        allow_insecure = query.get('allowInsecure', ['0'])[0] == '1'
        if not allow_insecure:
            allow_insecure = query.get('insecure', ['0'])[0] == '1'
        
        network = query.get('type', ['tcp'])[0]
        if network in ['xhttp', 'xhttp2']:
            network = 'tcp'
        
        path = query.get('path', [''])[0]
        
        return {
            'password': password,
            'host': host,
            'port': port,
            'sni': sni or host,
            'allow_insecure': allow_insecure,
            'security': security,
            'network': network,
            'path': path,
            'name': name,
            'raw': link
        }
    except Exception as e:
        return None

def generate_config(trojan_info: Dict[str, Any], inbound_port: int) -> Dict:
    """
    تولید کانفیگ JSON برای Xray
    """
    stream_settings = {
        "network": trojan_info['network'],
    }
    
    if trojan_info['security'] == 'tls':
        stream_settings["security"] = "tls"
        stream_settings["tlsSettings"] = {
            "serverName": trojan_info['sni'],
            "allowInsecure": trojan_info['allow_insecure']
        }
    
    if trojan_info['network'] == 'ws' and trojan_info['path']:
        stream_settings["wsSettings"] = {
            "path": trojan_info['path']
        }
    
    outbound = {
        "protocol": "trojan",
        "settings": {
            "servers": [
                {
                    "address": trojan_info['host'],
                    "port": trojan_info['port'],
                    "password": trojan_info['password']
                }
            ]
        },
        "streamSettings": stream_settings
    }
    
    config = {
        "inbounds": [
            {
                "port": inbound_port,
                "protocol": "socks",
                "settings": {
                    "udp": True,
                    "auth": "noauth"
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                }
            }
        ],
        "outbounds": [outbound]
    }
    
    return config

def create_temp_config(config: Dict) -> str:
    """ایجاد فایل موقت کانفیگ"""
    fd, path = tempfile.mkstemp(suffix='.json', prefix='xray_config_')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    return path

def start_xray(config_path: str) -> Optional[subprocess.Popen]:
    """اجرای Xray"""
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        process = subprocess.Popen(
            [XRAY_EXE, "-config", config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return process
    except FileNotFoundError:
        return None
    except Exception:
        return None

def wait_for_proxy(host: str, port: int, timeout: int = PROXY_READY_TIMEOUT) -> bool:
    """انتظار برای آماده شدن پروکسی"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(0.2)
    return False

def test_ttfb(proxy_host: str, proxy_port: int, url: str) -> Optional[float]:
    """تست TTFB"""
    proxies = {
        'http': f'socks5://{proxy_host}:{proxy_port}',
        'https': f'socks5://{proxy_host}:{proxy_port}'
    }
    try:
        start = time.perf_counter()
        response = requests.get(
            url, 
            proxies=proxies, 
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            stream=True
        )
        for chunk in response.iter_content(1024):
            break
        end = time.perf_counter()
        return (end - start) * 1000
    except Exception:
        return None

def test_loss(proxy_host: str, proxy_port: int, url: str, count: int = PING_COUNT) -> Optional[float]:
    """تست Packet Loss فقط"""
    proxies = {
        'http': f'socks5://{proxy_host}:{proxy_port}',
        'https': f'socks5://{proxy_host}:{proxy_port}'
    }
    failures = 0
    
    for _ in range(count):
        try:
            resp = requests.head(
                url, 
                proxies=proxies, 
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ)
            )
            if resp.status_code >= 400:
                failures += 1
        except:
            failures += 1
        time.sleep(0.1)
    
    total = count
    if total == 0:
        return None
    
    loss_percent = (failures / total) * 100
    return loss_percent

def test_config(trojan_link: str, inbound_port: int) -> Dict[str, Any]:
    """تست کامل یک کانفیگ (فقط TTFB و Loss)"""
    result = {
        'link': trojan_link,
        'success': False,
        'ttfb': None,
        'loss_percent': None,
        'error': None,
        'name': ''
    }
    
    config_path = None
    process = None
    
    try:
        trojan_info = parse_trojan_link(trojan_link)
        if not trojan_info:
            raise ValueError("لینک نامعتبر است")
        
        result['name'] = trojan_info.get('name', '')
        
        config = generate_config(trojan_info, inbound_port)
        config_path = create_temp_config(config)
        
        process = start_xray(config_path)
        if not process:
            raise RuntimeError("خطا در اجرای Xray")
        
        if not wait_for_proxy('127.0.0.1', inbound_port):
            raise RuntimeError("پروکسی راه‌اندازی نشد")
        
        ttfb = test_ttfb('127.0.0.1', inbound_port, TEST_URL)
        if ttfb is None or ttfb > 5000:
            raise RuntimeError("TTFB نامعتبر یا timeout")
        result['ttfb'] = ttfb
        
        loss = test_loss('127.0.0.1', inbound_port, TEST_URL)
        if loss is None:
            loss = 100.0
        result['loss_percent'] = loss
        
        result['success'] = True
        
    except Exception as e:
        result['error'] = str(e)
    
    finally:
        if process:
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        if config_path and os.path.exists(config_path):
            try:
                os.unlink(config_path)
            except:
                pass
    
    return result

def rank_configs(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """رتبه‌بندی کانفیگ‌ها بر اساس TTFB و Loss"""
    successful = [r for r in results if r['success']]
    if not successful:
        return []
    
    valid = []
    for r in successful:
        if (r['ttfb'] and r['ttfb'] < 3000 and
            r['loss_percent'] is not None and
            r['loss_percent'] < 50):
            valid.append(r)
    
    if not valid:
        return []
    
    ttfb_list = [r['ttfb'] for r in valid]
    loss_list = [r['loss_percent'] for r in valid]
    
    min_ttfb, max_ttfb = min(ttfb_list), max(ttfb_list)
    min_loss, max_loss = min(loss_list), max(loss_list)
    
    def norm_ttfb(x): 
        return (max_ttfb - x) / (max_ttfb - min_ttfb) if max_ttfb != min_ttfb else 1.0
    
    def norm_loss(x): 
        return (max_loss - x) / (max_loss - min_loss) if max_loss != min_loss else 1.0
    
    for r in valid:
        n_ttfb = norm_ttfb(r['ttfb'])
        n_loss = norm_loss(r['loss_percent'])
        r['score'] = (WEIGHT_TTFB * n_ttfb + WEIGHT_LOSS * n_loss)
    
    valid.sort(key=lambda x: x['score'], reverse=True)
    return valid

def save_best_configs(ranked: List[Dict[str, Any]], filename: str, top_n: int = 20):
    """ذخیره بهترین کانفیگ‌ها"""
    top = ranked[:top_n]
    with open(filename, 'w', encoding='utf-8') as f:
        for item in top:
            name = item.get('name', '')
            if name:
                f.write(f"{item['link']}\n")
            else:
                f.write(f"{item['link']}\n")

def push_to_github():
    """
    ارسال خودکار فایل‌ها به GitHub با استفاده از config.json
    """
    import subprocess
    import os
    
    try:
        print("\n" + "=" * 70)
        print("در حال ارسال به GitHub...")
        print("=" * 70)
        
        # بارگذاری تنظیمات از config.json
        github_token, github_username, github_repo = load_github_config()
        
        if not github_token or not github_username or not github_repo:
            print("⚠️ تنظیمات GitHub در config.json یافت نشد!")
            print("لطفاً فایل config.json را با اطلاعات زیر ایجاد کنید:")
            print("""
{
    "github_token": "YOUR_GITHUB_TOKEN",
    "github_username": "YOUR_GITHUB_USERNAME",
    "github_repo": "YOUR_REPO_NAME"
}
            """)
            return
        
        GITHUB_REPO_URL = f"https://{github_token}@github.com/{github_username}/{github_repo}.git"
        
        # بررسی وجود git
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except:
            print("❌ Git نصب نیست! لطفاً ابتدا Git را نصب کنید.")
            return
        
        # مقداردهی اولیه git اگر نشده باشد
        if not os.path.exists(".git"):
            subprocess.run(["git", "init"], check=True)
            print("✅ Git initialized")
        
        # اضافه کردن فایل‌ها
        files_to_add = ["check.py", "links.txt", "best_configs.txt"]
        for file in files_to_add:
            if os.path.exists(file):
                subprocess.run(["git", "add", file], check=True)
        
        print("✅ فایل‌ها added")
        
        # کامیت
        commit_msg = f"آپدیت خودکار - {time.strftime('%Y-%m-%d %H:%M:%S')}"
        try:
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            print(f"✅ کامیت: {commit_msg}")
        except:
            print("ℹ️ تغییری برای کامیت وجود ندارد")
        
        # تنظیم remote اگر وجود نداشته باشد
        result = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
        if "origin" not in result.stdout:
            subprocess.run(["git", "remote", "add", "origin", GITHUB_REPO_URL], check=True)
            print("✅ Remote added")
        
        # Push به GitHub
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
        print("✅ ارسال به GitHub با موفقیت انجام شد!")
        print(f"🔗 https://github.com/{github_username}/{github_repo}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ خطا در Git: {e}")
        print("⚠️ ممکن است نیاز به تنظیم دستی Git داشته باشید")
    except Exception as e:
        print(f"❌ خطا: {e}")

def main():
    """تابع اصلی"""
    print("=" * 70)
    print("ابزار تست و ارزیابی لینک‌های Trojan با Xray (فقط TTFB و Loss)")
    print("=" * 70)
    print()
    
    # خواندن لینک‌ها
    try:
        links = read_links_from_file(LINKS_FILE)
    except FileNotFoundError as e:
        print(f"❌ خطا: {e}")
        print("لطفاً فایل links.txt را در مسیر جاری ایجاد کنید.")
        return
    
    if not links:
        print("❌ هیچ لینک معتبر Trojan در فایل یافت نشد.")
        return
    
    print(f"✅ تعداد لینک‌های معتبر یافت شده: {len(links)}")
    print("-" * 70)
    
    if len(links) > MAX_LINKS_TO_TEST:
        print(f"⚠️ تعداد لینک‌ها زیاد است، فقط {MAX_LINKS_TO_TEST} تای اول تست می‌شوند.")
        links = links[:MAX_LINKS_TO_TEST]
    
    ports = [INBOUND_PORT_START + i for i in range(len(links))]
    
    results = []
    successful_count = 0
    failed_count = 0
    total = len(links)
    
    print(f"شروع تست {total} لینک... (این عمل ممکن است چند دقیقه طول بکشد)")
    print(f"تعداد تست‌های همزمان: {MAX_WORKERS}")
    print("-" * 70)
    print()
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_link = {
            executor.submit(test_config, link, port): (link, port, idx)
            for idx, (link, port) in enumerate(zip(links, ports))
        }
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_link):
            link, port, idx = future_to_link[future]
            completed += 1
            
            try:
                result = future.result()
                results.append(result)
                
                if result['success']:
                    successful_count += 1
                    name = result.get('name', 'بدون نام')[:25]
                    print(f"✅ [{completed}/{total}] {name}")
                    print(f"   TTFB: {result['ttfb']:.1f}ms | Loss: {result['loss_percent']:.1f}%")
                    print()
                else:
                    failed_count += 1
                    error_msg = result.get('error', 'خطای ناشناخته')
                    print(f"❌ [{completed}/{total}] خطا: {error_msg[:50]}")
                    print()
                    
            except Exception as e:
                failed_count += 1
                print(f"❌ [{completed}/{total}] خطای غیرمنتظره: {e}")
                print()
    
    elapsed_time = time.time() - start_time
    
    ranked = rank_configs(results)
    
    print("=" * 70)
    print("خلاصه نتایج")
    print("=" * 70)
    print(f"✅ تست‌های موفق: {successful_count} از {total}")
    print(f"❌ تست‌های ناموفق: {failed_count} از {total}")
    print(f"⏱️  زمان کل: {elapsed_time:.1f} ثانیه")
    if elapsed_time > 0:
        print(f"⚡ سرعت متوسط: {total / elapsed_time:.2f} تست در ثانیه")
    
    if ranked:
        print("\n" + "=" * 70)
        print(f"🏆 {min(20, len(ranked))} کانفیگ برتر (بر اساس TTFB و Loss):")
        print("=" * 70)
        for i, r in enumerate(ranked[:20], 1):
            name = r.get('name', 'بدون نام')
            print(f"{i}. {name}")
            print(f"   امتیاز: {r['score']:.3f} | TTFB: {r['ttfb']:.1f}ms | Loss: {r['loss_percent']:.1f}%")
            print()
        
        save_best_configs(ranked, OUTPUT_FILE, top_n=20)
        print(f"✅ بهترین کانفیگ‌ها در فایل {OUTPUT_FILE} ذخیره شدند.")
    else:
        print("\n❌ هیچ کانفیگ موفقی یافت نشد.")
        print("⚠️ ممکن است دلایل زیر باعث این مشکل شده باشند:")
        print("   - سرورها پاسخ نمی‌دهند")
        print("   - فایل xray.exe در مسیر جاری وجود ندارد")
        print("   - لینک‌ها نامعتبر هستند")
        print("   - اتصال اینترنت شما مشکل دارد")
    
    if successful_count > 0:
        try:
            successful_results = [r for r in results if r['success']]
            avg_ttfb = statistics.mean([r['ttfb'] for r in successful_results])
            avg_loss = statistics.mean([r['loss_percent'] for r in successful_results])
            print(f"\n📊 میانگین TTFB: {avg_ttfb:.1f}ms")
            print(f"📊 میانگین Packet Loss: {avg_loss:.1f}%")
            
            best_ttfb = min([r['ttfb'] for r in successful_results])
            best_loss = min([r['loss_percent'] for r in successful_results])
            print(f"🏆 بهترین TTFB: {best_ttfb:.1f}ms")
            print(f"🏆 بهترین Packet Loss: {best_loss:.1f}%")
        except:
            pass
    
    # ارسال به GitHub
    push_to_github()

if __name__ == "__main__":
    main()
