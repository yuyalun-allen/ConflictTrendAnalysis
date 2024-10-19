import time
import json
import datetime
import logging

from tqdm import tqdm
import git
from git import Repo


def get_conflict_commits(repo_name):
    # 初始化Git仓库对象
    repo = Repo(f"cases/{repo_name}")
    repo.git.reset('--hard')
    repo.git.checkout('main')

    conflict_commits = []
    conflict_commits_num = 0
    all_commits = list(repo.iter_commits())

    # 遍历所有提交
    start = time.time()

    for commit in tqdm(all_commits, desc="Commits"):
        # 保持工作区干净
        repo.git.reset('--hard')
        # 检查提交是否存在合并冲突
        if len(commit.parents) != 2:
            continue

        if check_conflict_commit(repo, commit.parents[0], commit.parents[1]):
            conflict_commits.append({
                "commit_hash": commit.hexsha,
                "commit_message": commit.message
            })
            conflict_commits_num += 1
            logging.info(f"Conflict commit: {commit.hexsha}")
            logging.info(f"Conflict message: {commit.message}")
    
    end = time.time()
    logging.info(f"Total conflict commits: {conflict_commits_num}")
    logging.info(f"Total extract time: {end-start} s")
    with open(f"commits/conflict_commits_{repo_name}.json", "w", encoding="utf-8") as f:
        json.dump(conflict_commits, f, indent=2)


def check_conflict_commit(repo, commit_a, commit_b):
    try:
        if repo.is_dirty():
            raise Exception("Repository has uncommitted changes. Please commit or stash them.")
        # 检出到提交 A
        repo.git.checkout(commit_a)
        # 尝试合并提交 B
        repo.git.merge(commit_b, no_commit=True)
        # 如果合并成功，不会抛出异常，返回 False
        return False
    except git.exc.GitCommandError as e:
        if "CONFLICT" in str(e):
            # 如果合并失败，捕获异常并返回 True
            return True
        else:
            return False


if __name__ == '__main__':
    now = datetime.datetime.now()
    logging.basicConfig(level=logging.INFO,
                        handlers=[
                        logging.FileHandler(f'log/output-{now.day}-{now.hour}-{now.minute}.log'),
                    ])
    repo = "rails"
    get_conflict_commits(repo)