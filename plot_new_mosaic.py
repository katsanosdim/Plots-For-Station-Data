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
st.title("🌍 Climate Mosaic Visualisation")
st.markdown("Monthly & Seasonal anomaly heatmaps for NOA Thiseio Station")

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

    st.header("Reference Period")
    ref_start = st.number_input("Reference Start", value=1991)
    ref_end   = st.number_input("Reference End", value=2020)

    st.header("Colormap")
    colormap = st.selectbox(
        "Select Colormap",
        [
            "RdBu_r", "coolwarm", "seismic", "BrBG",
            "Spectral_r", "PuOr", "PRGn",
            "viridis", "plasma", "cividis",
            "turbo", "magma"
        ],
        index=0
    )

    auto_center = st.checkbox("Auto center at zero", True)

    st.header("Year Range to Plot")
    year_range = st.slider("Select Years", 1950, 2025, (1990, 2023))

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
        st.error("CSV must contain 'Year' column")
        st.stop()

    df = df.sort_values("Year").reset_index(drop=True)

    # ----------------------------------------------
    # Select year range for plotting
    # ----------------------------------------------
    df_plot = df[
        (df["Year"] >= year_range[0]) &
        (df["Year"] <= year_range[1])
    ].copy()

    # ----------------------------------------------
    # Reference period selection
    # ----------------------------------------------
    df_ref = df[
        (df["Year"] >= ref_start) &
        (df["Year"] <= ref_end)
    ]

    if df_ref.empty:
        st.error("Reference period not found in dataset.")
        st.stop()

    month_cols = [c for c in df.columns if c != "Year"]

    if len(month_cols) != 12:
        st.error("Need exactly 12 monthly columns.")
        st.stop()

    # ----------------------------------------------
    # Compute anomalies using reference climatology
    # ----------------------------------------------
    ref_mean = df_ref[month_cols].mean()
    anomaly = df_plot[month_cols] - ref_mean

    anomaly = anomaly.values

    # ----------------------------------------------
    # Seasonal option
    # ----------------------------------------------
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

    # ----------------------------------------------
    # Color scaling
    # ----------------------------------------------
    vmin = np.nanmin(anomaly)
    vmax = np.nanmax(anomaly)

    if auto_center:
        max_abs = max(abs(vmin), abs(vmax))
        vmin, vmax = -max_abs, max_abs

    norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    cmap = plt.get_cmap(colormap)

    # ----------------------------------------------
    # Plot
    # ----------------------------------------------
    n_years = len(df_plot)
    fig_width = max(12, n_years * 0.35)

    fig, ax = plt.subplots(figsize=(fig_width, 8))

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

    title = f"Anomalies relative to {ref_start}-{ref_end}"
    plt.title(title, fontsize=18)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Anomaly")

    st.pyplot(fig)

    # ----------------------------------------------
    # Export
    # ----------------------------------------------
    buf = io.BytesIO()
    fig.savefig(buf, format=file_format.lower(), dpi=dpi, bbox_inches="tight")
    buf.seek(0)

    st.download_button(
        f"Download {file_format}",
        buf,
        file_name=f"mosaic_{year_range[0]}_{year_range[1]}.{file_format.lower()}"
    )

else:
    st.info("Upload a CSV file to begin.")
