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


def plot_all_points(trend_path):
    conflict_trends = []
    with open(trend_path, 'rb') as f:
        conflict_trends = pickle.load(f)

    # 创建图形和轴
    fig, ax = plt.subplots(dpi=1000)
    plt.grid(True)

    # 绘制折线图
    y_axis_types = ['files_cnt_conflict', 'loc_conflict', 'chunks_cnt_conflict']
    colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
    for i in range(len(y_axis_types)):
        y_axis_type = y_axis_types[i]
        for trend in conflict_trends:
            ax.plot(list(range(len(trend))), [data[y_axis_type] for data in trend], colors[i], label=y_axis_type)

    ax.legend()
    plt.title('Conflict lines trend')
    # 添加标题和标签
    plt.xlabel('Commits')


if __name__ == '__main__':
    plot_all_points('trends/gradle_x_axis_datetime.pkl', 'datetime')
    plot_all_points('trends/gradle_x_axis_datetime.pkl', 'commit_index')
    plot_all_points('trends/gradle_x_axis_lines.pkl', 'lines')
    plot_all_points('trends/gradle_x_axis_files.pkl', 'files')
