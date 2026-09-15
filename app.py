import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# ページ全体のレイアウトを広く設定
st.set_page_config(
    page_title="投稿数ダッシュボード",
    layout="wide"
)


@st.cache_data
def load_data():
    FILE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "dataset_0914",
        "dataset_0914.csv"
    )

    DATE_COLUMN = "投稿日時"

    # CSVが存在するか確認
    if not os.path.isfile(FILE_PATH):
        st.error(f"CSVファイルが見つかりません: {FILE_PATH}")
        return pd.DataFrame()

    # CSV読み込み
    df = pd.read_csv(
        FILE_PATH,
        encoding="utf-8"
    )

    # 「投稿日時」を日時型に変換
    df[DATE_COLUMN] = pd.to_datetime(
        df[DATE_COLUMN],
        errors="coerce"
    )

    # 日時変換できなかった行を削除
    df = df.dropna(
        subset=[DATE_COLUMN]
    )

    # 投稿日時をインデックスに設定
    df = df.set_index(DATE_COLUMN)

    # 日時順に並べ替え
    df = df.sort_index()

    return df


def main():

    st.title("データセット投稿数ダッシュボード")

    # データ読み込み
    df = load_data()

    if df.empty:
        st.error("データが読み込めませんでした。")
        return

    # 全期間の最小・最大日付
    min_date = df.index.min().date()
    max_date = df.index.max().date()

    # --------------------------------
    # サイドバー
    # --------------------------------

    st.sidebar.header("表示設定")

    # 集計単位
    freq_dict = {
        "日別": "D",
        "週別": "W-MON",
        "月別": "MS"
    }

    selected_freq = st.sidebar.radio(
        "集計単位を選択",
        list(freq_dict.keys())
    )

    freq_code = freq_dict[selected_freq]

    # 期間指定
    date_range = st.sidebar.slider(
        "表示期間を絞り込む",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )

    # --------------------------------
    # データの絞り込み
    # --------------------------------

    start_date, end_date = date_range

    mask = (
        (df.index.date >= start_date) &
        (df.index.date <= end_date)
    )

    filtered_df = df.loc[mask]

    # --------------------------------
    # 投稿数を集計
    # --------------------------------

    counts = (
        filtered_df
        .resample(freq_code)
        .size()
        .reset_index(name="投稿数")
    )

    counts.rename(
        columns={df.index.name: "date"},
        inplace=True
    )

    # --------------------------------
    # 統計
    # --------------------------------

    if not counts.empty:

        max_val = counts["投稿数"].max()
        min_val = counts["投稿数"].min()
        avg_val = counts["投稿数"].mean()

    else:

        max_val = 0
        min_val = 0
        avg_val = 0

    # --------------------------------
    # 統計表示
    # --------------------------------

    st.subheader(
        f"📊 {selected_freq}の統計 "
        f"({start_date} 〜 {end_date})"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "最大投稿数",
        f"{max_val:,} 件"
    )

    col2.metric(
        "最小投稿数",
        f"{min_val:,} 件"
    )

    col3.metric(
        "平均投稿数",
        f"{avg_val:,.1f} 件"
    )

    st.markdown("---")

    # --------------------------------
    # グラフ
    # --------------------------------

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=counts["date"],
            y=counts["投稿数"],
            name=selected_freq,
            marker_color="#1f77b4"
        )
    )

    fig.update_layout(
        title=f"投稿数の推移（{selected_freq}）",
        template="plotly_white",
        xaxis_title="年月日",
        yaxis_title="投稿件数",
        margin=dict(
            l=0,
            r=0,
            t=40,
            b=0
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


if __name__ == "__main__":
    main()
