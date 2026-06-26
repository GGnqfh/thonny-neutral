#!/usr/bin/env python3
"""
自动同步上游并清理乌克兰相关内容的脚本。
由 Hermes cron 定期执行。
同步后如检测到上游新版本，自动打 tag 触发 GitHub Actions 构建安装包。
"""

import subprocess
import sys
import os
import re

REPO_DIR = "/home/crazy/thonny"
UPSTREAM = "https://github.com/thonny/thonny.git"
BRANCH = "master"

def run(cmd, check=True):
    """执行命令并返回(returncode, stdout)"""
    result = subprocess.run(
        cmd, shell=True, cwd=REPO_DIR, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"❌ 命令失败: {cmd}")
        print(f"   stdout: {result.stdout.strip()}")
        print(f"   stderr: {result.stderr.strip()}")
        sys.exit(1)
    return result.returncode, result.stdout.strip()

def get_version():
    """读取当前版本号"""
    version_file = os.path.join(REPO_DIR, "thonny/VERSION")
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            return f.read().strip()
    return None

def sync_upstream():
    """同步上游仓库"""
    print("🔄 正在同步上游...")

    # 确保在正确的分支
    run(f"git checkout {BRANCH}")

    # 添加上游远程（如果不存在）
    _, remotes = run("git remote -v")
    if "upstream" not in remotes:
        run(f"git remote add upstream {UPSTREAM}")

    # 记录当前 HEAD
    _, old_head = run("git rev-parse HEAD")

    # 拉取上游
    run("git fetch upstream --tags")

    # 合并上游 master
    rc, _ = run("git merge upstream/master --no-edit", check=False)
    if rc != 0:
        # 有冲突，放弃合并
        run("git merge --abort", check=False)
        print("⚠️ 合并冲突，已放弃。需要手动处理。")
        return False, False

    # 检查是否有新提交
    _, new_head = run("git rev-parse HEAD")
    had_updates = old_head != new_head

    print("✅ 上游同步完成")
    return True, had_updates

def clean_ukraine_content():
    """清理所有乌克兰相关内容"""
    print("🧹 正在清理乌克兰相关内容...")
    changes_made = False

    # 1. 删除乌克兰国旗图片文件
    ukraine_files = [
        "thonny/res/Ukraine.png",
        "thonny/res/Ukraine_2x.png",
        "thonny/res/_disabled_Ukraine.png",
        "thonny/res/_disabled_Ukraine_2x.png",
        "thonny/plugins/pi/res/Ukraine.png",
        "thonny/plugins/pi/res/Ukraine48.png",
    ]
    for f in ukraine_files:
        filepath = os.path.join(REPO_DIR, f)
        if os.path.exists(filepath):
            run(f"git rm -f {f}")
            print(f"   删除: {f}")
            changes_made = True

    # 2. 清理 README.rst
    readme_path = os.path.join(REPO_DIR, "README.rst")
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        content = content.replace(
            ".. image:: https://github.com/thonny/thonny/blob/master/thonny/res/Ukraine.png\n\n",
            ""
        )
        content = content.replace(
            '`Support Ukraine! <https://github.com/thonny/thonny/wiki/Support-Ukraine>`_\n\n',
            ""
        )

        if content != original:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            run("git add README.rst")
            print("   清理: README.rst")
            changes_made = True

    # 3. 清理 workbench.py
    workbench_path = os.path.join(REPO_DIR, "thonny/workbench.py")
    if os.path.exists(workbench_path):
        with open(workbench_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        content = re.sub(
            r'\n    def _support_ukraine\(self.*?\n(?:        .*?\n)*',
            '\n',
            content
        )
        content = re.sub(
            r'\n    def _init_support_ukraine_bar\(self.*?\n(?:        .*?\n)*',
            '\n',
            content
        )
        content = re.sub(
            r'\n            "SupportUkraine",\n(?:.*\n)*?image="Ukraine",\n',
            '\n',
            content
        )
        content = content.replace(
            "self._init_support_ukraine_bar()",
            "# self._init_support_ukraine_bar()  # removed Ukraine support"
        )

        if content != original:
            with open(workbench_path, 'w', encoding='utf-8') as f:
                f.write(content)
            run("git add thonny/workbench.py")
            print("   清理: thonny/workbench.py")
            changes_made = True

    # 4. 清理 plugins/pi/__init__.py 中的 Ukraine 映射
    pi_path = os.path.join(REPO_DIR, "thonny/plugins/pi/__init__.py")
    if os.path.exists(pi_path):
        with open(pi_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        lines = content.split('\n')
        new_lines = [l for l in lines if '"Ukraine"' not in l and "'Ukraine'" not in l]

        if len(new_lines) != len(lines):
            with open(pi_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            run("git add thonny/plugins/pi/__init__.py")
            print("   清理: thonny/plugins/pi/__init__.py")
            changes_made = True

    return changes_made

def commit_and_push():
    """提交并推送"""
    _, status = run("git status --porcelain")
    if not status:
        print("📝 没有需要提交的变更")
        return False

    run("git add -A")
    run('git commit -m "chore: remove Ukraine flag solidarity patch (non-functional change)"')
    rc, _ = run(f"git push origin {BRANCH}", check=False)
    if rc != 0:
        print("⚠️ 推送失败，可能需要先 pull")
        run(f"git pull --rebase origin {BRANCH}", check=False)
        run(f"git push origin {BRANCH}", check=False)
    else:
        print("✅ 已推送到 origin")
    return True

def tag_and_trigger_build():
    """打 tag 并触发 GitHub Actions 构建"""
    version = get_version()
    if not version:
        print("⚠️ 无法读取版本号，跳过构建触发")
        return

    tag = f"v{version}"

    # 检查 tag 是否已存在
    _, existing = run(f"git tag -l {tag}", check=False)
    if existing.strip() == tag:
        print(f"📝 Tag {tag} 已存在，跳过")
        return

    # 打 tag 并推送
    run(f'git tag {tag}')
    run(f"git push origin {tag}", check=False)
    print(f"🏷️ 已打 tag {tag}，GitHub Actions 将自动开始构建")

def main():
    print("=" * 50)
    print("Thonny 仓库自动同步 & 清理")
    print("=" * 50)

    # 同步上游
    sync_ok, had_updates = sync_upstream()
    if not sync_ok:
        return

    # 清理乌克兰内容
    clean_ukraine_content()

    # 提交推送
    pushed = commit_and_push()

    # 如果有更新（来自上游同步或清理），触发构建
    if had_updates or pushed:
        tag_and_trigger_build()

    print("=" * 50)
    print("🎉 完成!")
    print("=" * 50)

if __name__ == "__main__":
    main()
