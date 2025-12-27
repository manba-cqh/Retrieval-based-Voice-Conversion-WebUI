"""获取MAC地址的工具函数"""
import platform
import subprocess
import re
import uuid


def get_mac_address() -> str:
    """
    获取本机的MAC地址
    
    Returns:
        MAC地址字符串（格式：XX:XX:XX:XX:XX:XX）
    """
    try:
        system = platform.system()
        
        if system == "Windows":
            # Windows系统
            result = subprocess.run(
                ["getmac", "/fo", "csv", "/nh"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line and ',' in line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            mac = parts[0].strip().replace('-', ':')
                            # 验证MAC地址格式
                            if re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac):
                                return mac.upper()
        
        elif system == "Darwin":  # macOS
            # macOS系统
            result = subprocess.run(
                ["ifconfig"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # 查找第一个有效的MAC地址（排除虚拟接口）
                mac_pattern = r'ether\s+([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2})'
                matches = re.findall(mac_pattern, result.stdout, re.IGNORECASE)
                if matches:
                    return matches[0].upper()
        
        elif system == "Linux":
            # Linux系统
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # 查找第一个有效的MAC地址
                mac_pattern = r'link/ether\s+([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2})'
                matches = re.findall(mac_pattern, result.stdout, re.IGNORECASE)
                if matches:
                    return matches[0].upper()
        
        # 如果上述方法都失败，使用uuid模块（可能返回虚拟MAC）
        mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
        if mac and mac != '00:00:00:00:00:00':
            return mac.upper()
        
    except Exception as e:
        print(f"获取MAC地址失败: {e}")
    
    # 如果所有方法都失败，返回一个默认值（不应该发生）
    return "00:00:00:00:00:00"


def format_mac_address(mac: str) -> str:
    """
    格式化MAC地址为标准格式（XX:XX:XX:XX:XX:XX）
    
    Args:
        mac: MAC地址字符串（可能包含-或:分隔符，或没有分隔符）
    
    Returns:
        格式化后的MAC地址
    """
    # 移除所有分隔符
    mac_clean = re.sub(r'[:-]', '', mac)
    
    # 验证长度
    if len(mac_clean) != 12:
        raise ValueError(f"无效的MAC地址格式: {mac}")
    
    # 验证字符
    if not re.match(r'^[0-9A-Fa-f]{12}$', mac_clean):
        raise ValueError(f"MAC地址包含无效字符: {mac}")
    
    # 格式化为标准格式
    return ':'.join(mac_clean[i:i+2] for i in range(0, 12, 2)).upper()


if __name__ == "__main__":
    # 测试
    mac = get_mac_address()
    print(f"本机MAC地址: {mac}")

