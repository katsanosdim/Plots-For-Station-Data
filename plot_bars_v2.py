import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
import io

# Configure the app
st.set_page_config(page_title="Climate Plots Generator", page_icon="🌍", layout="wide")
st.title(":earth_africa: Climate Bars Generator")
st.markdown("Make climate **bar plots** with anomalies and optional trendlines. Created by **Dimitris Katsanos**")

# Sidebar with controls
with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"],
                                    help="First column must be 'Year', others are parameters")

    st.header("Visualization Settings")
    colormap = st.selectbox("Color Map", ["RdBu_r", "coolwarm", "seismic", "BrBG", "viridis", "plasma"],
                          index=0, help="Choose a color scheme for the bars")

    bar_width = st.slider("Bar Width", 0.2, 1.0, 0.8, step=0.05, help="Width of bars")  ### 🔹 CHANGED

    show_years = st.checkbox("Show Years", True, help="Display year labels")
    year_step = st.slider("Year Label Step", 1, 20, 5, help="Show every Nth year")

    st.header("Title & Colorbar")
    custom_title = st.text_input("Custom Title", value="NOA/IERSD - Thisseio Station")
    set_color_range = st.checkbox("Set Colorbar Range")
    if set_color_range:
        color_min = st.number_input("Colorbar Min", value=-2.0, step=0.5)
        color_max = st.number_input("Colorbar Max", value=2.0, step=0.5)

    reference_line = st.selectbox("Reference Line",
                                 ["None", "Average", "20th Century Average", "Custom Value"],
                                 index=0)

    if reference_line == "Custom Value":
        custom_ref = st.number_input("Reference Value", value=0.0)

    # 🔹 NEW: Trendline settings
    show_trendline = st.checkbox("Show Trendline", True)
    if show_trendline:
        trend_color = st.color_picker("Trendline Color", "#000000")
        trend_style = st.selectbox("Trendline Style", ["solid", "dashed", "dotted", "dashdot"], index=0)

    st.header("Save Options")
    custom_filename = st.text_input("Custom Filename (without extension)", value="climate_bars")
    dpi = st.slider("Image Quality (DPI)", 100, 600, 300)
    file_format = st.selectbox("File Format", ["PNG", "SVG", "PDF"], index=0)

    st.markdown("---")
    st.caption("Climate bar plots visualize anomalies relative to the mean for any parameter.")

# Example data
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

        # Choose parameter
        parameter = st.selectbox("Select parameter to plot", param_columns)

        # Sort by year
        df = df.sort_values('Year').reset_index(drop=True)
        min_year, max_year = df['Year'].min(), df['Year'].max()

        # Compute anomalies
        mean_value = df[parameter].mean()
        df['Anomaly'] = df[parameter] - mean_value

        # Reference line value
        if reference_line == "Average":
            ref_value = 0
        elif reference_line == "20th Century Average":
            ref_value = df[(df['Year'] >= 1901) & (df['Year'] <= 2000)]['Anomaly'].mean()
        elif reference_line == "Custom Value":
            ref_value = custom_ref
        else:
            ref_value = None

        with st.expander("Data Preview"):
            st.dataframe(df.head(10))
            st.caption(f"Data range: {min_year} to {max_year} ({len(df)} years)")

        fig, ax = plt.subplots(figsize=(15, 6))

        # 🔹 Color normalization
        vmin = color_min if set_color_range else df['Anomaly'].min()
        vmax = color_max if set_color_range else df['Anomaly'].max()
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.get_cmap(colormap)

        # 🔹 Plot bars with colors based on anomaly
        colors = [cmap(norm(val)) for val in df['Anomaly']]
        ax.bar(df['Year'], df['Anomaly'], width=bar_width, color=colors)

        # 🔹 Match y-axis to colorbar range
        ax.set_ylim(vmin, vmax)

        # Reference line
        if ref_value is not None:
            ax.axhline(y=ref_value, color='black', linestyle='--', linewidth=2, alpha=0.7)
            ax.text(min_year, ref_value, f'Ref: {ref_value:.2f}', 
                    ha='left', va='bottom', fontsize=10, color='black')

        # 🔹 Trendline
        if show_trendline:
            coeffs = np.polyfit(df['Year'], df['Anomaly'], 1)
            trendline = np.poly1d(coeffs)
            ax.plot(df['Year'], trendline(df['Year']), 
                    color=trend_color, linestyle=trend_style, linewidth=2)

        # Year labels
        if show_years:
            years = df['Year'].unique()
            for i, year in enumerate(years):
                if year % year_step == 0:
                    ax.text(year, vmin - 0.05*(vmax-vmin), str(year),
                            rotation=90, ha='center', va='top', fontsize=9, alpha=0.7)

        # Title
        plt.title(f"{custom_title}: {parameter} ({min_year} - {max_year})", fontsize=18, pad=20)

        # Colorbar
        sm = ScalarMappable(norm=norm, cmap=cmap)
        cbar = fig.colorbar(sm, ax=ax, orientation='vertical', fraction=0.03, pad=0.02)
        cbar.set_label(f"{parameter} Anomaly", fontsize=12)

        st.pyplot(fig)

        # Save figure
        buf = io.BytesIO()
        if file_format == "PNG":
            plt.savefig(buf, format="png", dpi=dpi, bbox_inches='tight')
            mime_type, file_ext = "image/png", "png"
        elif file_format == "SVG":
            plt.savefig(buf, format="svg", bbox_inches='tight')
            mime_type, file_ext = "image/svg+xml", "svg"
        elif file_format == "PDF":
            plt.savefig(buf, format="pdf", bbox_inches='tight')
            mime_type, file_ext = "pdf", "pdf"

        buf.seek(0)
        filename = f"{custom_filename}_{parameter}_{min_year}-{max_year}.{file_ext}"

        st.download_button(
            label=f"Download Your Image ({file_format})",
            data=buf,
            file_name=filename,
            mime=mime_type
        )

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
else:
    st.markdown("""
    ## How to Use This App

    1. **Upload your data** in CSV format using the sidebar.
    2. Select the **parameter** to visualize.
    3. Customize the settings and **download** your climate bar plots.
    
    Your CSV file should contain:
    - `Year`: The year of measurement.
    - At least one parameter column (e.g., Temperature, Precipitation, etc.).
    """)
