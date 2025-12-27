"""邀请码管理工具 - 命令行脚本"""
import sys
import os
import argparse
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.database import SessionLocal, init_db
from server.models import InvitationCode
from server.config import settings


def list_codes(used_only=False, unused_only=False, limit=100):
    """列出邀请码"""
    db = SessionLocal()
    try:
        query = db.query(InvitationCode)
        
        if used_only:
            query = query.filter(InvitationCode.is_used == True)
        elif unused_only:
            query = query.filter(InvitationCode.is_used == False)
        
        codes = query.order_by(InvitationCode.created_at.desc()).limit(limit).all()
        
        if not codes:
            print("没有找到邀请码")
            return
        
        print(f"\n{'='*80}")
        print(f"{'ID':<5} {'邀请码':<20} {'状态':<10} {'使用人ID':<10} {'使用时间':<20} {'创建时间':<20}")
        print(f"{'-'*80}")
        
        for code in codes:
            status = "已使用" if code.is_used else "未使用"
            used_by = str(code.used_by) if code.used_by else "-"
            used_at = code.used_at.strftime("%Y-%m-%d %H:%M:%S") if code.used_at else "-"
            created_at = code.created_at.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"{code.id:<5} {code.code:<20} {status:<10} {used_by:<10} {used_at:<20} {created_at:<20}")
        
        print(f"{'='*80}")
        print(f"总计: {len(codes)} 条")
        
    finally:
        db.close()


def create_code(code, note=None):
    """创建邀请码"""
    db = SessionLocal()
    try:
        # 检查邀请码是否已存在
        existing = db.query(InvitationCode).filter(InvitationCode.code == code.strip()).first()
        if existing:
            print(f"错误: 邀请码 '{code}' 已存在")
            return False
        
        # 创建新邀请码
        invitation = InvitationCode(
            code=code.strip(),
            note=note,
            is_used=False
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        
        print(f"✓ 成功创建邀请码: {invitation.code}")
        if note:
            print(f"  备注: {note}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"错误: 创建邀请码失败 - {e}")
        return False
    finally:
        db.close()


def mark_used(code):
    """将邀请码标记为已使用"""
    db = SessionLocal()
    try:
        invitation = db.query(InvitationCode).filter(InvitationCode.code == code.strip()).first()
        
        if not invitation:
            print(f"错误: 邀请码 '{code}' 不存在")
            return False
        
        if invitation.is_used:
            print(f"警告: 邀请码 '{code}' 已经被使用")
            print(f"  使用人ID: {invitation.used_by}")
            print(f"  使用时间: {invitation.used_at}")
            return False
        
        invitation.is_used = True
        invitation.used_at = datetime.utcnow()
        db.commit()
        
        print(f"✓ 成功将邀请码 '{code}' 标记为已使用")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"错误: 标记失败 - {e}")
        return False
    finally:
        db.close()


def mark_unused(code):
    """将邀请码标记为未使用（取消使用）"""
    db = SessionLocal()
    try:
        invitation = db.query(InvitationCode).filter(InvitationCode.code == code.strip()).first()
        
        if not invitation:
            print(f"错误: 邀请码 '{code}' 不存在")
            return False
        
        if not invitation.is_used:
            print(f"警告: 邀请码 '{code}' 已经是未使用状态")
            return False
        
        invitation.is_used = False
        invitation.used_by = None
        invitation.used_at = None
        db.commit()
        
        print(f"✓ 成功将邀请码 '{code}' 标记为未使用")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"错误: 标记失败 - {e}")
        return False
    finally:
        db.close()


def delete_code(code):
    """删除邀请码"""
    db = SessionLocal()
    try:
        invitation = db.query(InvitationCode).filter(InvitationCode.code == code.strip()).first()
        
        if not invitation:
            print(f"错误: 邀请码 '{code}' 不存在")
            return False
        
        if invitation.is_used:
            print(f"警告: 邀请码 '{code}' 已被使用，无法删除")
            print(f"  使用人ID: {invitation.used_by}")
            print(f"  使用时间: {invitation.used_at}")
            return False
        
        db.delete(invitation)
        db.commit()
        
        print(f"✓ 成功删除邀请码: {code}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"错误: 删除失败 - {e}")
        return False
    finally:
        db.close()


def get_code(code):
    """获取指定邀请码信息"""
    db = SessionLocal()
    try:
        invitation = db.query(InvitationCode).filter(InvitationCode.code == code.strip()).first()
        
        if not invitation:
            print(f"错误: 邀请码 '{code}' 不存在")
            return False
        
        print(f"\n{'='*60}")
        print(f"邀请码信息")
        print(f"{'-'*60}")
        print(f"ID:           {invitation.id}")
        print(f"邀请码:       {invitation.code}")
        print(f"状态:         {'已使用' if invitation.is_used else '未使用'}")
        print(f"使用人ID:     {invitation.used_by if invitation.used_by else '-'}")
        print(f"使用时间:     {invitation.used_at.strftime('%Y-%m-%d %H:%M:%S') if invitation.used_at else '-'}")
        print(f"创建时间:     {invitation.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"创建者ID:     {invitation.created_by if invitation.created_by else '-'}")
        print(f"备注:         {invitation.note if invitation.note else '-'}")
        print(f"{'='*60}\n")
        
        return True
        
    finally:
        db.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="邀请码管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有邀请码
  python invitation_manager.py list
  
  # 列出未使用的邀请码
  python invitation_manager.py list --unused
  
  # 创建邀请码
  python invitation_manager.py create INVITE123 --note "测试邀请码"
  
  # 获取邀请码信息
  python invitation_manager.py get INVITE123
  
  # 标记邀请码为已使用
  python invitation_manager.py mark-used INVITE123
  
  # 标记邀请码为未使用
  python invitation_manager.py mark-unused INVITE123
  
  # 删除邀请码
  python invitation_manager.py delete INVITE123
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出邀请码')
    list_parser.add_argument('--used', action='store_true', help='只显示已使用的邀请码')
    list_parser.add_argument('--unused', action='store_true', help='只显示未使用的邀请码')
    list_parser.add_argument('--limit', type=int, default=100, help='限制显示数量（默认100）')
    
    # create 命令
    create_parser = subparsers.add_parser('create', help='创建邀请码')
    create_parser.add_argument('code', help='邀请码')
    create_parser.add_argument('--note', help='备注')
    
    # get 命令
    get_parser = subparsers.add_parser('get', help='获取邀请码信息')
    get_parser.add_argument('code', help='邀请码')
    
    # mark-used 命令
    mark_used_parser = subparsers.add_parser('mark-used', help='标记邀请码为已使用')
    mark_used_parser.add_argument('code', help='邀请码')
    
    # mark-unused 命令
    mark_unused_parser = subparsers.add_parser('mark-unused', help='标记邀请码为未使用')
    mark_unused_parser.add_argument('code', help='邀请码')
    
    # delete 命令
    delete_parser = subparsers.add_parser('delete', help='删除邀请码')
    delete_parser.add_argument('code', help='邀请码')
    
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
    if args.command == 'list':
        list_codes(used_only=args.used, unused_only=args.unused, limit=args.limit)
    elif args.command == 'create':
        create_code(args.code, args.note)
    elif args.command == 'get':
        get_code(args.code)
    elif args.command == 'mark-used':
        mark_used(args.code)
    elif args.command == 'mark-unused':
        mark_unused(args.code)
    elif args.command == 'delete':
        delete_code(args.code)


if __name__ == "__main__":
    main()

