"""
Git 仓库自动同步工具
依赖: pip install -U schedule GitPython
"""

import os
import sys
import time
import logging
import schedule
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError


class GitRepoSyncer:
    """Git 仓库同步器"""

    def __init__(self, config: dict):
        """
        初始化同步器

        Args:
            config: 配置字典, 包含以下键: 
                - source_repo_url: 源仓库 URL
                - target_repo_url: 目标仓库 URL
                - target_repo_token: 目标仓库认证令牌
                - local_repo_path: 本地仓库路径
                - branch: 分支名 (默认: "master")
        """
        self.config = config
        self.setup_logging()

    def setup_logging(self):
        """配置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("repo_sync.log"),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def get_authenticated_url(self, repo_url: str, token: str) -> str:
        """生成带认证的仓库 URL"""
        if "github.com" in repo_url:
            return repo_url.replace("https://", f"https://{token}:x-oauth-basic@")
        elif "gitcode.com" in repo_url:
            return repo_url.replace("https://", f"https://oauth2:{token}@")
        else:
            return repo_url

    def ensure_local_repo(self) -> Repo:
        """确保本地仓库存在且最新"""
        local_path = self.config["local_repo_path"]

        try:
            if not os.path.exists(local_path):
                self.logger.info(f"克隆仓库到本地: {local_path}")
                repo = Repo.clone_from(self.config["source_repo_url"], local_path)
                self.logger.info("仓库克隆成功")
            else:
                self.logger.info("拉取最新代码...")
                repo = Repo(local_path)

                # 检查是否为有效的 Git 仓库
                if not repo.bare:
                    origin = repo.remotes.origin
                    origin.pull()
                    self.logger.info("代码仓库拉取成功")
                else:
                    raise InvalidGitRepositoryError("无效的 Git 代码仓库")

            return repo

        except (GitCommandError, InvalidGitRepositoryError) as e:
            self.logger.error(f"本地仓库操作失败: {e}")
            raise

    def setup_git_lfs(self, repo: Repo):
        """设置 Git LFS"""
        try:
            # 检查 Git LFS 是否可用
            result = os.system("git lfs version")
            if result != 0:
                self.logger.warning("Git LFS 未安装, 跳过 LFS 设置")
                return

            # 在仓库中初始化 LFS
            with repo.git.custom_environment(GIT_WORK_TREE=repo.working_dir):
                repo.git.lfs("install", "--local")
            self.logger.info("Git LFS 设置完成")

        except Exception as e:
            self.logger.warning(f"Git LFS 设置失败: {e}")

    def sync_to_target(self, repo: Repo):
        """同步到目标仓库"""
        target_remote_name = "target"
        target_url = self.get_authenticated_url(
            self.config["target_repo_url"], self.config["target_repo_token"]
        )

        try:
            # 配置目标远程仓库
            if target_remote_name in [remote.name for remote in repo.remotes]:
                target_remote = repo.remotes[target_remote_name]
                target_remote.set_url(target_url)
            else:
                target_remote = repo.create_remote(target_remote_name, target_url)

            self.logger.info("开始推送到目标仓库...")

            # 推送到目标仓库
            push_result = target_remote.push(
                refspec=f"{self.config['branch']}:{self.config['branch']}"
            )

            if push_result and any(
                result.flags & result.ERROR for result in push_result
            ):
                self.logger.error("推送失败")
                for result in push_result:
                    if result.flags & result.ERROR:
                        self.logger.error(f"推送错误: {result.summary}")
                raise GitCommandError("push", "推送失败")
            else:
                self.logger.info("同步完成! ")

        except GitCommandError as e:
            self.logger.error(f"同步失败: {e}")
            raise

    def sync(self):
        """执行完整的同步流程"""
        try:
            self.logger.info("开始同步流程...")

            # 1. 确保本地仓库最新
            repo = self.ensure_local_repo()

            # 2. 设置 Git LFS
            self.setup_git_lfs(repo)

            # 3. 同步到目标仓库
            self.sync_to_target(repo)

        except Exception as e:
            self.logger.error(f"同步过程出错: {e}")
            raise


def load_config() -> dict:
    """从环境变量加载配置"""
    config = {
        "source_repo_url": os.getenv(
            "SOURCE_REPO_URL", "https://gitcode.com/Ascend/MindSpeed.git"
        ),
        "target_repo_url": os.getenv(
            "TARGET_REPO_URL", "https://github.com/verylucky01/MindSpeed.git"
        ),
        "target_repo_token": os.getenv("TARGET_REPO_TOKEN"),
        "local_repo_path": os.getenv("LOCAL_REPO_PATH", "./MindSpeed"),
        "branch": os.getenv("REPO_BRANCH", "master"),
        "sync_interval": int(os.getenv("SYNC_INTERVAL", "60")),
    }

    # 验证必要配置
    if not config["target_repo_token"]:
        raise ValueError("必须设置 TARGET_REPO_TOKEN 环境变量")

    return config


def main():
    """主函数"""
    try:
        config = load_config()
        syncer = GitRepoSyncer(config)

        # 立即执行一次同步
        syncer.sync()

        # 设置定时任务 - sync_interval 是间隔多少秒
        if config.get("enable_schedule", True):
            interval = config["sync_interval"]
            schedule.every(interval).seconds.do(syncer.sync)

            logger = logging.getLogger(__name__)
            logger.info(f"定时同步已启动, 间隔: {interval} 秒")

            # 保持运行
            while True:
                schedule.run_pending()
                time.sleep(10)

    except KeyboardInterrupt:
        logging.info("同步程序被用户中断")
    except Exception as e:
        logging.error(f"程序运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
