import os
import sys
import sqlite3
import hashlib
import secrets

# Safe UTF-8 console output for Windows GBK environment
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Locate user.db in backend or current folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DB_PATH = os.path.join(BASE_DIR, "backend", "user.db")
if not os.path.exists(USER_DB_PATH):
    USER_DB_PATH = os.path.join(BASE_DIR, "user.db")

def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return key.hex(), salt

def main():
    print("\n" + "=" * 55)
    print(" [Key] JavDB AutoSpider 管理员密码重置与安全救急工具")
    print("=" * 55)
    
    if not os.path.exists(USER_DB_PATH):
        print(f"[-] 未检测到数据库路径 ({USER_DB_PATH})。")
        print("[!] 直接打开 Web 界面即可进行首次管理员账号密码初始化。")
        return

    print("\n请选择您需要的救急操作:")
    print("  [1] 直接修改已有管理员账号的密码")
    print("  [2] 重置清空数据库用户表 (恢复为网页首次部署初始化状态)")
    print("  [3] 退出")
    
    try:
        choice = input("\n[>] 请输入选项编号 (1/2/3): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n操作已取消")
        return
    
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    
    if choice == "1":
        username = input("请输入需要修改密码的用户名 [默认: admin]: ").strip() or "admin"
        new_pwd = input(f"请输入 [{username}] 的新密码 (至少 4 位): ").strip()
        if len(new_pwd) < 4:
            print("[-] 新密码长度必须至少 4 个字符！操作已取消。")
            conn.close()
            return
        
        p_hash, salt = hash_password(new_pwd)
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if row:
            cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE username = ?", (p_hash, salt, username))
            cursor.execute("DELETE FROM sessions WHERE username = ?", (username,))
            conn.commit()
            print(f"\n[+] [成功] 已将管理员用户 [{username}] 的密码重置！关联 Session 已失效，请前往网页直接登录。")
        else:
            cursor.execute("INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)", (username, p_hash, salt))
            conn.commit()
            print(f"\n[+] [成功] 已全新创建管理员账号 [{username}] 并设置密码！")
            
    elif choice == "2":
        confirm = input("[!] 确认要清空 user.db 中的所有用户与 Session 记录吗？(y/N): ").strip().lower()
        if confirm == 'y':
            cursor.execute("DELETE FROM users")
            cursor.execute("DELETE FROM sessions")
            conn.commit()
            print("\n[+] [成功] 已彻底清空 user.db 用户表！刷新 Web 页面将重新展示首次部署设置密码界面。")
        else:
            print("操作已取消。")
    else:
        print("已退出密码重置工具。")
        
    conn.close()

if __name__ == "__main__":
    main()
