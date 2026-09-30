#!/usr/bin/env python3
# 鸣儿检索链路调试 · 服务器 JS 文件精确补丁工具
# 解决「Edit 工具大块改动会部分回滚」坑：用 Python io 读写做精确字符串替换 + 备份 + 断言校验。
# 用法（服务器上）：
#   python3 patch_server_file.py <file> <old> <new> [--backup /tmp/bakN.js] [--assert-old]
# 例：
#   python3 patch_server_file.py /www/wwwroot/hndcw.com/src/agent/index.js \
#     '    if (_secFromText) f.sector = String(a.sector || _secFromText);' \
#     '    f.sector = _secFromText;' --backup /tmp/bak5_index.js --assert-old
import sys, os, shutil

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        print("USAGE: patch_server_file.py <file> <old> <new> [--backup PATH] [--assert-old]"); sys.exit(2)
    path, old, new = args[0], args[1], args[2]
    backup = None; assert_old = False
    i = 3
    while i < len(args):
        if args[i] == '--backup' and i+1 < len(args): backup = args[i+1]; i += 2
        elif args[i] == '--assert-old': assert_old = True; i += 1
        else: i += 1
    if not os.path.exists(path):
        print("ERR: file not found:", path); sys.exit(1)
    s = open(path, encoding='utf-8').read()
    if assert_old and old not in s:
        print("ASSERT FAIL: OLD string not found in", path); sys.exit(1)
    if old not in s:
        print("WARN: OLD not found, no change"); return
    if backup:
        shutil.copy2(path, backup); print("BACKUP ->", backup)
    s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
    print("PATCHED OK; new present:", new in s, "| old gone:", old not in s)

if __name__ == '__main__':
    main()
