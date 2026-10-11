"""
Publication-quality three-panel figures for RQ1 and RQ3.

Outputs (saved to this script's directory):
  rq1_pai_three_panel.pdf / .png   – PAI × Size / Age / Category
  rq1_pdar_three_panel.pdf / .png  – PDAR × Size / Age / Category

Both figures share identical style, layout, and colour palette.
Project set matches the RQ1 text: 218 - 42 retired - 2 data-integrity = 174.
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _paths.RQ1_RESULTS
_os_root.makedirs(RESULTS_DIR, exist_ok=True)

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from scipy import stats
from itertools import combinations

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
# 语料筛选、Size / Age 分档、Domain 映射、PDAR 合并全部来自 rq1_bins —— 唯一定义处。
# 本文件原先放在 rq1_new/figures/，自己复制了一套常量，带来了三处与 Table 3 不一致的地方：
#   1. size_groups 的 pd.cut 没有传 right=False，实际是右闭区间（注释却写「左闭右开」）——
#      恰好 1806 个文件的 Ranger 被画进 Medium，组 n 与 Table 3 差一；
#   2. Domain 映射没有 rq1_bins 的 15 条手工补录，覆盖的项目更少；
#   3. PDAR 读的是 developer/result_v3/ 的 v3 结果，没有跟着换成 v4。
# 现在直接用 rq1_bins.load() 已算好的分组列，三处都自然消失。
import sys as _sys
HERE = os.path.dirname(os.path.abspath(__file__))
_sys.path.insert(0, HERE)
import rq1_bins                                                # noqa: E402

# rq1_bins 的组名 → 图上的显示标签（只改换行与符号，不改口径）
SIZE_LABELS = ["Small\n(<625)", "Medium\n(625–1805)", "Large\n(≥1806)"]
AGE_LABELS = ["≤2005", "2006–\n2011", "2012–\n2017", "≥2018"]
DOMAIN_LABELS = ["Data &\nAnalytics", "Network &\nComm.", "Dev. &\nTools", "Web &\nContent"]
_SIZE = dict(zip(rq1_bins.SIZE_LABELS, SIZE_LABELS))
_AGE = dict(zip(rq1_bins.AGE_LABELS, AGE_LABELS))
_DOMAIN = dict(zip(rq1_bins.DOMAIN_ORDER, DOMAIN_LABELS))

# Monochromatic blue palette – 2 to 4 groups, light → dark
MONO_BLUES = {
    2: ["#6BAED6", "#2171B5"],
    3: ["#9ECAE1", "#4292C6", "#08519C"],
    4: ["#C6DBEF", "#6BAED6", "#2171B5", "#08306B"],
}

SCATTER_THRESHOLD = 10  # groups with n < this → scatter only (excluded from KW)

# ── global matplotlib style ───────────────────────────────────────────────────
mpl.rcParams.update({
    "font.family":        "DejaVu Sans",
    "font.size":          10,
    "axes.titlesize":     11,
    "axes.titleweight":   "bold",
    "axes.labelsize":     10,
    "xtick.labelsize":    9,
    "ytick.labelsize":    9,
    "axes.linewidth":     0.8,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.color":         "#E0E0E0",
    "grid.linewidth":     0.6,
    "legend.frameon":     False,
    "figure.dpi":         150,
    "savefig.dpi":        300,
    "pdf.fonttype":       42,   # embeds fonts – required for most journals
    "ps.fonttype":        42,
})


# ── data loading ──────────────────────────────────────────────────────────────
def load_pai() -> pd.DataFrame:
    df = rq1_bins.load(adopters_only=True)
    print(f"[three_panel] PAI  N = {len(df)}")
    return df


def load_pdar() -> pd.DataFrame:
    df = rq1_bins.load(adopters_only=True, with_pdar=True)
    df["pdar"] = pd.to_numeric(df["pdar"], errors="coerce")
    print(f"[three_panel] PDAR N = {df['pdar'].notna().sum()}")
    return df


# ── grouping helpers ──────────────────────────────────────────────────────────
def _groups(df, metric, col, mapping, order):
    df = df.dropna(subset=[metric])
    out = {}
    for key in order:
        vals = df.loc[df[col].astype(str) == key, metric].values
        if len(vals) > 0:
            out[mapping[key]] = vals
    return out


def size_groups(df: pd.DataFrame, metric: str) -> dict:
    return _groups(df, metric, "size_grp", _SIZE, rq1_bins.SIZE_LABELS)


def age_groups(df: pd.DataFrame, metric: str) -> dict:
    return _groups(df, metric, "age_grp", _AGE, rq1_bins.AGE_LABELS)


def cat_groups(df: pd.DataFrame, metric: str) -> dict:
    return _groups(df, metric, "domain_grp", _DOMAIN, rq1_bins.DOMAIN_ORDER)


# ── statistics ────────────────────────────────────────────────────────────────
def kw_stat(groups: dict) -> tuple:
    """Return (H, p) for Kruskal-Wallis using only groups with n ≥ SCATTER_THRESHOLD."""
    arrays = [v for v in groups.values() if len(v) >= SCATTER_THRESHOLD]
    if len(arrays) < 2:
        return float("nan"), float("nan")
    result = stats.kruskal(*arrays)
    return result.statistic, result.pvalue


def p_annotation(H: float, p: float) -> str:
    if np.isnan(p):
        return ""
    sig = "" if p >= 0.05 else (" *" if p < 0.05 else "")
    if p < 0.001:
        sig = " ***"
    elif p < 0.01:
        sig = " **"
    elif p < 0.05:
        sig = " *"
    else:
        sig = " (n.s.)"
    return f"H={H:.2f}, p={p:.3f}{sig}"


# ── single-panel plot ─────────────────────────────────────────────────────────
def draw_panel(ax: plt.Axes, groups: dict,
               ylabel: str = "", title: str = "", panel_label: str = ""):
    """
    Violin + box overlay for groups with n ≥ SCATTER_THRESHOLD;
    scatter-only for groups with n < SCATTER_THRESHOLD.
    Colours are monochromatic blues, light → dark across groups.
    n= labels are NOT placed here; call add_n_labels() after setting ylim.
    """
    labels    = list(groups.keys())
    n_grps    = len(labels)
    colours   = MONO_BLUES.get(n_grps, MONO_BLUES[4])[:n_grps]
    positions = list(range(n_grps))

    # separate groups by size
    violin_pos, violin_data, violin_col = [], [], []
    scatter_pos, scatter_data, scatter_col = [], [], []
    for i, k in enumerate(labels):
        vals = groups[k]
        if len(vals) >= SCATTER_THRESHOLD:
            violin_pos.append(i)
            violin_data.append(vals)
            violin_col.append(colours[i])
        else:
            scatter_pos.append(i)
            scatter_data.append(vals)
            scatter_col.append(colours[i])

    # ── violin (clip polygon vertices to y ≥ 0) ──
    if violin_data:
        parts = ax.violinplot(violin_data, positions=violin_pos,
                              showmedians=False, showextrema=False, widths=0.65)
        for pc, col in zip(parts["bodies"], violin_col):
            pc.set_facecolor(col)
            pc.set_edgecolor("none")
            pc.set_alpha(0.40)
            verts = pc.get_paths()[0].vertices
            verts[:, 1] = np.clip(verts[:, 1], 0, None)
            pc.get_paths()[0].vertices = verts

    # ── box (narrow, on top of violin) ──
    if violin_data:
        bp = ax.boxplot(
            violin_data, positions=violin_pos, widths=0.22, patch_artist=True,
            medianprops=dict(color="black", linewidth=2.0),
            whiskerprops=dict(color="#555555", linewidth=1.0),
            capprops=dict(color="#555555", linewidth=1.0),
            flierprops=dict(marker="o", markersize=3.0,
                            markerfacecolor="#888888", markeredgewidth=0.4,
                            alpha=0.6),
            boxprops=dict(linewidth=0.8),
            zorder=3,
        )
        for patch, col in zip(bp["boxes"], violin_col):
            patch.set_facecolor(col)
            patch.set_alpha(0.80)

    # ── scatter for small groups ──
    for pos, vals, col in zip(scatter_pos, scatter_data, scatter_col):
        jitter = np.random.default_rng(42).uniform(-0.10, 0.10, len(vals))
        ax.scatter(pos + jitter, vals, color=col, s=48, zorder=4,
                   edgecolors="white", linewidths=0.6)
        # median tick
        ax.hlines(np.median(vals), pos - 0.18, pos + 0.18,
                  color="black", linewidth=2.0, zorder=5)

    # ── KW annotation (H and p) ──
    H, p = kw_stat(groups)
    ann = p_annotation(H, p)
    if ann:
        ax.text(0.98, 0.97, ann, transform=ax.transAxes,
                ha="right", va="top", fontsize=8,
                color="black",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                          edgecolor="#CCCCCC", linewidth=0.6))

    # ── axes cosmetics ──
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_xlim(-0.6, n_grps - 0.4)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold", pad=6)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.6)
    ax.set_axisbelow(True)

    if panel_label:
        ax.text(-0.14, 1.06, panel_label, transform=ax.transAxes,
                fontsize=13, fontweight="bold", va="top")


def add_n_labels(ax: plt.Axes, groups: dict):
    """Append n= count to x-tick labels (below the group name)."""
    labels = list(groups.keys())
    new_labels = [f"{k}\n(n={len(groups[k])})" for k in labels]
    ax.set_xticklabels(new_labels, fontsize=9)


# ── three-panel figure ────────────────────────────────────────────────────────
def make_three_panel(metric: str, ylabel: str, out_stem: str,
                     size_g: dict, age_g: dict, cat_g: dict):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5),
                             gridspec_kw={"wspace": 0.40})

    draw_panel(axes[0], size_g, ylabel=ylabel,
               title="By Project Size",  panel_label="(a)")
    draw_panel(axes[1], age_g,  ylabel="",
               title="By Founding Era",  panel_label="(b)")
    draw_panel(axes[2], cat_g,  ylabel="",
               title="By Domain",        panel_label="(c)")

    # unified y-axis: lower bound clipped at 0, upper at 99th-pct × 1.22
    all_vals = np.concatenate([v for g in [size_g, age_g, cat_g]
                                for v in g.values() if len(v) > 0])
    y_lo = 0.0
    y_hi = np.percentile(all_vals, 99) * 1.22
    for ax in axes:
        ax.set_ylim(y_lo, y_hi)

    # n= labels placed after ylim is fixed
    for ax, grp in zip(axes, [size_g, age_g, cat_g]):
        add_n_labels(ax, grp)

    fig.patch.set_facecolor("white")
    # metadata：去掉 PDF 里的生成时间，使重跑产物逐字节可复现
    plt.savefig(os.path.join(RESULTS_DIR, out_stem + ".pdf"), metadata={"CreationDate": None},
                bbox_inches="tight", backend="pdf")
    plt.savefig(os.path.join(RESULTS_DIR, out_stem + ".png"),
                bbox_inches="tight", dpi=300)
    plt.close()
    print(f"  Saved  {out_stem}.pdf  /  {out_stem}.png")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    # ── PAI figure ──
    print("Building PAI three-panel figure …")
    pai_df = load_pai()
    print(f"  PAI dataset: {len(pai_df)} projects (non-retired PT users)")
    make_three_panel(
        metric   = "pai",
        ylabel   = "PAI (%)",
        out_stem = "rq1_pai_three_panel",
        size_g   = size_groups(pai_df, "pai"),
        age_g    = age_groups(pai_df,  "pai"),
        cat_g    = cat_groups(pai_df,  "pai"),
    )

    # ── PDAR figure ──
    print("Building PDAR three-panel figure …")
    pdar_df = load_pdar()
    print(f"  PDAR dataset: {len(pdar_df)} projects (non-retired)")
    make_three_panel(
        metric   = "pdar",
        ylabel   = "PDAR (%)",
        out_stem = "rq1_pdar_three_panel",
        size_g   = size_groups(pdar_df, "pdar"),
        age_g    = age_groups(pdar_df,  "pdar"),
        cat_g    = cat_groups(pdar_df,  "pdar"),
    )

    print("\nDone. Output directory:", RESULTS_DIR)


if __name__ == "__main__":
    main()
