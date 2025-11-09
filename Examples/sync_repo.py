"""
Git 仓库自动同步工具
需要安装依赖库: pip install -U schedule GitPython
"""
import os
import schedule
import time
from git import Repo
from git.exc import GitCommandError


# 设置 GitHub 和 GitCode 的仓库 URL
gitcode_repo_url = "https://gitcode.com/xxxxxxxxx/xxxxxxxxxxx.git"
github_repo_url = "https://github.com/xxxxxxxxxxx/xxxxxxxxxxx.git"

# GitHub Personal Access Token (PAT), 请替换为你自己的。
github_pat = "gxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 本地仓库路径
local_repo_path = "./xxxxxxxxxxxxxx"


def sync_repo():
    # 克隆仓库到本地（如果仓库已存在, 则会跳过）
    if not os.path.exists(local_repo_path):
        print("克隆 GitCode 仓库到本地...")
        Repo.clone_from(gitcode_repo_url, local_repo_path)
    else:
        print("仓库已存在, 拉取最新代码...")
        repo = Repo(local_repo_path)
        origin = repo.remotes.origin
        origin.pull()

    # 初始化 Git LFS 支持（得确保 Git LFS 已经安装）
    os.system("git lfs install")

    # 获取本地仓库
    repo = Repo(local_repo_path)

    # 配置 GitHub 远程仓库和身份认证
    try:
        origin = repo.create_remote("github", github_repo_url)
    except GitCommandError:
        origin = repo.remotes.github

    # 设置一下认证信息（使用 PAT）
    origin.set_url(
        f"https://{github_pat}:x-oauth-basic@github.com/xxxxxxxxxxxxxxx/xxxxxxxxxxxxx.git"
    )

    # 推送到 GitHub 代码仓库
    print("推送到 GitHub...")
    origin.push(refspec="master")

    print("同步完成！")


# 设置定时同步任务（例如每 120s 同步一次）
schedule.every(120).seconds.do(sync_repo)

# 初次同步
sync_repo()

whether_schedule = False
# 进入定时循环, 保持脚本运行。
while whether_schedule:
    schedule.run_pending()
    time.sleep(10)
