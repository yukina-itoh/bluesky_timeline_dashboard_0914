import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import glob

# ページ全体のレイアウトを広く設定
st.set_page_config(page_title="投稿数ダッシュボード", layout="wide")

@st.cache_data
def load_data():
    # 1. どこにCSVがあっても自動で探し出す処理
    possible_paths = [
        "dataset_0914/dataset_0914.csv",
        "dataset_0914.csv",
        "light_dataset.csv"
    ]
    
    found_file = None
    for path in possible_paths:
        if os.path.exists(path):
            found_file = path
            break
            
    if not found_file:
        files = glob.glob("dataset_0914/*.csv")
        if files:
            found_file = files[0]
            
    if not found_file:
        return pd.DataFrame()

    # 2. データの読み込み
    df = pd.read_csv(found_file, encoding='utf-8')

    # 3. 列名の自動判定（'投稿日時' になっているケースに対応）
    date_col = None
    if '投稿日時' in df.columns:
        date_col = '投稿日時'
    elif 'created_at' in df.columns:
        date_col = 'created_at'
    else:
        st.error(f"CSV内に日時の列が見つかりません。現在の列名: {list(df.columns)}")
        return pd.DataFrame()

    # 日時データへの変換と整理
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    valid_data = df.dropna(subset=[date_col]).copy()
    
    valid_data.set_index(date_col, inplace=True)
    valid_data.sort_index(inplace=True)
    return valid_data

def main():
    st.title("データセット投稿数ダッシュボード")

    # データの読み込み
    df = load_data()

    if df.empty:
        st.error("CSVファイルが見つからない、もしくは読み込めませんでした。GitHubの構成を確認してください。")
        return

    min_date = df.index.min().date()
    max_date = df.index.max().date()

    # --- 左側サイドバー（操作パネル） ---
    st.sidebar.header("表示設定")

    freq_dict = {"日別": "D", "週別": "W-MON", "月別": "MS"}
    selected_freq = st.sidebar.radio("時系列グラフの集計単位", list(freq_dict.keys()))
    freq_code = freq_dict[selected_freq]

    date_range = st.sidebar.slider(
        "表示期間を絞り込む",
        min_value=min_date, max_value=max_date,
        value=(min_date, max_date), format="YYYY-MM-DD"
    )

    # --- データのフィルタリング ---
    start_date, end_date = date_range
    mask = (df.index.date >= start_date) & (df.index.date <= end_date)
    filtered_df = df.loc[mask]

    # --- 上部：統計情報 ---
    st.subheader(f"📊 {selected_freq}の統計 ({start_date} 〜 {end_date})")
    counts = filtered_df.resample(freq_code).size().reset_index(name='投稿数')
    counts.rename(columns={df.index.name: 'date'}, inplace=True)

    if not counts.empty:
        max_val, min_val, avg_val = counts['投稿数'].max(), counts['投稿数'].min(), counts['投稿数'].mean()
    else:
        max_val = min_val = avg_val = 0

    col1, col2, col3 = st.columns(3)
    col1.metric(label="最大投稿数", value=f"{max_val} 件")
    col2.metric(label="最小投稿数", value=f"{min_val} 件")
    col3.metric(label="平均投稿数", value=f"{avg_val:.1f} 件")

    st.markdown("---")

    # --- 中部：時系列グラフ ---
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=counts['date'], y=counts['投稿数'],
        name=selected_freq, marker_color='#1f77b4'
    ))
    fig_bar.update_layout(
        title=f"投稿数の推移（{selected_freq}）",
        template='plotly_white', xaxis_title="年月日", yaxis_title="投稿件数",
        margin=dict(l=0, r=0, t=40, b=0)
    )
    st.plotly_chart(fig_bar, width='stretch')

    st.markdown("---")

    # --- 下部：時間帯・曜日別のヒートマップ ---
    st.subheader("🔥 曜日・時間帯別の傾向（ヒートマップ）")
    
    # ヒートマップ用の集計
    heatmap_df = filtered_df.copy()
    heatmap_df['曜日'] = heatmap_df.index.strftime('%A')
    heatmap_df['時間'] = heatmap_df.index.hour
    
    # 英語の曜日を日本語に変換
    day_map = {'Monday': '月', 'Tuesday': '火', 'Wednesday': '水', 'Thursday': '木', 'Friday': '金', 'Saturday': '土', 'Sunday': '日'}
    heatmap_df['曜日'] = heatmap_df['曜日'].map(day_map)
    
    heatmap_data = heatmap_df.groupby(['曜日', '時間']).size().reset_index(name='投稿数')
    pivot_data = heatmap_data.pivot(index='曜日', columns='時間', values='投稿数').fillna(0)
    
    # 曜日の順番と、24時間すべての列を整える
    days_ja = ['月', '火', '水', '木', '金', '土', '日']
    pivot_data = pivot_data.reindex(days_ja).fillna(0)
    for h in range(24):
        if h not in pivot_data.columns:
            pivot_data[h] = 0
    pivot_data = pivot_data[range(24)]
    
    # グラフの描画
    fig_heat = px.imshow(
        pivot_data,
        labels=dict(x="時間帯（時）", y="曜日", color="投稿数"),
        x=pivot_data.columns,
        y=pivot_data.index,
        color_continuous_scale="Blues", # 色合い（Reds や Viridis などにも変更可能）
        aspect="auto"
    )
    fig_heat.update_layout(template='plotly_white', margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_heat, width='stretch')

if __name__ == '__main__':
    main()
