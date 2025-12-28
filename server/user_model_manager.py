"""用户可用模型管理工具 - 命令行脚本"""
import sys
import os
import argparse

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.database import SessionLocal, init_db
from server.models import User, Model
from server.config import settings


def list_users(limit=100):
    """列出所有用户"""
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
        
        if not users:
            print("没有找到用户")
            return
        
        print(f"\n{'='*100}")
        print(f"{'ID':<5} {'用户名':<20} {'手机号':<15} {'可用模型数':<12} {'MAC地址':<20} {'创建时间':<20}")
        print(f"{'-'*100}")
        
        for user in users:
            model_count = len(user.get_available_model_uids()) if user.available_models else 0
            phone = user.phone if user.phone else "-"
            mac = user.mac if user.mac else "-"
            created_at = user.created_at.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"{user.id:<5} {user.username:<20} {phone:<15} {model_count:<12} {mac:<20} {created_at:<20}")
        
        print(f"{'='*100}")
        print(f"总计: {len(users)} 个用户")
        
    finally:
        db.close()


def list_models(limit=100):
    """列出所有模型"""
    db = SessionLocal()
    try:
        models = db.query(Model).order_by(Model.created_at.desc()).limit(limit).all()
        
        if not models:
            print("没有找到模型")
            return
        
        print(f"\n{'='*120}")
        print(f"{'ID':<5} {'UID':<40} {'模型名称':<30} {'分类':<15} {'价格':<10} {'创建时间':<20}")
        print(f"{'-'*120}")
        
        for model in models:
            category = model.category if model.category else "-"
            created_at = model.created_at.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"{model.id:<5} {model.uid:<40} {model.name:<30} {category:<15} {model.price:<10.2f} {created_at:<20}")
        
        print(f"{'='*120}")
        print(f"总计: {len(models)} 个模型")
        
    finally:
        db.close()


def get_user_models(username=None, user_id=None):
    """获取用户的可用模型列表"""
    db = SessionLocal()
    try:
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
        elif username:
            user = db.query(User).filter(User.username == username).first()
        else:
            print("错误: 必须提供用户名或用户ID")
            return
        
        if not user:
            print(f"错误: 用户不存在")
            return
        
        model_uids = user.get_available_model_uids()
        
        if not model_uids:
            print(f"\n用户 '{user.username}' (ID: {user.id}) 没有可用模型")
            return
        
        print(f"\n{'='*120}")
        print(f"用户: {user.username} (ID: {user.id})")
        print(f"{'-'*120}")
        print(f"{'序号':<5} {'模型UID':<40} {'模型名称':<30} {'分类':<15} {'价格':<10}")
        print(f"{'-'*120}")
        
        for idx, uid in enumerate(model_uids, 1):
            model = db.query(Model).filter(Model.uid == uid).first()
            if model:
                category = model.category if model.category else "-"
                print(f"{idx:<5} {model.uid:<40} {model.name:<30} {category:<15} {model.price:<10.2f}")
            else:
                print(f"{idx:<5} {uid:<40} {'(模型不存在)':<30} {'-':<15} {'-':<10}")
        
        print(f"{'='*120}")
        print(f"总计: {len(model_uids)} 个可用模型")
        
    finally:
        db.close()


def add_model_to_user(username=None, user_id=None, model_uid=None):
    """为用户添加可用模型"""
    db = SessionLocal()
    try:
        # 查找用户
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
        elif username:
            user = db.query(User).filter(User.username == username).first()
        else:
            print("错误: 必须提供用户名或用户ID")
            return False
        
        if not user:
            print(f"错误: 用户不存在")
            return False
        
        # 验证模型是否存在
        if model_uid:
            model = db.query(Model).filter(Model.uid == model_uid.strip()).first()
            if not model:
                print(f"错误: 模型UID '{model_uid}' 不存在")
                return False
        
        # 添加模型
        if user.add_available_model(model_uid.strip()):
            db.commit()
            model = db.query(Model).filter(Model.uid == model_uid.strip()).first()
            print(f"✓ 成功为用户 '{user.username}' 添加模型: {model.name} (UID: {model_uid})")
            return True
        else:
            print(f"警告: 模型 '{model_uid}' 已经存在于用户的可用模型列表中")
            return False
        
    except Exception as e:
        db.rollback()
        print(f"错误: 添加模型失败 - {e}")
        return False
    finally:
        db.close()


def remove_model_from_user(username=None, user_id=None, model_uid=None):
    """移除用户的可用模型"""
    db = SessionLocal()
    try:
        # 查找用户
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
        elif username:
            user = db.query(User).filter(User.username == username).first()
        else:
            print("错误: 必须提供用户名或用户ID")
            return False
        
        if not user:
            print(f"错误: 用户不存在")
            return False
        
        # 移除模型
        if user.remove_available_model(model_uid.strip()):
            db.commit()
            print(f"✓ 成功从用户 '{user.username}' 移除模型: {model_uid}")
            return True
        else:
            print(f"警告: 模型 '{model_uid}' 不在用户的可用模型列表中")
            return False
        
    except Exception as e:
        db.rollback()
        print(f"错误: 移除模型失败 - {e}")
        return False
    finally:
        db.close()


def clear_user_models(username=None, user_id=None):
    """清空用户的所有可用模型"""
    db = SessionLocal()
    try:
        # 查找用户
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
        elif username:
            user = db.query(User).filter(User.username == username).first()
        else:
            print("错误: 必须提供用户名或用户ID")
            return False
        
        if not user:
            print(f"错误: 用户不存在")
            return False
        
        model_count = len(user.get_available_model_uids()) if user.available_models else 0
        
        if model_count == 0:
            print(f"警告: 用户 '{user.username}' 没有可用模型")
            return False
        
        user.available_models = None
        db.commit()
        
        print(f"✓ 成功清空用户 '{user.username}' 的所有可用模型（共 {model_count} 个）")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"错误: 清空模型失败 - {e}")
        return False
    finally:
        db.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="用户可用模型管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有用户
  python user_model_manager.py list-users
  
  # 列出所有模型
  python user_model_manager.py list-models
  
  # 查看用户的可用模型
  python user_model_manager.py get-models --username testuser
  python user_model_manager.py get-models --user-id 1
  
  # 为用户添加模型
  python user_model_manager.py add --username testuser --model-uid "model-uuid-123"
  python user_model_manager.py add --user-id 1 --model-uid "model-uuid-123"
  
  # 移除用户的模型
  python user_model_manager.py remove --username testuser --model-uid "model-uuid-123"
  
  # 清空用户的所有模型
  python user_model_manager.py clear --username testuser
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # list-users 命令
    list_users_parser = subparsers.add_parser('list-users', help='列出所有用户')
    list_users_parser.add_argument('--limit', type=int, default=100, help='限制显示数量（默认100）')
    
    # list-models 命令
    list_models_parser = subparsers.add_parser('list-models', help='列出所有模型')
    list_models_parser.add_argument('--limit', type=int, default=100, help='限制显示数量（默认100）')
    
    # get-models 命令
    get_models_parser = subparsers.add_parser('get-models', help='获取用户的可用模型列表')
    get_models_group = get_models_parser.add_mutually_exclusive_group(required=True)
    get_models_group.add_argument('--username', help='用户名')
    get_models_group.add_argument('--user-id', type=int, help='用户ID')
    
    # add 命令
    add_parser = subparsers.add_parser('add', help='为用户添加可用模型')
    add_group = add_parser.add_mutually_exclusive_group(required=True)
    add_group.add_argument('--username', help='用户名')
    add_group.add_argument('--user-id', type=int, help='用户ID')
    add_parser.add_argument('--model-uid', required=True, help='模型UID')
    
    # remove 命令
    remove_parser = subparsers.add_parser('remove', help='移除用户的可用模型')
    remove_group = remove_parser.add_mutually_exclusive_group(required=True)
    remove_group.add_argument('--username', help='用户名')
    remove_group.add_argument('--user-id', type=int, help='用户ID')
    remove_parser.add_argument('--model-uid', required=True, help='模型UID')
    
    # clear 命令
    clear_parser = subparsers.add_parser('clear', help='清空用户的所有可用模型')
    clear_group = clear_parser.add_mutually_exclusive_group(required=True)
    clear_group.add_argument('--username', help='用户名')
    clear_group.add_argument('--user-id', type=int, help='用户ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 初始化数据库（确保表存在）
    try:
        init_db()
    except Exception as e:
        print(f"警告: 数据库初始化失败 - {e}")
    
    # 执行命令
    if args.command == 'list-users':
        list_users(limit=args.limit)
    elif args.command == 'list-models':
        list_models(limit=args.limit)
    elif args.command == 'get-models':
        get_user_models(username=args.username, user_id=args.user_id)
    elif args.command == 'add':
        add_model_to_user(username=args.username, user_id=args.user_id, model_uid=args.model_uid)
    elif args.command == 'remove':
        remove_model_from_user(username=args.username, user_id=args.user_id, model_uid=args.model_uid)
    elif args.command == 'clear':
        clear_user_models(username=args.username, user_id=args.user_id)


if __name__ == "__main__":
    main()

