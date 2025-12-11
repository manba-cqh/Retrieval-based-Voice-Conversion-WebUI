"""工具函数"""
import hashlib
import os
from typing import Optional


def calculate_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_file_size(file_path: str) -> int:
    """获取文件大小（字节）"""
    return os.path.getsize(file_path)


def ensure_directory_exists(directory: str):
    """确保目录存在"""
    os.makedirs(directory, exist_ok=True)

