import requests
import re
import os
import time
from datetime import datetime

def get_country_code(ip):
    """دریافت کد کشور برای یک IP با استفاده از ip-api.com"""
    try:
        # استفاده از سرویس رایگان ip-api.com (بدون API key)
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('countryCode', '')
    except Exception as e:
        print(f"  ⚠️ خطا در دریافت اطلاعات IP {ip}: {e}")
    return None

def extract_ip_from_trojan(trojan_url):
    """استخراج IP از لینک trojan"""
    # الگوی trojan://password@ip:port
    match = re.search(r'trojan://[^@]+@([^:?]+):(\d+)', trojan_url)
    if match:
        ip = match.group(1)
        port = match.group(2)
        return ip, port
    return None, None

def filter_trojan_configs():
    url = "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/trojan.txt"
    
    try:
        print("📥 دریافت فایل کانفیگ‌ها...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        
        # فیلتر اولیه: فقط کانفیگ‌های trojan با پورت 443
        temp_configs = []
        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            
            if 'trojan://' in line:
                # بررسی پورت 443
                if re.search(r'trojan://[^@]+@([^:?]+):443(?:[?/]|$)', line):
                    temp_configs.append(line)
        
        print(f"📊 کانفیگ‌های با پورت 443 پیدا شد: {len(temp_configs)}")
        
        # فیلتر نهایی: فقط آیپی‌های آمریکا
        us_configs = []
        total = len(temp_configs)
        
        for idx, config in enumerate(temp_configs, 1):
            ip, port = extract_ip_from_trojan(config)
            
            if ip:
                print(f"🔍 بررسی {idx}/{total}: {ip}:{port}")
                
                # بررسی کشور IP
                country = get_country_code(ip)
                
                if country == 'US':
                    print(f"  ✅ آیپی آمریکا: {ip}")
                    us_configs.append(config)
                else:
                    print(f"  ❌ کشور: {country} (آمریکا نیست)")
                
                # تاخیر کوتاه برای جلوگیری از مسدود شدن
                time.sleep(0.1)
            else:
                print(f"  ⚠️ نمی‌توان IP را استخراج کرد: {config[:50]}...")
        
        # ذخیره نتایج در فایل
        output_filename = "trojan_us_port443.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(f"# Trojan Configs - USA IP + Port 443\n")
            f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total Configs: {len(us_configs)}\n")
            f.write(f"# Source: {url}\n")
            f.write("#" + "="*60 + "\n\n")
            f.write("\n".join(us_configs))
        
        print(f"\n✅ نتیجه نهایی:")
        print(f"   - کانفیگ‌های با پورت 443: {len(temp_configs)}")
        print(f"   - کانفیگ‌های آمریکا + پورت 443: {len(us_configs)}")
        print(f"   - ذخیره شده در: {output_filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False

if __name__ == "__main__":
    filter_trojan_configs()