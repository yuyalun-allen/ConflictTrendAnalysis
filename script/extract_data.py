import time
import json
import datetime
import os
import tempfile
import subprocess
import logging

from tqdm import tqdm
from git import Repo
from git import IndexFile
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def get_conflict_commits(repo_name):
    # 初始化Git仓库对象
    repo = Repo(f"cases/{repo_name}")
    conflict_commits = []
    conflict_commits_num = 0

    # 遍历所有提交
    start = time.time()

    for commit in tqdm(repo.iter_commits(), desc="Commits"):
        # 检查提交是否存在合并冲突
        if len(commit.parents) != 2:
            continue
        try:
            base = repo.merge_base(commit.parents[0], commit.parents[1])[0]
        except:
            continue
        virtual_merge = IndexFile.from_tree(repo, base, commit.parents[0], commit.parents[1])

        if len(get_conflict_files(virtual_merge)) > 0:
            conflict_commits.append({
                "commit_hash": commit.hexsha,
                "commit_message": commit.message
            })
            conflict_commits_num += 1
            logging.info(f"Conflict commit: {commit.hexsha}")
    
    end = time.time()
    print(f"Total conflict commits: {conflict_commits_num}")
    print(f"Total extract time: {end-start} s")
    with open(f"conflict_commits_{repo_name}.json", "w", encoding="utf-8") as f:
        json.dump(conflict_commits, f, indent=2)


def get_conflict_lines_trend(repo_path, conflict_commit_hash):
    repo = Repo(repo_path)
    conflict_commit = repo.commit(conflict_commit_hash)
    base_commit = repo.merge_base(conflict_commit.parents[0], conflict_commit.parents[1])[0]
    commits1, commits2 = get_commit_lists(conflict_commit, base_commit)

    cur_commit_branch1 = base_commit
    cur_commit_branch2 = base_commit
    counts = [0]
    segments = [base_commit.committed_datetime.astimezone(datetime.timezone.utc)]
    # Similar to merge algorithem in merge sort.
    while len(commits1) != 0 and len(commits2) != 0:
        if commits1[-1]["time"] < commits2[-1]["time"]:
            segments.append(commits1[-1]["time"])
            cur_commit_branch1 = commits1.pop()["commit"]
        else:
            segments.append(commits2[-1]["time"])
            cur_commit_branch2 = commits2.pop()["commit"]
        # 计算当前时间点的冲突行数
        merge_commit = IndexFile.from_tree(repo, base_commit, cur_commit_branch1, cur_commit_branch2)
        conflict_lines_count = get_conflict_lines_count(repo, merge_commit)
        counts.append(conflict_lines_count)
    if len(commits1) != 0:
        for c in reversed(commits1):
            segments.append(c["time"])
            cur_commit_branch1 = c["commit"]
            merge_commit = IndexFile.from_tree(repo, base_commit, cur_commit_branch1, cur_commit_branch2)
            conflict_lines_count = get_conflict_lines_count(repo, merge_commit)
            counts.append(conflict_lines_count)
    if len(commits2) != 0:
        for c in reversed(commits2):
            segments.append(c["time"])
            cur_commit_branch2 = c["commit"]
            merge_commit = IndexFile.from_tree(repo, base_commit, cur_commit_branch1, cur_commit_branch2)
            conflict_lines_count = get_conflict_lines_count(repo, merge_commit)
            counts.append(conflict_lines_count)
    return segments, counts


def plot_trend(segments, counts):
    # 创建图形和轴
    fig, ax = plt.subplots(dpi=100)

    # 绘制折线图
    ax.plot(segments, counts, marker='o')

    # 设置日期格式
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))

    # 自动旋转日期标签
    fig.autofmt_xdate()

    # 添加标题和标签
    plt.title('Conflict lines trend')
    plt.xlabel('Datetime')
    plt.ylabel('Conflict lines')

    # 显示网格
    plt.grid(True)

    # 显示图形
    plt.savefig("graphs/conflict_lines_trend.png")


def get_conflict_lines_count(repo: Repo, conflict_index_files: IndexFile):
    conflict_files = get_conflict_files(conflict_index_files)
    conflict_lines_count = 0

    if not conflict_files:
        return conflict_lines_count
    # 生成冲突标记的文件内容
    for _, stages in conflict_files.items():
        if len(stages) != 3:
            continue  # 需要三个阶段的条目

        base_sha = stages[1]
        ours_sha = stages[2]
        theirs_sha = stages[3]

        base_content = read_blob_content(repo, base_sha)
        ours_content = read_blob_content(repo, ours_sha)
        theirs_content = read_blob_content(repo, theirs_sha)
        
        conflict_content = merge_files("".join(base_content), "".join(ours_content), "".join(theirs_content))
        if not conflict_content:
            continue

        start, end = 0, -1
        
        for index, line in enumerate(conflict_content.splitlines()):
            if line.startswith('<<<<<<<'):
                start = index
            elif line.startswith('>>>>>>>'):
                end = index
                conflict_lines_count += end - start + 1
    return conflict_lines_count
        

def get_conflict_files(conflict_index_files: IndexFile):
    conflicted_files = {}
    for entry in conflict_index_files.entries.values():
        if entry.stage == 0:
            continue

        if entry.path not in conflicted_files:
            conflicted_files[entry.path] = {}

        conflicted_files[entry.path][entry.stage] = entry.hexsha
    return conflicted_files


def read_blob_content(repo, sha):
    """Read the content of a blob by its SHA-1 and return it as a list of lines."""
    blob = repo.git.cat_file('blob', sha)
    return blob.splitlines(keepends=True)


def merge_files(base_file, ours_file, theirs_file) -> str:
    with tempfile.TemporaryDirectory() as tempdir:
        # Create temporary files for base, ours, and theirs
        base_path = os.path.join(tempdir, 'base')
        ours_path = os.path.join(tempdir, 'ours')
        theirs_path = os.path.join(tempdir, 'theirs')

        # Write contents to temporary files
        with open(base_path, 'w') as f:
            f.write(base_file)
        with open(ours_path, 'w') as f:
            f.write(ours_file)
        with open(theirs_path, 'w') as f:
            f.write(theirs_file)

        try:
        # Use git merge-file to merge the files
            return subprocess.run(['git', 'merge-file', '-p', ours_path, base_path, theirs_path], 
                            check=True, 
                            text=True,
                            capture_output=True).stdout

        except subprocess.CalledProcessError as e:
            return e.stdout


def get_commit_lists(conflict_commit, base_commit) -> tuple[list, list]:
    commit_list_1 = dfs_commits(conflict_commit.parents[0], base_commit)
    commit_list_2 = dfs_commits(conflict_commit.parents[1], base_commit)
    return commit_list_1, commit_list_2


def dfs_commits(commit, base):
    # 初始化栈和访问列表
    stack = [(commit, 
              [{"commit": commit, 
                "time": commit.committed_datetime.astimezone(datetime.timezone.utc)}]
        )]
    visited = set()

    while stack:
        current_commit, path = stack.pop()

        # 如果找到了 base 提交，则返回路径
        if current_commit == base:
            return path

        # 标记当前提交为已访问
        if current_commit.hexsha not in visited:
            visited.add(current_commit.hexsha)

            # 将父提交添加到栈中
            for parent in current_commit.parents:
                if parent.hexsha not in visited:
                    stack.append((parent, path + [{
                        "commit": parent, 
                        "time": parent.committed_datetime.astimezone(datetime.timezone.utc)
                        }]))

    # 如果没有找到路径，返回空列表
    return []


if __name__ == '__main__':
    now = datetime.datetime.now()
    logging.basicConfig(level=logging.INFO,
                        handlers=[
                        logging.FileHandler(f'output-{now.day}-{now.hour}-{now.minute}.log'),
                        logging.StreamHandler()
                    ])
    # get_conflict_commits("rails")

    repo_path = "cases/rails"
    # conflict_commmits = []
    # with open("conflict_commits_rails_filtered.json", "r", encoding="utf-8") as f:
    #     conflict_commits = json.load(f)
    
    # for index, c in enumerate(conflict_commits):
    #     logging.info(f'######\ncommit {c["commit_hash"]}: ')
    #     get_conflict_lines_trend(repo_path, c["commit_hash"])

    segments, counts = get_conflict_lines_trend(repo_path, "8898a0ae2a0d5c8826fe08bbf4ccd10745802f9e")
    plot_trend(segments, counts)