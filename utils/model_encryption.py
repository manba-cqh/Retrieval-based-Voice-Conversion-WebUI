"""
模型文件加密工具模块

在模型文件（pth和index）头部添加加密标识数据，使文件无法被直接使用。
读取时自动检测并跳过加密头部，实现对加密和非加密文件的兼容。

加密格式:
- MAGIC (8 bytes): b'RVCENC01' 魔数标识
- PADDING_SIZE (4 bytes): uint32 little-endian, 填充数据大小
- RANDOM_PADDING (N bytes): 随机填充数据
- ORIGINAL_DATA: 原始文件数据
"""

import os
import io
import struct
import tempfile
from typing import Union, BinaryIO, Optional, Tuple

# 魔数标识
MAGIC_BYTES = b'RVCENC01'
MAGIC_SIZE = 8
PADDING_SIZE_BYTES = 4
HEADER_SIZE = MAGIC_SIZE + PADDING_SIZE_BYTES

# 默认填充大小（可配置）
DEFAULT_PADDING_SIZE = 256


def generate_random_padding(size: int = DEFAULT_PADDING_SIZE) -> bytes:
    """生成随机填充数据"""
    return os.urandom(size)


def encrypt_file(input_path: str, output_path: Optional[str] = None, 
                 padding_size: int = DEFAULT_PADDING_SIZE) -> str:
    """
    加密模型文件（在头部添加加密标识和随机填充）
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径，如果为None则覆盖原文件
        padding_size: 随机填充数据大小
        
    Returns:
        输出文件路径
    """
    if output_path is None:
        output_path = input_path
    
    # 读取原始数据
    with open(input_path, 'rb') as f:
        original_data = f.read()
    
    # 检查是否已经加密
    if is_encrypted_data(original_data):
        print(f"文件已加密，跳过: {input_path}")
        return output_path
    
    # 生成加密头部
    padding = generate_random_padding(padding_size)
    header = MAGIC_BYTES + struct.pack('<I', padding_size) + padding
    
    # 写入加密文件
    # 如果输出路径与输入路径相同，使用临时文件
    if output_path == input_path:
        dir_name = os.path.dirname(input_path)
        with tempfile.NamedTemporaryFile(mode='wb', dir=dir_name, delete=False) as tmp:
            tmp.write(header)
            tmp.write(original_data)
            tmp_path = tmp.name
        
        # 替换原文件
        os.replace(tmp_path, output_path)
    else:
        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(original_data)
    
    return output_path


def decrypt_file(input_path: str, output_path: Optional[str] = None) -> str:
    """
    解密模型文件（移除头部加密标识）
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径，如果为None则覆盖原文件
        
    Returns:
        输出文件路径
    """
    if output_path is None:
        output_path = input_path
    
    with open(input_path, 'rb') as f:
        data = f.read()
    
    # 检查是否加密
    if not is_encrypted_data(data):
        print(f"文件未加密，跳过: {input_path}")
        return output_path
    
    # 解析头部，获取原始数据偏移量
    offset = get_data_offset(data)
    original_data = data[offset:]
    
    # 写入解密文件
    if output_path == input_path:
        dir_name = os.path.dirname(input_path)
        with tempfile.NamedTemporaryFile(mode='wb', dir=dir_name, delete=False) as tmp:
            tmp.write(original_data)
            tmp_path = tmp.name
        
        os.replace(tmp_path, output_path)
    else:
        with open(output_path, 'wb') as f:
            f.write(original_data)
    
    return output_path


def is_encrypted_data(data: bytes) -> bool:
    """检查数据是否包含加密头部"""
    if len(data) < HEADER_SIZE:
        return False
    return data[:MAGIC_SIZE] == MAGIC_BYTES


def is_encrypted_file(file_path: str) -> bool:
    """检查文件是否加密"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(HEADER_SIZE)
        return is_encrypted_data(header)
    except Exception:
        return False


def get_data_offset(data: bytes) -> int:
    """
    获取原始数据在加密文件中的偏移量
    
    Args:
        data: 文件数据（至少包含头部）
        
    Returns:
        原始数据起始偏移量
    """
    if not is_encrypted_data(data):
        return 0
    
    # 解析padding大小
    padding_size = struct.unpack('<I', data[MAGIC_SIZE:HEADER_SIZE])[0]
    return HEADER_SIZE + padding_size


def get_file_data_offset(file_path: str) -> int:
    """
    获取文件中原始数据的偏移量
    
    Args:
        file_path: 文件路径
        
    Returns:
        原始数据起始偏移量
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(HEADER_SIZE)
            if not is_encrypted_data(header):
                return 0
            
            padding_size = struct.unpack('<I', header[MAGIC_SIZE:HEADER_SIZE])[0]
            return HEADER_SIZE + padding_size
    except Exception:
        return 0


def read_decrypted_data(file_path: str) -> bytes:
    """
    读取解密后的文件数据（自动跳过加密头部）
    
    Args:
        file_path: 文件路径
        
    Returns:
        解密后的原始数据
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    
    offset = get_data_offset(data)
    return data[offset:]


def create_decrypted_file_object(file_path: str) -> io.BytesIO:
    """
    创建一个包含解密数据的BytesIO对象
    
    Args:
        file_path: 文件路径
        
    Returns:
        包含解密数据的BytesIO对象
    """
    data = read_decrypted_data(file_path)
    return io.BytesIO(data)


def encrypt_model_files_in_directory(directory: str, 
                                      extensions: Tuple[str, ...] = ('.pth', '.index'),
                                      padding_size: int = DEFAULT_PADDING_SIZE) -> int:
    """
    加密目录中所有指定扩展名的模型文件
    
    Args:
        directory: 目录路径
        extensions: 要加密的文件扩展名元组
        padding_size: 随机填充数据大小
        
    Returns:
        加密的文件数量
    """
    count = 0
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(extensions):
                file_path = os.path.join(root, filename)
                try:
                    if not is_encrypted_file(file_path):
                        encrypt_file(file_path, padding_size=padding_size)
                        print(f"已加密: {file_path}")
                        count += 1
                except Exception as e:
                    print(f"加密失败 {file_path}: {e}")
    
    return count


# ==================== PyTorch 加载支持 ====================

def load_torch_model(file_path: str, map_location=None):
    """
    加载（可能加密的）PyTorch模型文件
    
    自动检测文件是否加密，如果加密则跳过头部读取原始数据
    
    Args:
        file_path: pth文件路径
        map_location: torch.load的map_location参数
        
    Returns:
        加载的模型数据
    """
    import torch
    
    if is_encrypted_file(file_path):
        # 加密文件：读取解密数据后加载
        buffer = create_decrypted_file_object(file_path)
        return torch.load(buffer, map_location=map_location)
    else:
        # 未加密文件：直接加载
        return torch.load(file_path, map_location=map_location)


# ==================== FAISS Index 加载支持 ====================

def load_faiss_index(file_path: str):
    """
    加载（可能加密的）FAISS index文件
    
    自动检测文件是否加密，如果加密则跳过头部读取原始数据
    
    Args:
        file_path: index文件路径
        
    Returns:
        加载的FAISS index对象
    """
    import faiss
    
    if is_encrypted_file(file_path):
        # 加密文件：需要写入临时文件后加载（faiss.read_index不支持BytesIO）
        data = read_decrypted_data(file_path)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.index', delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        
        try:
            index = faiss.read_index(tmp_path)
        finally:
            # 删除临时文件
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        
        return index
    else:
        # 未加密文件：直接加载
        return faiss.read_index(file_path)


# ==================== 命令行工具 ====================

if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='模型文件加密/解密工具')
    parser.add_argument('action', choices=['encrypt', 'decrypt', 'check'],
                       help='操作类型: encrypt=加密, decrypt=解密, check=检查是否加密')
    parser.add_argument('path', help='文件或目录路径')
    parser.add_argument('--padding', type=int, default=DEFAULT_PADDING_SIZE,
                       help=f'填充数据大小（默认{DEFAULT_PADDING_SIZE}字节）')
    parser.add_argument('--output', '-o', help='输出路径（仅对单文件有效）')
    
    args = parser.parse_args()
    
    if args.action == 'check':
        if os.path.isfile(args.path):
            encrypted = is_encrypted_file(args.path)
            print(f"{args.path}: {'已加密' if encrypted else '未加密'}")
        elif os.path.isdir(args.path):
            for root, dirs, files in os.walk(args.path):
                for f in files:
                    if f.lower().endswith(('.pth', '.index')):
                        file_path = os.path.join(root, f)
                        encrypted = is_encrypted_file(file_path)
                        print(f"{file_path}: {'已加密' if encrypted else '未加密'}")
    
    elif args.action == 'encrypt':
        if os.path.isfile(args.path):
            encrypt_file(args.path, args.output, args.padding)
            print(f"已加密: {args.path}")
        elif os.path.isdir(args.path):
            count = encrypt_model_files_in_directory(args.path, padding_size=args.padding)
            print(f"共加密 {count} 个文件")
    
    elif args.action == 'decrypt':
        if os.path.isfile(args.path):
            decrypt_file(args.path, args.output)
            print(f"已解密: {args.path}")
        elif os.path.isdir(args.path):
            count = 0
            for root, dirs, files in os.walk(args.path):
                for f in files:
                    if f.lower().endswith(('.pth', '.index')):
                        file_path = os.path.join(root, f)
                        if is_encrypted_file(file_path):
                            decrypt_file(file_path)
                            print(f"已解密: {file_path}")
                            count += 1
            print(f"共解密 {count} 个文件")
