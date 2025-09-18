import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
import io

# Configure the app
st.set_page_config(page_title="Climate Plots Generator", page_icon="🌍", layout="wide")
st.title(":earth_africa: Climate Plots Generator")
st.markdown("Make **climate stripes** or **climate bars** plots for any parameter. Created by **Dimitris Katsanos**")

# Sidebar with controls
with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"],
                                     help="First column must be 'Year', others are parameters")

    st.header("Visualization Settings")
    plot_type = st.radio("Plot Type", ["Stripes", "Bars"], index=0)

    colormap = st.selectbox("Color Map",
                            ["RdBu_r", "coolwarm", "seismic", "BrBG", "viridis", "plasma"],
                            index=0, help="Choose a color scheme")

    stripe_width = st.slider("Stripe Width", 1, 20, 5, help="(Stripes only)")
    stripe_height = st.slider("Stripe Height", 1, 20, 10, help="(Stripes only)")

    bar_width = st.slider("Bar Width", 0.1, 1.0, 0.8, step=0.1, help="(Bars only)")

    show_years = st.checkbox("Show Years", True)
    year_step = st.slider("Year Label Step", 1, 20, 5)

    st.header("Colorbar & Title")
    custom_title = st.text_input("Custom Title", value="Data - Area Sum Precipitation % Anomaly for")
    set_color_range = st.checkbox("Set Colorbar Range")
    if set_color_range:
        color_min = st.number_input("Colorbar Min", value=-100.0, step=10)
        color_max = st.number_input("Colorbar Max", value=100.0, step=10)

    st.header("Trendline (Bars only)")
    add_trendline = st.checkbox("Add Trendline", value=True)
    if add_trendline:
        trend_color = st.color_picker("Trendline Color", "#000000")
        trend_style = st.selectbox("Trendline Style", ["solid", "dashed", "dotted", "dashdot"])
        trend_width = st.slider("Trendline Width", 1, 5, 2)

    st.header("Save Options")
    custom_filename = st.text_input("Custom Filename (without extension)", value="climate_plot")
    dpi = st.slider("Image Quality (DPI)", 100, 600, 300)
    file_format = st.selectbox("File Format", ["PNG", "SVG", "PDF"], index=0)

# Example data for download
example_data = pd.DataFrame({
    'Year': range(1980, 2024),
    'Temperature': np.random.normal(15, 2, 44),
    'Precipitation': np.random.normal(100, 20, 44),
    'Humidity': np.random.normal(70, 5, 44)
})
csv = example_data.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="Download Example CSV",
    data=csv,
    file_name="climate_data_example.csv",
    mime="text/csv"
)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

        if 'Year' not in df.columns:
            st.error("CSV must contain a 'Year' column")
            st.stop()

        param_columns = [col for col in df.columns if col != 'Year']
        if len(param_columns) < 1:
            st.error("CSV must contain at least one parameter column besides 'Year'")
            st.stop()

        parameter = st.selectbox("Select parameter to plot", param_columns)

        df = df.sort_values('Year').reset_index(drop=True)
        min_year, max_year = df['Year'].min(), df['Year'].max()

        mean_value = df[parameter].mean()
        df['Anomaly'] = df[parameter] - mean_value

        # 🔹 Handle color limits
        if set_color_range:
            vmin, vmax = color_min, color_max
        else:
            if plot_type == "Bars":
                max_abs = max(abs(df['Anomaly'].min()), abs(df['Anomaly'].max()))
                vmin, vmax = -max_abs, max_abs
            else:
                vmin = df['Anomaly'].min()
                vmax = df['Anomaly'].max()

        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.get_cmap(colormap)

        fig, ax = plt.subplots(figsize=(15, 5))

        if plot_type == "Stripes":
            for i, row in df.iterrows():
                color = cmap(norm(row['Anomaly']))
                ax.fill_between([i, i + 1], 0, 1, color=color)

            ax.set_xlim(0, len(df))
            ax.set_ylim(0, 1)
            ax.set_axis_off()

            if show_years:
                for i, year in enumerate(df['Year']):
                    if year % year_step == 0:
                        ax.text(i + 0.5, -0.05, str(year),
                                rotation=90, ha='center', va='top', fontsize=10, alpha=0.7)

        elif plot_type == "Bars":
            colors = [cmap(norm(val)) for val in df['Anomaly']]
            ax.bar(df['Year'], df['Anomaly'], color=colors, width=bar_width, edgecolor="black")

            # 🔹 Make y-axis follow vmin/vmax
            ax.set_ylim(vmin, vmax)
            ax.axhline(0, color="black", linewidth=1)

            if show_years:
                ax.set_xticks(df['Year'][::year_step])
                ax.set_xticklabels(df['Year'][::year_step], rotation=90)

            if add_trendline:
                z = np.polyfit(df['Year'], df['Anomaly'], 1)
                p = np.poly1d(z)
                ax.plot(df['Year'], p(df['Year']),
                        color=trend_color, linestyle=trend_style, linewidth=trend_width)

        plt.title(f"{custom_title} {parameter} ({min_year}-{max_year})", fontsize=16)

        # Colorbar
        sm = ScalarMappable(norm=norm, cmap=cmap)
        cbar = fig.colorbar(sm, ax=ax, orientation='vertical', fraction=0.03, pad=0.02)
        cbar.set_label("% Anomaly", fontsize=12)

        st.pyplot(fig)

        # Save
        buf = io.BytesIO()
        plt.savefig(buf, format=file_format.lower(), dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        filename = f"{custom_filename}_{parameter}_{min_year}-{max_year}.{file_format.lower()}"

        st.download_button(
            label=f"Download Your Image ({file_format})",
            data=buf,
            file_name=filename,
            mime="image/png" if file_format == "PNG" else
                 "image/svg+xml" if file_format == "SVG" else "application/pdf"
        )

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
else:
    st.markdown("""
    ## How to Use This App
    1. **Upload your CSV file** with a `Year` column and parameters.  
    2. Choose **plot type** (Stripes or Bars).  
    3. Customize visualization, color map, and trendline.  
    4. Save the figure in PNG, SVG, or PDF.  
    """)
