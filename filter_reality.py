import requests
import re
import os
from datetime import datetime
import urllib.parse

def validate_vless_config(config_line):
    """
    اعتبارسنجی ملایم‌تر اما دقیق برای VLESS Reality
    فقط کانفیگ‌های واقعاً ناقص را رد می‌کند
    """
    try:
        # حذف پروتکل و استخراج بخش‌های کانفیگ
        if not config_line.startswith('vless://'):
            return False, "Not vless protocol"
        
        # بررسی ساختار کلی
        if '@' not in config_line:
            return False, "Missing @"
        
        # جدا کردن بخش های مختلف
        parts = config_line.split('?')
        if len(parts) != 2:
            return False, "Invalid format (missing ?)"
        
        # استخراج UUID
        uuid_match = re.search(r'vless://([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', config_line)
        if not uuid_match:
            return False, "Invalid UUID format"
        
        # استخراج پارامترهای query string
        query_part = parts[1].split('#')[0]
        params = {}
        for param in query_part.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
        
        # بررسی پارامترهای ضروری با انعطاف بیشتر
        required_params = ['security', 'sni', 'fp', 'pbk']
        missing_params = []
        
        for param in required_params:
            if param not in params or not params[param].strip():
                missing_params.append(param)
        
        if missing_params:
            return False, f"Missing parameters: {', '.join(missing_params)}"
        
        # بررسی security
        if params['security'].lower() != 'reality':
            return False, f"Security is not reality: {params['security']}"
        
        # بررسی sni (فقط وجود داشته باشد)
        if not params['sni'].strip():
            return False, "Empty sni"
        
        # بررسی fp (فقط وجود داشته باشد)
        if not params['fp'].strip():
            return False, "Empty fp"
        
        # بررسی pbk (فقط وجود داشته باشد و طول معقول)
        pbk = params['pbk'].strip()
        if len(pbk) < 32:  # کاهش به ۳۲ کاراکتر
            return False, f"pbk too short: {len(pbk)}"
        
        # بررسی پورت 443 (با انعطاف بیشتر)
        if ':443' not in config_line:
            return False, "Port is not 443"
        
        # بررسی type (اگر وجود داشته باشد)
        if 'type' in params and params['type']:
            # لیست typeهای مجاز در Xray/V2Ray
            allowed_types = ['tcp', 'http', 'quic', 'grpc', 'websocket', 'raw']
            if params['type'].lower() not in allowed_types:
                return False, f"Invalid type: {params['type']}"
        
        return True, "Valid"
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"

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
        invalid_stats = {}
        invalid_samples = []
        
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
                    
                    # اعتبارسنجی
                    is_valid, reason = validate_vless_config(line)
                    
                    if is_valid:
                        filtered_lines.append(line)
                        valid_configs += 1
                    else:
                        invalid_configs += 1
                        # آمار دلایل نامعتبری
                        invalid_stats[reason] = invalid_stats.get(reason, 0) + 1
                        # ذخیره نمونه‌های نامعتبر
                        if len(invalid_samples) < 20:
                            invalid_samples.append({
                                'config': line[:150] + "...",
                                'reason': reason
                            })
        
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
        
        # ذخیره گزارش نامعتبرها
        with open("invalid_report.txt", "w", encoding="utf-8") as f:
            f.write(f"# Invalid Configs Report\n")
            f.write(f"# Total Invalid: {invalid_configs}\n")
            f.write("#" + "="*60 + "\n\n")
            
            f.write("## Statistics by reason:\n")
            for reason, count in sorted(invalid_stats.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {count:>4} : {reason}\n")
            
            f.write("\n## Sample Invalid Configs:\n")
            for i, sample in enumerate(invalid_samples[:10], 1):
                f.write(f"\n{i}. Reason: {sample['reason']}\n")
                f.write(f"   Config: {sample['config']}\n")
        
        print("\n" + "="*60)
        print(f"✅ Valid configs: {valid_configs}")
        print(f"❌ Invalid configs: {invalid_configs}")
        print(f"📊 Total configs processed: {total_configs}")
        print(f"💾 Saved to: {output_filename}")
        print(f"📄 Invalid report: invalid_report.txt")
        print("="*60)
        
        # نمایش آمار دلایل نامعتبری
        if invalid_stats:
            print("\n📋 Top reasons for invalidity:")
            for reason, count in sorted(invalid_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  • {reason}: {count} configs")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    filter_valid_vless_reality_configs()
