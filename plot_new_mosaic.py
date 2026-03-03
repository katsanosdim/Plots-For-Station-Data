import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Climate Mosaic", page_icon="🌍", layout="wide")
st.title("🌍 Temperature Heatmap Visualisation")
st.markdown("Anomalies relative to 1991–2020 climatology - Created by Dimitris Katsanos (NOA/IERSD)")

REFERENCE_START = 1991
REFERENCE_END   = 2020

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
with st.sidebar:

    st.header("Upload Data")
    uploaded_file = st.file_uploader(
        "Upload CSV",
        type=["csv"],
        help="Must contain Year + 12 monthly columns (Jan–Dec)"
    )

    st.header("Plot Type")
    plot_type = st.radio(
        "Choose Plot",
        ["Mosaic", "Seasonal Mosaic"]
    )
    st.header("Title")
    custom_title = st.text_input(
    "Plot Title",
    value="Climate Anomalies"
    )
    
    st.header("Plot Period (adjustable)")
    plot_start = st.number_input("Start Year", value=2000)
    plot_end   = st.number_input("End Year", value=2023)

    st.header("Colormap")
    colormap = st.selectbox(
        "Select Colormap",
        [
            "RdBu_r", "coolwarm", "seismic", "BrBG",
            "Spectral_r", "PuOr_r", "PRGn",
            "RdYlBu_r", "plasma", "cividis",
            "turbo", "magma"
        ],
        index=0
    )

    auto_center = st.checkbox("Auto center at zero", True)

    st.header("Display Options")
    show_years = st.checkbox("Show Year Labels", True)
    year_step = st.slider("Year Label Step", 1, 20, 5)

    st.header("Export")
    dpi = st.slider("DPI", 100, 600, 300)
    file_format = st.selectbox("Format", ["PNG", "SVG", "PDF"])


# -------------------------------------------------
# MAIN
# -------------------------------------------------
if uploaded_file:

    df = pd.read_csv(uploaded_file)

    if "Year" not in df.columns:
        st.error("CSV must contain 'Year' column.")
        st.stop()

    df = df.sort_values("Year").reset_index(drop=True)

    month_cols = [c for c in df.columns if c != "Year"]

    if len(month_cols) != 12:
        st.error("Need exactly 12 monthly columns.")
        st.stop()

    # -------------------------------------------------
    # FIXED REFERENCE PERIOD (1991–2020)
    # -------------------------------------------------
    df_ref = df[
        (df["Year"] >= REFERENCE_START) &
        (df["Year"] <= REFERENCE_END)
    ]

    if df_ref.empty:
        st.error("Reference period 1991–2020 not found in dataset.")
        st.stop()

    ref_mean = df_ref[month_cols].mean()

    # -------------------------------------------------
    # USER-SELECTED PLOT PERIOD
    # -------------------------------------------------
    df_plot = df[
        (df["Year"] >= plot_start) &
        (df["Year"] <= plot_end)
    ].copy()

    if df_plot.empty:
        st.error("Selected plot period not found in dataset.")
        st.stop()

    anomaly = df_plot[month_cols] - ref_mean
    anomaly = anomaly.values

    # -------------------------------------------------
    # SEASONAL OPTION
    # -------------------------------------------------
    if plot_type == "Seasonal Mosaic":

        seasons = {
            "DJF": [11, 0, 1],
            "MAM": [2, 3, 4],
            "JJA": [5, 6, 7],
            "SON": [8, 9, 10]
        }

        seasonal_matrix = []
        for s in seasons.values():
            seasonal_matrix.append(
                np.nanmean(anomaly[:, s], axis=1)
            )

        anomaly = np.array(seasonal_matrix).T
        month_cols = list(seasons.keys())

    # -------------------------------------------------
    # COLOR SCALING
    # -------------------------------------------------
    vmin = np.nanmin(anomaly)
    vmax = np.nanmax(anomaly)

    if auto_center:
        max_abs = max(abs(vmin), abs(vmax))
        vmin, vmax = -max_abs, max_abs

    norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    cmap = plt.get_cmap(colormap)

    # -------------------------------------------------
    # PLOT
    # -------------------------------------------------
    n_years = len(df_plot)
    fig_width = max(12, n_years * 0.35)

    fig, ax = plt.subplots(figsize=(fig_width, 4))

    im = ax.imshow(
        anomaly.T,
        cmap=cmap,
        norm=norm,
        origin="upper",
        aspect="auto"
    )

    # Gridlines
    ax.set_xticks(np.arange(-.5, n_years, 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(month_cols), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.5)
    ax.tick_params(which="minor", bottom=False, left=False)

    # Year labels
    if show_years:
        ax.set_xticks(np.arange(0, n_years, year_step))
        ax.set_xticklabels(
            df_plot["Year"].values[::year_step],
            rotation=90
        )
    else:
        ax.set_xticklabels([])

    ax.set_yticks(np.arange(len(month_cols)))
    ax.set_yticklabels(month_cols)

    title = f"{custom_title} ({plot_start}–{plot_end})\nReference Period: 1991–2020"
    plt.title(title, fontsize=18)
    #title = f"Anomalies relative to 1991–2020 ({plot_start}–{plot_end})"
    #plt.title(title, fontsize=18)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Anomaly")

    st.pyplot(fig)

    # -------------------------------------------------
    # EXPORT
    # -------------------------------------------------
    buf = io.BytesIO()
    fig.savefig(buf, format=file_format.lower(), dpi=dpi, bbox_inches="tight")
    buf.seek(0)

    st.download_button(
        f"Download {file_format}",
        buf,
        file_name=f"mosaic_{plot_start}_{plot_end}.{file_format.lower()}"
    )

else:
    st.info("Upload a CSV file to begin.")
