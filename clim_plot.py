import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
import io
from datetime import datetime

# Configure the app
st.set_page_config(page_title="Climate Plots Generator", page_icon="🌍", layout="wide")
st.title(":earth_africa: Plots Generator")
st.markdown("Make climate stripes plots for any parameter (Temperature, Precipitation, etc.). Created by **Dimitris Katsanos**")

# Sidebar with controls
with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"],
                                    help="First column must be 'Year', others are parameters")

    st.header("Visualization Settings")
    colormap = st.selectbox("Color Map", ["RdBu_r", "coolwarm", "seismic", "BrBG", "viridis", "plasma"],
                          index=0, help="Choose a color scheme for the stripes")

    stripe_width = st.slider("Stripe Width", 1, 20, 5, help="Width of each stripe (year)")
    stripe_height = st.slider("Stripe Height", 1, 20, 10, help="Height of the stripes")

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

    st.header("Save Options")
    custom_filename = st.text_input("Custom Filename (without extension)", value="climate_stripes")
    dpi = st.slider("Image Quality (DPI)", 100, 600, 300)
    file_format = st.selectbox("File Format", ["PNG", "SVG", "PDF"], index=0)

    st.markdown("---")
    st.caption("Climate stripes visualize anomalies relative to the mean for any parameter.")

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

        # Let user choose parameter
        parameter = st.selectbox("Select parameter to plot", param_columns)

        # Sort by year
        df = df.sort_values('Year').reset_index(drop=True)
        min_year = df['Year'].min()
        max_year = df['Year'].max()

        # Compute anomalies
        mean_value = df[parameter].mean()
        df['Anomaly'] = df[parameter] - mean_value

        # Reference line value
        if reference_line == "Average":
            ref_value = 0  # Anomaly mean is always 0
        elif reference_line == "20th Century Average":
            ref_value = df[(df['Year'] >= 1901) & (df['Year'] <= 2000)]['Anomaly'].mean()
        elif reference_line == "Custom Value":
            ref_value = custom_ref
        else:
            ref_value = None

        with st.expander("Data Preview"):
            st.dataframe(df.head(10))
            st.caption(f"Data range: {min_year} to {max_year} ({len(df)} years)")

        fig, ax = plt.subplots(figsize=(15, stripe_height * 0.5))

        vmin = color_min if set_color_range else df['Anomaly'].min()
        vmax = color_max if set_color_range else df['Anomaly'].max()
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.get_cmap(colormap)

        for i, row in df.iterrows():
            color = cmap(norm(row['Anomaly']))
            ax.fill_between([i, i + 1], 0, 1, color=color)

        if ref_value is not None:
            ref_index = np.interp(ref_value, [vmin, vmax], [0, 1])
            ax.axhline(y=ref_index, color='black', linestyle='--', linewidth=2, alpha=0.7)
            ax.text(0, ref_index + 0.02, f'Reference: {ref_value:.2f}', 
                    ha='left', va='bottom', fontsize=12, transform=ax.get_yaxis_transform())

        ax.set_xlim(0, len(df))
        ax.set_ylim(0, 1)
        ax.set_axis_off()

        if show_years:
            years = df['Year'].unique()
            for i, year in enumerate(years):
                if year % year_step == 0:
                    ax.text(i + 0.5, -0.05, str(year), 
                            rotation=90, ha='center', va='top', fontsize=10, alpha=0.7)

        plt.title(f"{custom_title}: {parameter} ({min_year} - {max_year})", fontsize=18, pad=20)

        # Colorbar
        sm = ScalarMappable(norm=norm, cmap=cmap)
        cbar = fig.colorbar(sm, ax=ax, orientation='vertical', fraction=0.03, pad=0.02)
        cbar.set_label(f'% Anomaly', fontsize=12)
        #cbar.set_label(f'{parameter} % Anomaly', fontsize=12)

        st.pyplot(fig)

        # Save figure
        buf = io.BytesIO()
        if file_format == "PNG":
            plt.savefig(buf, format="png", dpi=dpi, bbox_inches='tight')
            mime_type = "image/png"
            file_ext = "png"
        elif file_format == "SVG":
            plt.savefig(buf, format="svg", bbox_inches='tight')
            mime_type = "image/svg+xml"
            file_ext = "svg"
        elif file_format == "PDF":
            plt.savefig(buf, format="pdf", bbox_inches='tight')
            mime_type = "application/pdf"
            file_ext = "pdf"

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
    3. Customize the settings and **download** your climate stripes.
    
    Your CSV file should contain:
    - `Year`: The year of measurement.
    - At least one parameter column (e.g., Temperature, Precipitation, etc.).
    """)
