import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
import plotly.express as px
import io

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Advanced Climate Plots", page_icon="🌍", layout="wide")
st.title("🌍 Advanced Climate Visualisation App")
st.markdown("Stripes • Bars • Mosaic • Interactive • Seasonal")

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
with st.sidebar:

    st.header("Upload Data")
    uploaded_file = st.file_uploader(
        "Upload CSV",
        type=["csv"],
        help="For Mosaic: Year, Jan–Dec columns"
    )

    st.header("Plot Type")
    plot_type = st.radio(
        "Choose Plot",
        ["Stripes", "Bars", "Mosaic", "Interactive Mosaic", "Seasonal Mosaic"]
    )

    st.header("Color Settings")
    colormap = st.selectbox(
        "Colormap",
        ["RdBu_r", "coolwarm", "seismic", "BrBG", "viridis", "plasma"],
        index=0
    )

    auto_center = st.checkbox("Auto center at zero", value=True)

    set_color_range = st.checkbox("Manual color range")
    if set_color_range:
        color_min = st.number_input("Min", value=-2.0)
        color_max = st.number_input("Max", value=2.0)

    st.header("Labels")
    show_years = st.checkbox("Show Year Labels", True)
    year_step = st.slider("Year Step", 1, 20, 5)

    st.header("Trendline (Bars only)")
    add_trendline = st.checkbox("Add Trendline", True)

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

    min_year, max_year = df["Year"].min(), df["Year"].max()

    # -------------------------------------------------
    # STRIPES & BARS
    # -------------------------------------------------
    if plot_type in ["Stripes", "Bars"]:

        param_columns = [col for col in df.columns if col != "Year"]
        parameter = st.selectbox("Select Parameter", param_columns)

        mean_value = df[parameter].mean()
        df["Anomaly"] = df[parameter] - mean_value

        vmin = df["Anomaly"].min()
        vmax = df["Anomaly"].max()

        if auto_center:
            max_abs = max(abs(vmin), abs(vmax))
            vmin, vmax = -max_abs, max_abs

        if set_color_range:
            vmin, vmax = color_min, color_max

        norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
        cmap = plt.get_cmap(colormap)

        fig, ax = plt.subplots(figsize=(15,5))

        if plot_type == "Stripes":

            for i, row in df.iterrows():
                ax.fill_between(
                    [i, i+1], 0, 1,
                    color=cmap(norm(row["Anomaly"]))
                )

            ax.set_axis_off()

            if show_years:
                for i, year in enumerate(df["Year"]):
                    if year % year_step == 0:
                        ax.text(i+0.5, -0.05, str(year),
                                rotation=90, ha='center')

        elif plot_type == "Bars":

            colors = cmap(norm(df["Anomaly"]))
            ax.bar(df["Year"], df["Anomaly"], color=colors)

            if show_years:
                ax.set_xticks(df["Year"][::year_step])
                ax.set_xticklabels(df["Year"][::year_step], rotation=90)

            ax.axhline(0, color="black")

            if add_trendline:
                z = np.polyfit(df["Year"], df["Anomaly"], 1)
                p = np.poly1d(z)
                ax.plot(df["Year"], p(df["Year"]), color="black", linewidth=2)

        sm = ScalarMappable(norm=norm, cmap=cmap)
        fig.colorbar(sm, ax=ax)

        plt.title(f"{parameter} Anomaly ({min_year}-{max_year})")
        st.pyplot(fig)

    # -------------------------------------------------
    # MOSAIC
    # -------------------------------------------------
    elif plot_type in ["Mosaic", "Interactive Mosaic", "Seasonal Mosaic"]:

        month_cols = [c for c in df.columns if c != "Year"]

        if len(month_cols) != 12:
            st.error("Need 12 monthly columns (Jan–Dec)")
            st.stop()

        data_matrix = df[month_cols].values

        # Monthly climatology anomaly
        monthly_mean = np.nanmean(data_matrix, axis=0)
        anomaly = data_matrix - monthly_mean

        if plot_type == "Seasonal Mosaic":

            seasons = {
                "DJF": [11,0,1],
                "MAM": [2,3,4],
                "JJA": [5,6,7],
                "SON": [8,9,10]
            }

            seasonal_matrix = []
            for s in seasons.values():
                seasonal_matrix.append(np.nanmean(anomaly[:, s], axis=1))

            anomaly = np.array(seasonal_matrix).T
            month_cols = list(seasons.keys())

        vmin = np.nanmin(anomaly)
        vmax = np.nanmax(anomaly)

        if auto_center:
            max_abs = max(abs(vmin), abs(vmax))
            vmin, vmax = -max_abs, max_abs

        if set_color_range:
            vmin, vmax = color_min, color_max

        if plot_type == "Interactive Mosaic":

            fig = px.imshow(
                anomaly.T,
                labels=dict(x="Year", y="Month/Season", color="Anomaly"),
                x=df["Year"],
                y=month_cols,
                color_continuous_scale=colormap,
                zmin=vmin,
                zmax=vmax,
                aspect="auto"
            )

            st.plotly_chart(fig, use_container_width=True)

        else:

            norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
            cmap = plt.get_cmap(colormap)

            fig, ax = plt.subplots(figsize=(15,6))
            im = ax.imshow(
                anomaly.T,
                aspect="auto",
                cmap=cmap,
                norm=norm,
                origin="lower"
            )

            # Grid style
            ax.set_xticks(np.arange(-.5, len(df), 1), minor=True)
            ax.set_yticks(np.arange(-.5, len(month_cols), 1), minor=True)
            ax.grid(which="minor", color="white", linewidth=0.5)
            ax.tick_params(which="minor", bottom=False, left=False)

            if show_years:
                ax.set_xticks(np.arange(0,len(df),year_step))
                ax.set_xticklabels(df["Year"][::year_step], rotation=90)
            else:
                ax.set_xticklabels([])

            ax.set_yticks(np.arange(len(month_cols)))
            ax.set_yticklabels(month_cols)

            fig.colorbar(im, ax=ax)

            plt.title(f"Mosaic Anomaly ({min_year}-{max_year})")

            st.pyplot(fig)

    # -------------------------------------------------
    # EXPORT
    # -------------------------------------------------
    if plot_type != "Interactive Mosaic":
        buf = io.BytesIO()
        plt.savefig(buf, format=file_format.lower(), dpi=dpi, bbox_inches='tight')
        buf.seek(0)

        st.download_button(
            f"Download {file_format}",
            buf,
            file_name=f"climate_plot.{file_format.lower()}"
        )

else:
    st.info("Upload a CSV file to begin.")
