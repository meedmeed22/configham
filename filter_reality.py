import requests
import re
import os
from datetime import datetime
import urllib.parse

def validate_vless_config(config_line):
    """
    اعتبارسنجی کامل کانفیگ VLESS Reality
    بررسی پارامترهای ضروری: pbk, sni, fp, security=reality
    """
    try:
        # حذف پروتکل و استخراج بخش‌های کانفیگ
        if not config_line.startswith('vless://'):
            return False
        
        # جدا کردن بخش های مختلف
        parts = config_line.split('?')
        if len(parts) != 2:
            return False
        
        # استخراج پارامترهای query string
        query_params = parts[1].split('#')[0]  # حذف کامنت انتهای لینک
        params = {}
        for param in query_params.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
        
        # بررسی پارامترهای ضروری
        required_params = {
            'security': ['reality'],
            'sni': None,  # باید وجود داشته باشد
            'fp': ['chrome', 'firefox', 'safari', 'edge', 'randomized', 'none'],
            'pbk': None,  # باید وجود داشته باشد و حداقل 44 کاراکتر
            'type': ['tcp', 'http', 'quic', 'grpc', 'websocket']  # ساپورت شده
        }
        
        # بررسی security
        if 'security' not in params:
            print(f"⚠️ Missing security parameter")
            return False
        
        if params['security'].lower() != 'reality':
            print(f"⚠️ Security is not 'reality': {params['security']}")
            return False
        
        # بررسی sni
        if 'sni' not in params or not params['sni'].strip():
            print(f"⚠️ Missing or empty sni")
            return False
        
        # بررسی fp (fingerprint)
        if 'fp' not in params:
            print(f"⚠️ Missing fp parameter")
            return False
        
        allowed_fp = ['chrome', 'firefox', 'safari', 'edge', 'randomized', 'none']
        if params['fp'].lower() not in allowed_fp:
            print(f"⚠️ Invalid fp: {params['fp']}")
            return False
        
        # بررسی pbk (public key) - باید Base64 معتبر باشد
        if 'pbk' not in params:
            print(f"⚠️ Missing pbk parameter")
            return False
        
        pbk = params['pbk'].strip()
        if len(pbk) < 44:  # طول استاندارد کلید عمومی X25519
            print(f"⚠️ pbk too short: {len(pbk)} chars")
            return False
        
        # بررسی اینکه pbk فقط شامل کاراکترهای Base64 مجاز باشد
        if not re.match(r'^[A-Za-z0-9+/=]+$', pbk):
            print(f"⚠️ Invalid base64 in pbk")
            return False
        
        # بررسی type (اختیاری اما اگر وجود داشته باشد باید معتبر باشد)
        if 'type' in params:
            allowed_types = ['tcp', 'http', 'quic', 'grpc', 'websocket']
            if params['type'].lower() not in allowed_types:
                print(f"⚠️ Invalid type: {params['type']}")
                return False
        
        # بررسی پورت 443
        if ':443' not in config_line:
            print(f"⚠️ Port is not 443")
            return False
        
        # بررسی ساختار کلی UUID در ابتدای لینک
        uuid_pattern = r'vless://([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
        if not re.search(uuid_pattern, config_line):
            print(f"⚠️ Invalid UUID format")
            return False
        
        # بررسی وجود @ و آدرس IP/دامنه
        if '@' not in config_line:
            print(f"⚠️ Missing @ in config")
            return False
        
        return True
        
    except Exception as e:
        print(f"⚠️ Validation error: {e}")
        return False

def filter_valid_vless_reality_configs():
    url = "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt"
    
    try:
        print("🔄 Downloading configs...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        
        total_configs = 0
        valid_configs = 0
        invalid_configs = 0
        filtered_lines = []
        invalid_details = []
        
        print(f"📥 Total lines: {len(lines)}")
        
        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            
            if 'vless://' in line:
                total_configs += 1
                
                # فیلتر اولیه: security=reality و پورت 443
                if (re.search(r'security=reality', line, re.IGNORECASE) and 
                    re.search(r':443[?&/]', line)):
                    
                    # اعتبارسنجی کامل
                    if validate_vless_config(line):
                        filtered_lines.append(line)
                        valid_configs += 1
                    else:
                        invalid_configs += 1
                        # ذخیره نمونه‌های نامعتبر برای دیباگ
                        if len(invalid_details) < 10:  # فقط 10 نمونه اول
                            invalid_details.append(line[:100] + "...")
        
        # ذخیره کانفیگ‌های معتبر
        output_filename = "vless_reality.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total Configs: {len(filtered_lines)}\n")
            f.write(f"# Valid Configs: {valid_configs}\n")
            f.write(f"# Invalid Configs: {invalid_configs}\n")
            f.write(f"# Total Processed: {total_configs}\n")
            f.write("#" + "="*60 + "\n\n")
            f.write("\n".join(filtered_lines))
        
        # ذخیره لاگ نامعتبرها (اختیاری)
        if invalid_details:
            with open("invalid_configs_sample.txt", "w", encoding="utf-8") as f:
                f.write(f"# Sample of invalid configs ({len(invalid_details)} samples)\n")
                f.write("#" + "="*60 + "\n\n")
                f.write("\n\n".join(invalid_details))
        
        print("\n" + "="*50)
        print(f"✅ Valid configs saved: {len(filtered_lines)}")
        print(f"❌ Invalid configs: {invalid_configs}")
        print(f"📊 Total configs processed: {total_configs}")
        print(f"💾 File: {output_filename}")
        print("="*50)
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    filter_valid_vless_reality_configs()
