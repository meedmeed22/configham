import requests
import base64
import re
import time
from datetime import datetime

def extract_ip_port_from_any_config(line):
    """استخراج IP و پورت از هر نوع کانفیگ (SS, SSR, Trojan, Vmess)"""
    
    line = line.strip()
    
    # حذف کامنت‌های انتهایی
    if '#' in line:
        line = line.split('#')[0]
    
    # 1. پردازش Shadowsocks (ss://)
    if line.startswith('ss://'):
        try:
            content = line[5:]
            # دیکد کردن base64
            decoded = base64.b64decode(content).decode('utf-8')
            # استخراج IP و پورت با regex
            match = re.search(r'@([0-9.]+):(\d+)', decoded)
            if match:
                return match.group(1), match.group(2)
            match = re.search(r'([0-9.]+):(\d+)$', decoded)
            if match:
                return match.group(1), match.group(2)
        except:
            pass
    
    # 2. پردازش SSR (ssr://)
    if line.startswith('ssr://'):
        try:
            content = line[6:]
            decoded = base64.b64decode(content).decode('utf-8')
            # فرمت ssr: host:port:protocol:method:obfs:...
            parts = decoded.split(':')
            if len(parts) >= 2:
                return parts[0], parts[1]
        except:
            pass
    
    # 3. پردازش Trojan (trojan://)
    if line.startswith('trojan://'):
        match = re.search(r'trojan://[^@]+@([^:?]+):(\d+)', line)
        if match:
            return match.group(1), match.group(2)
    
    # 4. اگر کل خط base64 بود (مثل نمونه‌های شما)
    try:
        decoded = base64.b64decode(line).decode('utf-8')
        if decoded.startswith('ss://') or decoded.startswith('ssr://') or decoded.startswith('trojan://'):
            return extract_ip_port_from_any_config(decoded)
    except:
        pass
    
    return None, None

def get_country_code(ip):
    """دریافت کد کشور از IP"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('countryCode', '')
    except:
        pass
    return None

def main():
    print("="*70)
    print("Config Filter - USA IP + Port 443 (Support: SS, SSR, Trojan)")
    print("="*70)
    
    url = "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/ssr.txt"
    
    try:
        print(f"\n📥 Downloading: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        print(f"✅ Total lines: {len(lines)}")
        
        # پیدا کردن کانفیگ‌های با پورت 443
        port443_configs = []
        all_configs = []
        
        print("\n🔍 Processing configs...")
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            ip, port = extract_ip_port_from_any_config(line)
            
            if ip and port:
                all_configs.append((line, ip, port))
                if str(port) == '443':
                    port443_configs.append((line, ip, port))
                    print(f"   ✅ Found: {ip}:{port}")
        
        print(f"\n📊 Statistics:")
        print(f"   - Total valid configs: {len(all_configs)}")
        print(f"   - Configs with port 443: {len(port443_configs)}")
        
        if len(port443_configs) == 0:
            print("\n⚠️ No configs with port 443 found!")
            return
        
        # بررسی کشور
        print("\n🌍 Checking IP countries...")
        us_configs = []
        
        for idx, (config, ip, port) in enumerate(port443_configs, 1):
            print(f"   [{idx}/{len(port443_configs)}] {ip}:{port}...", end=" ")
            
            country = get_country_code(ip)
            
            if country == 'US':
                print(f"✅ USA")
                us_configs.append(config)
            else:
                print(f"❌ {country if country else 'Unknown'}")
            
            time.sleep(0.1)
        
        # ذخیره نتایج
        output_file = "trojan_us_port443.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Configs - USA IP + Port 443\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total: {len(us_configs)}\n")
            f.write("#" + "="*70 + "\n\n")
            for config in us_configs:
                f.write(config + "\n")
        
        # گزارش نهایی
        print("\n" + "="*70)
        print("✅ FINAL RESULTS:")
        print(f"   - Total configs processed: {len(all_configs)}")
        print(f"   - Port 443: {len(port443_configs)}")
        print(f"   - USA + Port 443: {len(us_configs)}")
        print(f"   - Saved to: {output_file}")
        print("="*70)
        
        if us_configs:
            print("\n📝 Sample (first 3):")
            for i, config in enumerate(us_configs[:3], 1):
                print(f"   {i}. {config[:80]}...")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
