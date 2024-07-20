import pickle

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def plot_trend_by_datetime(segments, counts):
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


def plot_all_points(trend_path, x_axis_type):
    conflict_trends = []
    x_axis = []
    counts = []
    with open(trend_path, 'rb') as f:
        conflict_trends = pickle.load(f)

    # 创建图形和轴
    fig, ax = plt.subplots(dpi=1000)
    plt.grid(True)

    # 绘制折线图
    if x_axis_type == 'datetime':
        for trend in conflict_trends:
            x_axis.extend(trend['x_axis'])
            counts.extend(trend['counts'])
        ax.scatter(x_axis, counts, color='blue', marker='o')
        plt.title('Conflict lines trend')

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        fig.autofmt_xdate()

        # 添加标题和标签
        plt.xlabel('Datetime')
        plt.ylabel('Conflict lines')

    elif x_axis_type == 'commit_index':
        for trend in conflict_trends:
            x_axis.extend(range(len(trend['x_axis'])))
            counts.extend(trend['counts'])
        ax.plot(x_axis, counts, color='blue', marker='o')
        plt.title('Conflict lines trend')

        # 添加标题和标签
        plt.xlabel('Commits')
        plt.ylabel('Conflict lines')

    elif x_axis_type == 'lines':
        for trend in conflict_trends:
            x_axis_accumulate = [0]
            for x in trend['x_axis'][1:]:
                x_axis_accumulate.append(x + x_axis_accumulate[-1])
            x_axis.extend(x_axis_accumulate)
            counts.extend(trend['counts'])
        ax.scatter(x_axis, counts, color='blue', marker='o')
        plt.title('Conflict lines trend')

        # 添加标题和标签
        plt.xlabel('Changed lines')
        plt.ylabel('Conflict lines')

    elif x_axis_type == 'files':
        for trend in conflict_trends:
            changed_files = set()
            changed_files_count = [0]
            for x in trend['x_axis'][1:]:
                changed_files = changed_files.union(x)
                changed_files_count.append(len(changed_files))
            x_axis.extend(changed_files_count)
            counts.extend(trend['counts'])
        ax.scatter(x_axis, counts, color='blue', marker='o')
        plt.title('Conflict files trend')

        # 添加标题和标签
        plt.xlabel('Changed files')
        plt.ylabel('Conflict files')

    plt.savefig(f"graphs/{trend_path.split('/')[1].split('_')[0]}/conflict_lines_trend_{x_axis_type}.png")

if __name__ == '__main__':
    plot_all_points('trends/tensorflow_x_axis_datetime.pkl', 'datetime')
    plot_all_points('trends/tensorflow_x_axis_datetime.pkl', 'commit_index')
    plot_all_points('trends/tensorflow_x_axis_lines.pkl', 'lines')
    plot_all_points('trends/tensorflow_x_axis_files.pkl', 'files')
