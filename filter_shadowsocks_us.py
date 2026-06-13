import requests
import re
import base64
import socket
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_server_and_port(ss_url):
    """استخراج سرور و پورت از لینک Shadowsocks"""
    try:
        # حذف کامنت
        if '#' in ss_url:
            clean_url = ss_url.split('#')[0]
        else:
            clean_url = ss_url
        
        if not clean_url.startswith('ss://'):
            return None, None
        
        encoded_part = clean_url[5:]
        
        # روش اول: ss://method:password@server:port
        if '@' in encoded_part:
            after_at = encoded_part.split('@')[1]
            # استخراج سرور و پورت
            match = re.search(r'([^:]+):(\d+)', after_at)
            if match:
                server = match.group(1)
                port = int(match.group(2))
                return server, port
        
        # روش دوم: ss://base64(method:password@server:port)
        else:
            try:
                decoded = base64.b64decode(encoded_part).decode('utf-8')
                match = re.search(r'@([^:]+):(\d+)', decoded)
                if match:
                    server = match.group(1)
                    port = int(match.group(2))
                    return server, port
            except:
                pass
        
        return None, None
    except:
        return None, None

def is_us_ip(ip_or_domain):
    """بررسی اینکه IP مربوط به آمریکا است یا خیر"""
    try:
        # اگر domain بود، resolve کن
        if not re.match(r'^\d+\.\d+\.\d+\.\d+$', ip_or_domain):
            ip = socket.gethostbyname(ip_or_domain)
        else:
            ip = ip_or_domain
        
        # استفاده از API رایگان برای تشخیص کشور
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('countryCode') == 'US':
                return True
        return False
    except:
        return False

def check_port_443(server, port):
    """بررسی اینکه پورت 443 باز است یا خیر"""
    if port != 443:
        return False
    
    # تست اتصال به پورت 443
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((server, 443))
        sock.close()
        return result == 0
    except:
        return False

def filter_shadowsocks_us_port443():
    """فیلتر کانفیگ‌های Shadowsocks با پورت 443 و IP آمریکا"""
    
    # سورس‌های مختلف برای دریافت کانفیگ
    sources = [
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/ss.txt"
    ]
    
    all_configs = []
    
    for url in sources:
        try:
            print(f"\n📡 دریافت از: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            lines = response.text.splitlines()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if 'ss://' in line:
                    server, port = extract_server_and_port(line)
                    
                    if port == 443 and server:
                        all_configs.append({
                            'config': line,
                            'server': server,
                            'port': port
                        })
                        print(f"  ✅ Found: {server}:{port}")
            
        except Exception as e:
            print(f"  ❌ خطا در دریافت {url}: {e}")
    
    print(f"\n🔍 تعداد کل کانفیگ‌های با پورت 443: {len(all_configs)}")
    
    # فیلتر بر اساس IP آمریکا
    us_configs = []
    
    print("\n🌍 در حال بررسی موقعیت سرورها...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_config = {
            executor.submit(is_us_ip, config['server']): config 
            for config in all_configs
        }
        
        for future in as_completed(future_to_config):
            config = future_to_config[future]
            try:
                if future.result():
                    us_configs.append(config['config'])
                    print(f"  🇺🇸 آمریکا: {config['server']}")
                else:
                    print(f"  ❌ غیر آمریکا: {config['server']}")
            except Exception as e:
                print(f"  ⚠️ خطا در بررسی {config['server']}: {e}")
    
    # حذف موارد تکراری
    unique_us_configs = list(dict.fromkeys(us_configs))
    unique_all_configs = list(dict.fromkeys([c['config'] for c in all_configs]))
    
    # ذخیره فایل فقط آمریکا
    output_us_file = "shadowsocks_us_port443.txt"
    with open(output_us_file, "w", encoding="utf-8") as f:
        f.write(f"# Shadowsocks Configs - USA Servers - Port 443\n")
        f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"# Total Configs: {len(unique_us_configs)}\n")
        f.write(f"# Filter: Port 443 & USA IP\n")
        f.write("#" + "="*70 + "\n\n")
        
        for idx, config in enumerate(unique_us_configs, 1):
            f.write(f"{config}\n")
    
    # ذخیره فایل تمام کانفیگ‌های پورت 443 (بدون فیلتر کشور)
    output_all_file = "shadowsocks_all_port443.txt"
    with open(output_all_file, "w", encoding="utf-8") as f:
        f.write(f"# Shadowsocks Configs - All Servers - Port 443\n")
        f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"# Total Configs: {len(unique_all_configs)}\n")
        f.write("#" + "="*70 + "\n\n")
        
        for idx, config in enumerate(unique_all_configs, 1):
            f.write(f"{config}\n")
    
    # نمایش گزارش نهایی
    print("\n" + "="*60)
    print(f"📊 گزارش نهایی:")
    print(f"  - کل کانفیگ‌های پورت 443: {len(unique_all_configs)}")
    print(f"  - کانفیگ‌های سرور آمریکا: {len(unique_us_configs)}")
    print(f"\n📁 فایل‌های ذخیره شده:")
    print(f"  - {output_us_file} (فقط آمریکا)")
    print(f"  - {output_all_file} (همه کشورها)")
    print("="*60)
    
    # نمایش نمونه
    if unique_us_configs:
        print("\n🇺🇸 نمونه کانفیگ‌های آمریکا:")
        for i, sample in enumerate(unique_us_configs[:3], 1):
            # نمایش خلاصه
            if len(sample) > 80:
                print(f"  {i}. {sample[:80]}...")
            else:
                print(f"  {i}. {sample}")
    
    return True

def main():
    print("🔰 فیلتر Shadowsocks - پورت 443 و سرور آمریکا 🔰")
    print("="*60)
    filter_shadowsocks_us_port443()

if __name__ == "__main__":
    main()
