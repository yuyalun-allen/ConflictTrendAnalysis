import json
import datetime
import os
import tempfile
import subprocess
import logging
import pickle

from tqdm import tqdm
from git import Repo
from git import IndexFile


def get_all_trend(repo_path: str, x_axis_type: str, y_axis_type: str):
    repo_name = repo_path.split('/')[-1]
    with open(f"commits/conflict_commits_{repo_name}.json", "r", encoding="utf-8") as f:
        conflict_commits = json.load(f)
        # conflict_commits = conflict_commits[:int(len(conflict_commits)/100)]
    
    conflict_trends = []
    for c in tqdm(conflict_commits):
        try:
            data_list = get_conflict_trend(repo_path, c["commit_hash"])
        except Exception as e:
            logging.error(f"Error in {c['commit_hash']}")
            logging.error(e)
            continue

        conflict_trends.append({
            'commit_hash': c['commit_hash'],
            'trends': data_list
        })
    
    with open(f'trends/{repo_name}.pkl', 'wb') as f:
        pickle.dump(conflict_trends, f)


def get_conflict_trend(repo_path, conflict_commit_hash):
    repo = Repo(repo_path)

    conflict_commit = repo.commit(conflict_commit_hash)
    base_commit = repo.merge_base(conflict_commit.parents[0], conflict_commit.parents[1])[0]
    commits1, commits2 = get_commit_lists(conflict_commit, base_commit)

    data_list = []

    cur_commit_branch1 = base_commit
    cur_commit_branch2 = base_commit
    commit_index_branch1 = 0
    commit_index_branch2 = 0
    loc_change_branch1 = 0
    loc_change_branch2 = 0
    files_change_branch1 = set()
    files_change_branch2 = set()
    commiters_branch1 = set()
    commiters_branch2 = set()
    commiters_merge = set()


    def extract_commmit_data(commit_time, ours_commit, theirs_commit, commit_branch):
        nonlocal commit_index_branch1
        nonlocal commit_index_branch2
        nonlocal loc_change_branch1
        nonlocal loc_change_branch2
        nonlocal files_change_branch1
        nonlocal files_change_branch2
        nonlocal commiters_branch1
        nonlocal commiters_branch2
        nonlocal commiters_merge

        data = {}
        data['datetime'] = commit_time
        data['commit_ours'] = ours_commit.hexsha
        data['commit_theirs'] = theirs_commit.hexsha
        files, loc = get_commit_changes(ours_commit)
        if commit_branch == 1:
            files_change_branch1 = files.union(files_change_branch1)
            commiters_branch1.add(ours_commit.author)
            loc_change_branch1 += loc
            commit_index_branch1 += 1

            data['commits_index_ours'] = commit_index_branch1
            data['commits_index_theirs'] = commit_index_branch2
            data['loc_ours'] = loc_change_branch1
            data['loc_theirs'] = loc_change_branch2
            data['files_cnt_ours'] = len(files_change_branch1)
            data['files_cnt_theirs'] = len(files_change_branch2)
            data['commiters_cnt_ours'] = len(commiters_branch1)
            data['commiters_cnt_theirs'] = len(commiters_branch2)
        else:
            files_change_branch2 = files.union(files_change_branch2)
            commiters_branch2.add(ours_commit.author)
            loc_change_branch2 += loc
            commit_index_branch2 += 1

            data['commits_index_ours'] = commit_index_branch2
            data['commits_index_theirs'] = commit_index_branch1
            data['loc_ours'] = loc_change_branch2
            data['loc_theirs'] = loc_change_branch1
            data['files_cnt_ours'] = len(files_change_branch2)
            data['files_cnt_theirs'] = len(files_change_branch1)
            data['commiters_cnt_ours'] = len(commiters_branch2)
            data['commiters_cnt_theirs'] = len(commiters_branch1)

        files_merge = files_change_branch1.union(files_change_branch2)
        commiters_merge = commiters_branch1.union(commiters_branch2)
        data['files_cnt_merge'] = len(files_merge)
        data['commiters_cnt_merge'] = len(commiters_merge)
        data['loc_merge'] = loc_change_branch1 + loc_change_branch2
    
        return data


    # commit index (i.e. data index in data_list) as time series' index
    data = {}

    # Dependent Var
    data['files_cnt_conflict'] = 0
    data['loc_conflict'] = 0
    data['chunks_cnt_conflict'] = 0

    # Independent Var
    data['datetime'] = base_commit.committed_datetime.astimezone(datetime.timezone.utc)
    data['commit_ours'] = base_commit.hexsha
    data['commit_theirs'] = base_commit.hexsha

    data['commits_index_ours'] = 0
    data['commits_index_theirs'] = 0
    data['files_cnt_ours'] = 0
    data['files_cnt_theirs'] = 0
    data['files_cnt_merge'] = 0
    data['loc_ours'] = 0
    data['loc_theirs'] = 0
    data['loc_merge'] = 0
    data['commiters_cnt_ours'] = 0
    data['commiters_cnt_theirs'] = 0
    data['commiters_cnt_merge'] = 0

    data_list.append(data)
    # Similar to merge algorithem in merge sort.
    while len(commits1) != 0 and len(commits2) != 0:
        if commits1[-1]["time"] < commits2[-1]["time"]:
            c = commits1.pop()
            cur_commit_branch1 = c["commit"] 
            data = extract_commmit_data(c['time'], cur_commit_branch1, cur_commit_branch2, 1)
        else:
            c = commits2.pop()
            cur_commit_branch2 = c["commit"]
            data = extract_commmit_data(c['time'], cur_commit_branch2, cur_commit_branch1, 2)
        get_conflict_data(repo, base_commit, cur_commit_branch1, cur_commit_branch2, data)
        data_list.append(data)


    if len(commits1) != 0:
        for c in reversed(commits1):
            cur_commit_branch1 = c["commit"]
            data = extract_commmit_data(c['time'], cur_commit_branch1, cur_commit_branch2, 1)
            get_conflict_data(repo, base_commit, cur_commit_branch1, cur_commit_branch2, data)
            data_list.append(data)

    if len(commits2) != 0:
        for c in reversed(commits2):
            cur_commit_branch2 = c["commit"]
            data = extract_commmit_data(c['time'], cur_commit_branch2, cur_commit_branch1, 2)
            get_conflict_data(repo, base_commit, cur_commit_branch1, cur_commit_branch2, data)
            data_list.append(data.copy())
    logging.info(f"Conflict commit: {conflict_commit_hash}")
    logging.info(f"Data list: {data_list}")
    return data_list


def get_conflict_data(repo, base_commit, cur_commit_branch1, cur_commit_branch2, data: dict):
    merge_commit = IndexFile.from_tree(repo, base_commit, cur_commit_branch1, cur_commit_branch2)
    data['files_cnt_conflict'] = len(get_conflict_files(merge_commit))
    data['loc_conflict'], data['chunks_cnt_conflict'] = get_conflict_lines_count(repo, merge_commit)


def get_conflict_lines_count(repo: Repo, conflict_index_files: IndexFile):
    conflict_files = get_conflict_files(conflict_index_files)
    conflict_lines_count = 0
    chunk_count = 0

    if not conflict_files:
        return conflict_lines_count, chunk_count
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
                chunk_count += 1
                start = index
            elif line.startswith('>>>>>>>'):
                end = index
                conflict_lines_count += end - start + 1
    return conflict_lines_count, chunk_count
        

def get_commit_changes(commit):
    changed_files = set()
    added_lines = 0
    deleted_lines = 0

    # 遍历提交的diff
    for diff in commit.diff(commit.parents[0], create_patch=True):
        changed_files.add(diff.a_path) 
        if diff.b_path:
            changed_files.add(diff.b_path)
        for line in diff.diff.decode('utf-8').splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                added_lines += 1
            elif line.startswith('-') and not line.startswith('---'):
                deleted_lines += 1

    return changed_files, added_lines+deleted_lines


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
                        logging.FileHandler(f'log/output-{now.day}-{now.hour}-{now.minute}.log'),
                    ])
    repo = "rails"
    # get_conflict_commits(repo)
    # filter_conflict_commits("tensorflow")
    # filter_conflict_commits("gradle")
    # filter_conflict_commits("linux")
    # tasks = [
    #     (f'cases/{repo}', 'datetime'),
    #     (f'cases/{repo}', 'lines'),
    #     (f'cases/{repo}', 'files'),
    # ]
    
    # # 创建进程池
    # with multiprocessing.Pool(processes=3) as pool:
    #     # 使用 starmap 方法并行执行函数
    #     pool.starmap(get_all_trend, tasks)
    get_all_trend(f'cases/{repo}', 'datetime', 'lines')