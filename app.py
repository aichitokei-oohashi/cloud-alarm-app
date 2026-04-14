import re
from datetime import timedelta

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import streamlit as st

st.set_page_config(page_title="クラウド通報データ分析アプリ", layout="wide")

st.title("クラウド通報データ分析アプリ")
st.caption("通報データを期間指定し、傾向分析・時系列分析・個別分析を行います。")

PRIORITY_EVENTS = [
    "継続使用時間遮断",
    "圧力低下遮断",
    "合計・増加流量遮断",
]

COL_DATETIME = "発生日時"
COL_DEVICE_ID = "無線機ＩＤ"
COL_EVENT = "セキュリティ情報"


# -------------------------
# 日本語フォント設定
# -------------------------
def setup_japanese_font():
    fonts = ["Meiryo", "Yu Gothic", "MS Gothic"]
    installed = {f.name for f in fm.fontManager.ttflist}
    for f in fonts:
        if f in installed:
            plt.rcParams["font.family"] = f
            break
    plt.rcParams["axes.unicode_minus"] = False


setup_japanese_font()


# -------------------------
# CSV読込
# -------------------------
def load_csv(file):
    for enc in ["utf-8-sig", "cp932", "shift_jis"]:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc)
        except:
            pass
    file.seek(0)
    return pd.read_csv(file)


def split_events(text):
    if pd.isna(text):
        return []
    text = str(text).replace("\u3000", " ")
    return [t.strip() for t in re.split(r"\s+", text) if t.strip()]


# -------------------------
# グラフ
# -------------------------
def style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.3)


def barh(df, x, y, title):
    fig, ax = plt.subplots(figsize=(10, max(4, len(df)*0.4)))
    bars = ax.barh(df[x], df[y])
    ax.set_title(title)
    ax.invert_yaxis()
    style(ax)
    for b in bars:
        ax.text(b.get_width(), b.get_y()+b.get_height()/2,
                f"{int(b.get_width())}", va="center")
    return fig


def barv(df, x, y, title):
    fig, ax = plt.subplots(figsize=(10,4))
    bars = ax.bar(df[x], df[y])
    ax.set_title(title)
    plt.xticks(rotation=45)
    style(ax)
    for b in bars:
        ax.text(b.get_x()+b.get_width()/2, b.get_height(),
                f"{int(b.get_height())}", ha="center")
    return fig


# -------------------------
# ファイル読込
# -------------------------
file = st.file_uploader("CSVアップロード", type="csv")
if not file:
    st.stop()

df = load_csv(file)

df[COL_DATETIME] = pd.to_datetime(
    df[COL_DATETIME],
    format="%Y年%m月%d日 %H時%M分",
    errors="coerce"
)

df = df.dropna(subset=[COL_DATETIME])
df["日付"] = df[COL_DATETIME].dt.date

# -------------------------
# 期間フィルタ
# -------------------------
min_d, max_d = df["日付"].min(), df["日付"].max()

st.sidebar.header("期間フィルタ")

start = st.sidebar.date_input("開始", min_d)
end = st.sidebar.date_input("終了", max_d)

df = df[(df["日付"]>=start)&(df["日付"]<=end)]

# -------------------------
# イベント展開
# -------------------------
rows = []
for _, r in df.iterrows():
    for e in split_events(r[COL_EVENT]):
        rows.append({
            "イベント": e,
            "無線機": r[COL_DEVICE_ID],
            "年月": r[COL_DATETIME].strftime("%Y-%m")
        })

edf = pd.DataFrame(rows)

# -------------------------
# ① イベント別件数
# -------------------------
st.subheader("① イベント別発生件数（全体傾向）")

ev_sum = edf.groupby("イベント").size().reset_index(name="件数").sort_values("件数",ascending=False)

col1,col2=st.columns(2)
col1.dataframe(ev_sum)
col2.pyplot(barh(ev_sum.head(10),"イベント","件数","イベント件数TOP10"))

# -------------------------
# ② 月別件数
# -------------------------
st.subheader("② イベント別 月別発生件数（時系列分析）")

event_sel = st.selectbox("イベント選択", ev_sum["イベント"])

m = edf[edf["イベント"]==event_sel]

m_sum = m.groupby("年月").size().reset_index(name="件数").sort_values("年月")

col1,col2=st.columns(2)
col1.dataframe(m_sum)
col2.pyplot(barv(m_sum,"年月","件数",f"{event_sel} 月別推移"))

# -------------------------
# ③ ランキング
# -------------------------
st.subheader("③ イベント別 無線機IDランキング（個別分析）")

event_multi = st.multiselect("イベント選択", ev_sum["イベント"], default=PRIORITY_EVENTS)

for ev in event_multi:
    d = edf[edf["イベント"]==ev]
    rank = d.groupby("無線機").size().reset_index(name="件数").sort_values("件数",ascending=False)

    st.markdown(f"### {ev}")
    col1,col2=st.columns(2)
    col1.dataframe(rank.head(20))
    col2.pyplot(barh(rank.head(15),"無線機","件数",ev))