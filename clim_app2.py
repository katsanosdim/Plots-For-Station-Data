import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
import io
from datetime import datetime

# Configure the app
st.set_page_config(page_title="Plots Generator", page_icon="🌍", layout="wide")
st.title(":earth_africa: Plots Generator")
st.markdown("Make climate stripes from temperature data. Created by **Dimitris Katsanos**")

# Sidebar with controls
with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"],
                                    help="File should contain 'Year' and 'Temperature' columns")

    st.header("Visualization Settings")
    colormap = st.selectbox("Color Map", ["RdBu_r", "coolwarm", "seismic", "viridis", "plasma"],
                          index=0, help="Choose a color scheme for the stripes")

    stripe_width = st.slider("Stripe Width", 1, 20, 5, help="Width of each stripe (year)")
    stripe_height = st.slider("Stripe Height", 1, 20, 10, help="Height of the stripes")

    show_years = st.checkbox("Show Years", True, help="Display year labels")
    year_step = st.slider("Year Label Step", 1, 20, 5, help="Show every Nth year")

    st.header("Title & Colorbar")
    custom_title = st.text_input("Custom Title", value="Climate Stripes")
    set_color_range = st.checkbox("Set Colorbar Range")
    if set_color_range:
        color_min = st.number_input("Colorbar Min", value=-2.0, step=0.5)
        color_max = st.number_input("Colorbar Max", value=2.0, step =0.5)

    reference_line = st.selectbox("Reference Line",
                                 ["None", "Average", "20th Century Average", "Custom Value"],
                                 index=0, help="Add a reference line to the visualization")

    if reference_line == "Custom Value":
        custom_ref = st.number_input("Reference Value", value=0.0)

    st.header("Save Options")
    custom_filename = st.text_input("Custom Filename (without extension)", value="climate_stripes")
    dpi = st.slider("Image Quality (DPI)", 100, 600, 300)
    file_format = st.selectbox("File Format", ["PNG", "SVG", "PDF"], index=0)

    st.markdown("---")
    st.caption("Climate stripes visualize annual temperature anomalies relative to a baseline period. \
               Each stripe represents one year of temperature data.")

# Example data for download
example_data = pd.DataFrame({
    'Year': range(1850, 2024),
    'Temperature': np.random.normal(0, 0.8, 174).cumsum() + np.random.rand(174)*0.5
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

        if 'Year' not in df.columns or 'Temperature' not in df.columns:
            st.error("CSV must contain 'Year' and 'Temperature' columns")
            st.stop()

        df = df.sort_values('Year').reset_index(drop=True)
        min_year = df['Year'].min()
        max_year = df['Year'].max()

        if reference_line == "Average":
            ref_value = df['Temperature'].mean()
        elif reference_line == "20th Century Average":
            ref_value = df[(df['Year'] >= 1901) & (df['Year'] <= 2000)]['Temperature'].mean()
        elif reference_line == "Custom Value":
            ref_value = custom_ref
        else:
            ref_value = None

        with st.expander("Data Preview"):
            st.dataframe(df.head(10))
            st.caption(f"Data range: {min_year} to {max_year} ({len(df)} years)")

        fig, ax = plt.subplots(figsize=(15, stripe_height*0.5))

        vmin = color_min if set_color_range else df['Temperature'].min()
        vmax = color_max if set_color_range else df['Temperature'].max()
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.get_cmap(colormap)

        for i, row in df.iterrows():
            color = cmap(norm(row['Temperature']))
            ax.fill_between([i, i+1], 0, 1, color=color)

        if ref_value is not None:
            ref_index = np.interp(ref_value, [vmin, vmax], [0, 1])
            ax.axhline(y=ref_index, color='black', linestyle='--', linewidth=2, alpha=0.7)
            ax.text(0, ref_index + 0.02, f'Reference: {ref_value:.2f}°C', 
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

        plt.title(f"{custom_title}: {min_year} - {max_year}", fontsize=18, pad=20)

        #cax = fig.add_axes([0.15, 0.85, 0.7, 0.03])
        #sm = ScalarMappable(norm=norm, cmap=cmap)
        #fig.colorbar(sm, cax=cax, orientation='horizontal', label='Temperature Anomaly (°C)')

        # Add vertical colorbar on the right
        sm = ScalarMappable(norm=norm, cmap=cmap)
        cbar = fig.colorbar(sm, ax=ax, orientation='vertical', fraction=0.03, pad=0.02)
        cbar.set_label('Temperature Anomaly (°C)', fontsize=12)

        st.pyplot(fig)

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
        current_date = datetime.now().strftime("%Y-%m-%d")
        #filename = f"climate_stripes_{min_year}-{max_year}_{current_date}.{file_ext}"
        #filename = f"{custom_filename}_{min_year}-{max_year}_{current_date}.{file_ext}"
        filename = f"{custom_filename}_{min_year}-{max_year}.{file_ext}"


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

    1. **Upload your data** in CSV format using the sidebar
    2. **Customize** the visualization settings
    3. **Download** your climate stripes visualization

    Your CSV file should contain two columns:
    - `Year`: The year of the temperature measurement
    - `Temperature`: The temperature anomaly value (in °C)
    """)

