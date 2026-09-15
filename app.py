import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import glob
import os

# ページ全体のレイアウトを広く設定
st.set_page_config(page_title="投稿数ダッシュボード", layout="wide")

# @st.cache_data をつけると、毎回CSVを読み込み直さずキャッシュを利用するため動作が高速になります
@st.cache_data
@st.cache_data
def load_data():
    FILE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'dataset_0914',
        'dataset_0914.csv'
    )

    st.write("CSVパス:", FILE_PATH)
    st.write("ファイル存在:", os.path.isfile(FILE_PATH))

    # ファイルサイズ
    file_size = os.path.getsize(FILE_PATH)
    st.write("ファイルサイズ:", file_size, "bytes")

    # CSVを直接読み込む
    df = pd.read_csv(FILE_PATH, encoding='utf-8')

    st.write("DataFrameのshape:", df.shape)
    st.write("列名:", df.columns.tolist())
    st.write("先頭5行:")
    st.dataframe(df.head())

    return df
    files = glob.glob(os.path.join(TARGET_DIR))
    if not files:
        return pd.DataFrame()

    df_list = []
    for file in files:
        df = pd.read_csv(file, encoding='utf-8')
        df_list.append(df)

    all_data = pd.concat(df_list, ignore_index=True)
    all_data[DATE_COLUMN] = pd.to_datetime(all_data[DATE_COLUMN], errors='coerce')
    valid_data = all_data.dropna(subset=[DATE_COLUMN]).copy()

    # 日時をインデックスに設定して並び替え
    valid_data.set_index(DATE_COLUMN, inplace=True)
    valid_data.sort_index(inplace=True)
    return valid_data

def main():
    st.title("データセット投稿数ダッシュボード")

    # データの読み込み
    df = load_data()

    if df.empty:
        return

    # 全期間の最小・最大日付を取得
    min_date = df.index.min().date()
    max_date = df.index.max().date()

    # --- 左側サイドバー（操作パネル） ---
    st.sidebar.header("表示設定")

    # 1. 集計単位の切り替え
    freq_dict = {"日別": "D", "週別": "W-MON", "月別": "MS"}  # MSは月初の意味
    selected_freq = st.sidebar.radio("集計単位を選択", list(freq_dict.keys()))
    freq_code = freq_dict[selected_freq]

    # 2. 期間指定スライダー
    date_range = st.sidebar.slider(
        "表示期間を絞り込む",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )

    # --- データのフィルタリングと再計算 ---
    start_date, end_date = date_range
    # 選択された期間でデータを絞り込み
    mask = (df.index.date >= start_date) & (df.index.date <= end_date)
    filtered_df = df.loc[mask]

    # 絞り込んだデータに対して指定の単位で集計
    counts = filtered_df.resample(freq_code).size().reset_index(name='投稿数')
    counts.rename(columns={df.index.name: 'date'}, inplace=True)

    # 絞り込んだ範囲内での統計を計算
    if not counts.empty:
        max_val = counts['投稿数'].max()
        min_val = counts['投稿数'].min()
        avg_val = counts['投稿数'].mean()
    else:
        max_val = min_val = avg_val = 0

    # --- メイン画面（右側）の表示 ---
    st.subheader(f"📊 {selected_freq}の統計 ({start_date} 〜 {end_date})")

    # 3つの指標を横並びで表示
    col1, col2, col3 = st.columns(3)
    col1.metric(label="最大投稿数", value=f"{max_val} 件")
    col2.metric(label="最小投稿数", value=f"{min_val} 件")
    col3.metric(label="平均投稿数", value=f"{avg_val:.1f} 件")

    st.markdown("---")

    # Plotlyグラフの描画
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=counts['date'],
        y=counts['投稿数'],
        name=selected_freq,
        marker_color='#1f77b4'
    ))

    fig.update_layout(
        title=f"投稿数の推移（{selected_freq}）",
        template='plotly_white',
        xaxis_title="年月日",
        yaxis_title="投稿件数",
        margin=dict(l=0, r=0, t=40, b=0) # グラフの余白を調整
    )

    # Streamlit上にPlotlyグラフを表示
    st.plotly_chart(fig, use_container_width=True)

if __name__ == '__main__':
    main()
