import requests
import base64
import re
import time
from datetime import datetime

def decode_shadowsocks_config(ss_line):
    """
    دیکد کردن کانفیگ Shadowsocks با فرمت خاص
    مثال: c3M6Ly9ZV1Z6TFRJMU5pMW5ZMjA2T0VwRGMxQnpjMlpuVXpoMGFWSjNhVTFzYUVGU1p6MDlAMTQ0LjIxNy4xNjQuMjk6MTIwMDAj...
    """
    try:
        # حذف فاصله و کاراکترهای اضافی
        ss_line = ss_line.strip()
        
        # اگر خط با ss:// شروع نمی‌شود، ممکن است کل خط base64 باشد
        if not ss_line.startswith('ss://'):
            # دیکد کردن base64
            decoded = base64.b64decode(ss_line).decode('utf-8')
            if decoded.startswith('ss://'):
                ss_line = decoded
            else:
                return None, None
        
        # حذف ss://
        content = ss_line[5:]
        
        # حذف کامنت (هر چیزی بعد از #)
        if '#' in content:
            content = content.split('#')[0]
        
        # استخراج IP و پورت با regex
        # الگوی IP:Port در انتهای لینک
        match = re.search(r'@([0-9.]+):(\d+)', content)
        if match:
            ip = match.group(1)
            port = match.group(2)
            return ip, port
        
        # اگر @ نبود، ممکن است فرمت دیگری باشد
        match = re.search(r'([0-9.]+):(\d+)$', content)
        if match:
            return match.group(1), match.group(2)
        
        return None, None
        
    except Exception as e:
        print(f"Decode error: {e}")
        return None, None

def get_country_code(ip):
    """دریافت کشور از IP با استفاده از API رایگان"""
    try:
        # استفاده از ip-api.com (رایگان، بدون نیاز به API key)
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('countryCode', '')
    except:
        pass
    return None

def main():
    print("="*60)
    print("Shadowsocks Filter - USA IP + Port 443")
    print("="*60)
    
    # منبع کانفیگ‌ها
    url = "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/ss.txt"
    
    try:
        # دریافت فایل
        print(f"\n📥 Downloading from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        print(f"✅ Total lines: {len(lines)}")
        
        # پردازش هر خط
        port443_configs = []
        all_valid_configs = []
        
        print("\n📊 Decoding configs...")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            ip, port = decode_shadowsocks_config(line)
            
            if ip and port:
                all_valid_configs.append((line, ip, port))
                if str(port) == '443':
                    port443_configs.append((line, ip, port))
                    print(f"   ✅ Found: {ip}:{port}")
        
        print(f"\n📊 Statistics:")
        print(f"   - Valid SS configs: {len(all_valid_configs)}")
        print(f"   - Configs with port 443: {len(port443_configs)}")
        
        if len(port443_configs) == 0:
            print("\n⚠️ No configs with port 443 found!")
            return
        
        # بررسی کشور IPها
        print("\n🔍 Checking IP countries...")
        us_configs = []
        
        for idx, (config, ip, port) in enumerate(port443_configs, 1):
            print(f"   [{idx}/{len(port443_configs)}] {ip}:{port}...", end=" ")
            
            country = get_country_code(ip)
            
            if country == 'US':
                print(f"✅ USA")
                us_configs.append(config)
            else:
                print(f"❌ {country if country else 'Unknown'}")
            
            time.sleep(0.1)  # تاخیر برای احترام به API
        
        # ذخیره نتایج
        output_file = "shadowsocks_us_port443.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Shadowsocks Configs - USA IP + Port 443\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total: {len(us_configs)}\n")
            f.write("#" + "="*60 + "\n\n")
            for config in us_configs:
                f.write(config + "\n")
        
        # گزارش نهایی
        print("\n" + "="*60)
        print("✅ FINAL RESULTS:")
        print(f"   - Total valid SS configs: {len(all_valid_configs)}")
        print(f"   - Port 443: {len(port443_configs)}")
        print(f"   - USA + Port 443: {len(us_configs)}")
        print(f"   - Saved to: {output_file}")
        print("="*60)
        
        # نمایش نمونه
        if us_configs:
            print("\n📝 First 3 USA configs:")
            for i, config in enumerate(us_configs[:3], 1):
                # نمایش 100 کاراکتر اول
                print(f"   {i}. {config[:100]}...")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()