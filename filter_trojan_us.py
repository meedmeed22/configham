import requests
import base64
import re
import time
from datetime import datetime

def decode_ss_config(ss_url):
    """
    دیکد کردن کانفیگ Shadowsocks (ss://)
    پشتیبانی از هر دو فرمت:
    - ss://YmYtY2ZnOnRlNTQ2NTY3QDE0Mi45My4yMTEuMTIzOjU0Mg
    - ss://chacha20-ietf-poly1305:password@host:port
    """
    # حذف کامنت‌های انتهای لینک
    if '#' in ss_url:
        ss_url = ss_url.split('#')[0]
    
    # حذف ss:// از ابتدا
    if not ss_url.startswith('ss://'):
        return None, None
    
    encoded_part = ss_url[5:]  # حذف ss://
    
    try:
        # اگر فرمت جدید باشد (بدون @ در بخش اول)
        if '@' not in encoded_part:
            # دیکد کردن بخش Base64
            decoded = base64.b64decode(encoded_part).decode('utf-8')
            
            # حالا فرمت decoded به صورت method:password@host:port است
            if '@' in decoded:
                method_pass, host_port = decoded.split('@', 1)
                method, password = method_pass.split(':', 1)
                host, port = host_port.split(':')
                return host, port
        else:
            # فرمت قدیمی: method:password@host:port
            # ابتدا قسمت قبل از @ را دیکد می‌کنیم
            method_pass, host_port = encoded_part.split('@', 1)
            decoded_method_pass = base64.b64decode(method_pass).decode('utf-8')
            method, password = decoded_method_pass.split(':', 1)
            host, port = host_port.split(':')
            return host, port
            
    except Exception as e:
        # اگر روش اول جواب نداد، روش جایگزین
        try:
            # برخی کانفیگ‌ها کل لینک به جز ss:// base64 هستند
            decoded = base64.b64decode(encoded_part).decode('utf-8')
            # استخراج با رجکس
            match = re.search(r'([^:@]+):([^@]+)@([^:]+):(\d+)', decoded)
            if match:
                return match.group(3), match.group(4)
        except:
            pass
    
    return None, None

def get_country_from_ip(ip):
    """دریافت کد کشور از آیپی با استفاده از api.ipapi.co (رایگان)"""
    try:
        # استفاده از سرویس رایگان ipapi.co
        response = requests.get(f"https://ipapi.co/{ip}/country_code/", timeout=5)
        if response.status_code == 200:
            country_code = response.text.strip()
            return country_code if country_code else None
    except:
        # سرویس پشتیبان
        try:
            response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('countryCode')
        except:
            pass
    return None

def extract_ip_port_from_config(line):
    """استخراج آیپی و پورت از هر خط کانفیگ"""
    # فقط کانفیگ‌های ss:// را پردازش کن
    if not line.startswith('ss://'):
        return None, None
    
    return decode_ss_config(line)

def main():
    """تابع اصلی برای فیلتر کانفیگ‌های Shadowsocks با پورت 443 و آیپی آمریکا"""
    
    # آدرس فایل کانفیگ‌ها (شما می‌توانید تغییر دهید)
    url = "https://github.com/Epodonios/v2ray-configs/raw/main/Splitted-By-Protocol/ss.txt"
    
    print("="*60)
    print("Shadowsocks Config Filter - USA IP + Port 443")
    print("="*60)
    
    try:
        # دریافت فایل
        print(f"\n📥 Downloading from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        print(f"✅ Total lines: {len(lines)}")
        
        # فیلتر اول: پیدا کردن کانفیگ‌های Shadowsocks با پورت 443
        ss_port443 = []
        all_ss_configs = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('ss://'):
                all_ss_configs.append(line)
                ip, port = decode_ss_config(line)
                if ip and port and str(port) == '443':
                    ss_port443.append({
                        'config': line,
                        'ip': ip,
                        'port': port
                    })
        
        print(f"\n📊 Statistics:")
        print(f"   - Total SS configs: {len(all_ss_configs)}")
        print(f"   - SS configs with port 443: {len(ss_port443)}")
        
        if len(ss_port443) == 0:
            print("\n⚠️ No Shadowsocks configs with port 443 found!")
            return
        
        # فیلتر دوم: بررسی آیپی آمریکا
        us_configs = []
        
        print(f"\n🔍 Checking IP countries...")
        for idx, item in enumerate(ss_port443, 1):
            ip = item['ip']
            print(f"   [{idx}/{len(ss_port443)}] Checking {ip}:{item['port']}...", end=" ")
            
            country = get_country_from_ip(ip)
            
            if country == 'US':
                print(f"✅ USA")
                us_configs.append(item['config'])
            else:
                print(f"❌ {country if country else 'Unknown'}")
            
            # تاخیر برای جلوگیری از مسدود شدن API
            time.sleep(0.2)
        
        # ذخیره نتایج نهایی
        output_file = "shadowsocks_us_port443.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Shadowsocks Configs - USA IP + Port 443\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total configs: {len(us_configs)}\n")
            f.write("#" + "="*60 + "\n\n")
            
            for config in us_configs:
                f.write(config + "\n")
        
        # گزارش نهایی
        print("\n" + "="*60)
        print("✅ FINAL RESULT:")
        print(f"   - Total SS configs: {len(all_ss_configs)}")
        print(f"   - Port 443: {len(ss_port443)}")
        print(f"   - USA + Port 443: {len(us_configs)}")
        print(f"   - Saved to: {output_file}")
        print("="*60)
        
        # نمایش چند نمونه
        if us_configs:
            print("\n📝 Sample configs:")
            for i, config in enumerate(us_configs[:3], 1):
                print(f"   {i}. {config[:80]}...")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Network error: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()