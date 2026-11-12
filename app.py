import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Bluesky投稿数ダッシュボード", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
RAW_SUMMARY_CSV = BASE_DIR / "raw_daily_counts.csv"
PROCESSED_SUMMARY_CSV = BASE_DIR / "processed_daily_counts.csv"
DATE_COLUMN = "投稿日時"

@st.cache_data(show_spinner=False)
def daily_counts_from_csv(data: bytes):
    """投稿単位CSV、または date・投稿数 の日別集計CSVを読み込む。"""
    df = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", low_memory=False)

    if DATE_COLUMN in df.columns:
        dates = pd.to_datetime(df[DATE_COLUMN], errors="coerce", format="mixed")
        valid_dates = dates.dropna()
        daily = valid_dates.dt.normalize().value_counts().sort_index().astype("int64")
        invalid = len(df) - len(valid_dates)
    elif {"date", "投稿数"}.issubset(df.columns):
        dates = pd.to_datetime(df["date"], errors="coerce", format="mixed")
        counts = pd.to_numeric(df["投稿数"], errors="coerce")
        valid = dates.notna() & counts.notna() & (counts >= 0) & (counts % 1 == 0)
        if not valid.all():
            raise ValueError("集計CSVに不正な日付・投稿数があります。")
        daily = pd.Series(counts[valid].astype("int64").to_numpy(),
                          index=pd.DatetimeIndex(dates[valid].dt.normalize()))
        daily = daily.groupby(level=0).sum().sort_index()
        invalid = 0
    else:
        raise ValueError("「投稿日時」列、または「date」「投稿数」列が必要です。")

    daily.index = pd.DatetimeIndex(daily.index)
    daily.index.name = "date"
    if daily.empty:
        raise ValueError("有効な投稿日時がありません。")
    return daily, int(daily.sum()), invalid

def read_dataset(uploaded, default_path=None):
    if uploaded is not None:
        return daily_counts_from_csv(uploaded.getvalue()), f"アップロード: {uploaded.name}"
    if default_path is not None and default_path.is_file():
        return daily_counts_from_csv(default_path.read_bytes()), f"既定ファイル: {default_path.name}"
    return None, None

def main():
    st.title("📊 Bluesky 投稿数ダッシュボード")
    st.caption("2025年大阪・関西万博に関するBluesky投稿の比較（GitHub保存の10月31日版CSVを初期表示）")

    st.sidebar.header("データの指定")
    raw_upload = st.sidebar.file_uploader(
        "前処理前CSV（未指定ならGitHubの raw_daily_counts.csv）",
        type="csv", key="raw"
    )
    clean_upload = st.sidebar.file_uploader(
        "前処理後CSV（未指定ならGitHubの processed_daily_counts.csv）",
        type="csv", key="clean"
    )
    st.sidebar.caption(
        "アップロードしたファイルは現在のセッションの表示に使います。"
        "恒常的に公開する場合は、投稿本文を含まない日別集計CSV"
        "「processed_daily_counts.csv」をリポジトリに配置してください。"
    )

    try:
        raw_data, raw_source = read_dataset(raw_upload, RAW_SUMMARY_CSV)
        clean_data, clean_source = read_dataset(clean_upload, PROCESSED_SUMMARY_CSV)
    except Exception as exc:
        st.error(f"CSVの読み込みに失敗しました: {exc}")
        return

    if raw_data is None:
        st.error("前処理前の raw_daily_counts.csv が見つかりません。GitHubに保存するか、サイドバーからアップロードしてください。")
        return

    raw_daily, raw_total, raw_invalid = raw_data
    if clean_data is not None:
        clean_daily, clean_total, clean_invalid = clean_data
        min_date = min(raw_daily.index.min(), clean_daily.index.min()).date()
        max_date = max(raw_daily.index.max(), clean_daily.index.max()).date()
    else:
        clean_daily, clean_total, clean_invalid = None, None, 0
        min_date, max_date = raw_daily.index.min().date(), raw_daily.index.max().date()

    if raw_upload is None and clean_upload is None and clean_data is not None:
        st.success("GitHubに保存された前処理前・前処理後のCSVを読み込んでいます。")

    with st.expander("読み込みデータの確認"):
        st.write(f"前処理前：{raw_source} ／ {raw_total:,}件"
                 f"（{raw_daily.index.min().date()}〜{raw_daily.index.max().date()}）")
        if clean_data is not None:
            st.write(f"前処理後：{clean_source} ／ {clean_total:,}件"
                     f"（{clean_daily.index.min().date()}〜{clean_daily.index.max().date()}）")

    st.sidebar.header("表示設定")
    freq_options = {"日別": "D", "週別": "W-MON", "月別": "MS"}
    selected_freq = st.sidebar.radio("集計単位", list(freq_options), index=2)
    chart_kind = st.sidebar.radio("グラフ形式", ["棒グラフ", "折れ線グラフ"])
    if min_date < max_date:
        start_date, end_date = st.sidebar.slider(
            "表示期間", min_value=min_date, max_value=max_date,
            value=(min_date, max_date), format="YYYY-MM-DD"
        )
    else:
        start_date = end_date = min_date

    day_index = pd.date_range(start_date, end_date, freq="D")
    raw_period = raw_daily.reindex(day_index, fill_value=0).astype("int64")
    raw_counts = raw_period.resample(freq_options[selected_freq]).sum()
    raw_period_total = int(raw_period.sum())

    if clean_daily is not None:
        clean_period = clean_daily.reindex(day_index, fill_value=0).astype("int64")
        clean_counts = clean_period.resample(freq_options[selected_freq]).sum()
        clean_period_total = int(clean_period.sum())
        delta = raw_period_total - clean_period_total
        rate = clean_period_total / raw_period_total * 100 if raw_period_total else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("前処理前", f"{raw_period_total:,} 件")
        c2.metric("前処理後", f"{clean_period_total:,} 件")
        c3.metric("減少件数", f"{delta:,} 件")
        c4.metric("保持率", f"{rate:.1f}%")

        if (clean_period > raw_period).any():
            st.warning("一部の日で前処理後の投稿数が前処理前を上回っています。"
                       "元データ・日付基準・集計方法が一致するか確認してください。")

        if clean_period_total > raw_period_total:
            st.warning(
                "前処理後の件数が前処理前を上回っています。"
                "データの収集期間・元データ・抽出条件が同じか確認してください。"
            )
        if (raw_daily.index.min().date(), raw_daily.index.max().date()) != (
            clean_daily.index.min().date(), clean_daily.index.max().date()
        ):
            st.info(
                "2つのデータで最初または最後の投稿日が異なります。"
                "除外の結果として端の日付が消えた可能性もありますが、"
                "同じ元データを使っているか確認してください。"
            )
    else:
        st.metric("前処理前", f"{raw_period_total:,} 件")
        st.info(
            "前処理後データはまだ指定されていません。"
            "サイドバーから最新CSVをアップロードすると、2系列の比較が表示されます。"
        )

    # 以前のダッシュボードにあった最大値・最小値・平均値を復元。
    # 選択中の集計単位と表示期間で求め、前処理後があれば両方表示する。
    st.subheader(f"📊 {selected_freq}の統計（{start_date} 〜 {end_date}）")

    def show_summary(label, counts):
        st.markdown(f"**{label}**")
        maximum = int(counts.max()) if not counts.empty else 0
        minimum = int(counts.min()) if not counts.empty else 0
        average = float(counts.mean()) if not counts.empty else 0.0
        col1, col2, col3 = st.columns(3)
        col1.metric("最大投稿数", f"{maximum:,} 件")
        col2.metric("最小投稿数", f"{minimum:,} 件")
        col3.metric("平均投稿数", f"{average:,.1f} 件")

    show_summary("前処理前", raw_counts)
    if clean_daily is not None:
        show_summary("前処理後", clean_counts)

    st.caption(f"前処理前: {raw_source}")
    if clean_source is not None:
        st.caption(f"前処理後: {clean_source}")
    if raw_invalid or clean_invalid:
        st.warning(
            f"日付を解釈できず集計から外れた行: "
            f"前処理前 {raw_invalid:,} 件 / 前処理後 {clean_invalid:,} 件"
        )

    st.subheader(f"投稿数の推移（{selected_freq}・{start_date}〜{end_date}）")
    fig = go.Figure()
    if chart_kind == "棒グラフ":
        fig.add_trace(go.Bar(
            x=raw_counts.index, y=raw_counts.values,
            name="前処理前", marker_color="#1f77b4"
        ))
        if clean_daily is not None:
            fig.add_trace(go.Bar(
                x=clean_counts.index, y=clean_counts.values,
                name="前処理後", marker_color="#ff7f0e"
            ))
    else:
        fig.add_trace(go.Scatter(
            x=raw_counts.index, y=raw_counts.values,
            name="前処理前", mode="lines", line_color="#1f77b4"
        ))
        if clean_daily is not None:
            fig.add_trace(go.Scatter(
                x=clean_counts.index, y=clean_counts.values,
                name="前処理後", mode="lines", line_color="#ff7f0e"
            ))

    fig.update_layout(
        template="plotly_white", barmode="group",
        xaxis_title="年月日", yaxis_title="投稿件数",
        margin=dict(l=0, r=0, t=20, b=0),
        hovermode="x unified", legend_title_text="データ"
    )
    st.plotly_chart(fig, use_container_width=True)

    comparison = pd.DataFrame({
        "日付": raw_counts.index.strftime("%Y-%m-%d"),
        "前処理前": raw_counts.to_numpy()
    })
    if clean_daily is not None:
        comparison["前処理後"] = clean_counts.to_numpy()
        comparison["減少数"] = comparison["前処理前"] - comparison["前処理後"]
        comparison["保持率(%)"] = (
            comparison["前処理後"]
            .div(comparison["前処理前"].replace(0, float("nan")))
            .mul(100).round(1)
        )
    with st.expander("日別・週別・月別の集計表を表示"):
        st.dataframe(comparison, use_container_width=True, hide_index=True)
        st.download_button(
            "集計表をCSVで保存",
            comparison.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"bluesky_投稿数比較_{selected_freq}.csv",
            mime="text/csv"
        )
    st.caption(
        "※ 減少件数と保持率を前処理効果として解釈するには、"
        "両CSVの収集対象と期間が同じである必要があります。"
    )

if __name__ == "__main__":
    main()
