import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
import matplotlib.colors as mcolors
import os

# --- Sidebar Inputs ---
st.sidebar.header("Plot Settings")

uploaded_file = st.sidebar.file_uploader("Upload NetCDF file", type=["nc"])

# Customization options
title_line1 = st.sidebar.text_input("Plot Title Line 1", "1981 - 2020 annual precipitation trend [mm]")
title_line2 = st.sidebar.text_input("Plot Title Line 2", "Days with 1mm - 10mm [ERA5 Land Data]")

# Variable selection
data_var_options = ["tp", "rr", "precipitation", "precipitation_days_index_per_time_period", "trend"]
data_variable = st.sidebar.selectbox("Data Variable", data_var_options, index=0)
p_value_variable = st.sidebar.selectbox("P-value Variable", ["p_value"], index=0)

# Color settings
vmin = st.sidebar.number_input("Colorbar Min", value=-20.0, step=1.0)
vmax = st.sidebar.number_input("Colorbar Max", value=20.0, step=1.0)
cmap_name = st.sidebar.selectbox("Colormap", 
    ["BrBG", "RdBu", "viridis", "coolwarm", "plasma", "Spectral", "cividis", "inferno", "magma"])

# Figure settings
fig_width = st.sidebar.number_input("Figure Width", value=10.0, step=0.5)
fig_height = st.sidebar.number_input("Figure Height", value=6.0, step=0.5)
dpi = st.sidebar.number_input("DPI", value=300, step=50)

# Region settings
lat_min = st.sidebar.number_input("Latitude Min", value=34.0, step=0.5)
lat_max = st.sidebar.number_input("Latitude Max", value=42.0, step=0.5)
lon_min = st.sidebar.number_input("Longitude Min", value=19.5, step=0.5)
lon_max = st.sidebar.number_input("Longitude Max", value=28.5, step=0.5)

# Shapefile settings - GitHub compatible
shapefile_name = st.sidebar.selectbox(
    "Shapefile", 
    ["peri_new.shp", "custom_shapefile.shp"],  # Add your shapefile options here
    index=0
)

# Output settings
output_file = st.sidebar.text_input("Output filename (without .png)", "greece_plot")

# Additional options
scale_factor = st.sidebar.number_input("Scale Factor", value=40.0, step=1.0)
add_significance = st.sidebar.checkbox("Add statistical significance markers", value=True)

# --- Main App ---
st.title(":earth_africa: NetCDF Map Visualizer for Greece")
st.markdown("Make maps for Precipitation Trends etc. Created by **Dimitris Katsanos**")

if uploaded_file is not None:
    try:
        # Load the NetCDF file
        data = xr.open_dataset(uploaded_file, decode_times=False)
        
        # Display dataset info
        st.subheader("Dataset Information")
        st.write(f"Variables available: {list(data.data_vars.keys())}")
        st.write(f"Coordinates: {list(data.coords.keys())}")
        
        # Subset the data for the specified area
        subset = data.where(
            (data.latitude >= lat_min) & (data.latitude <= lat_max) &
            (data.longitude >= lon_min) & (data.longitude <= lon_max),
            drop=True
        )
        
        # Extract data
        try:
            pvalue_data = subset[p_value_variable].values[:, :]
        except:
            st.warning(f"P-value variable '{p_value_variable}' not found in dataset")
            pvalue_data = None
            
        try:
            precipitation_data = subset[data_variable].values[0, :, :] * scale_factor
        except:
            st.error(f"Data variable '{data_variable}' not found in dataset")
            st.stop()
            
        # Create 2D meshgrid for latitudes and longitudes
        lat = subset['latitude'].values
        lon = subset['longitude'].values
        lon_grid, lat_grid = np.meshgrid(lon, lat)
        
        # Create a map projection
        projection = ccrs.PlateCarree()
        
        # Plot the data
        fig, ax = plt.subplots(subplot_kw={'projection': projection}, figsize=(fig_width, fig_height))
        
        # Add map features
        ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=0.5)
        ax.add_feature(cfeature.BORDERS.with_scale('10m'), linestyle='dashed')
        ax.add_feature(cfeature.LAND, facecolor='lightgray')
        ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
        
        # Ensure the map focuses on the correct region
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
        
        # Define levels and normalization
        levels = np.linspace(vmin, vmax, num=41)
        norm = mcolors.BoundaryNorm(boundaries=levels, ncolors=256)
        
        # Plot the precipitation data
        filled_contour = ax.pcolormesh(lon_grid, lat_grid, precipitation_data, 
                                      cmap=cmap_name, norm=norm, shading='auto')
        
        # Add significance markers if requested and available
        if add_significance and pvalue_data is not None:
            mask = pvalue_data < 0.05
            ax.scatter(lon_grid[mask], lat_grid[mask], color='black', marker='.', 
                      s=1, label='Statistical Significant')
        
        # Overlay shapefile - GitHub compatible approach
        shapefile_path = os.path.join("shapefiles", shapefile_name)
        
        if os.path.exists(shapefile_path):
            try:
                shp = shpreader.Reader(shapefile_path, encoding="cp1253", errors="ignore")
                records = list(shp.records())
                
                for rec in records:
                    geom = rec.geometry
                    ax.add_geometries(
                        [geom],
                        crs=ccrs.PlateCarree(),
                        edgecolor="black",
                        facecolor="none",
                        linewidth=0.3
                    )
            except Exception as e:
                st.warning(f"Could not load shapefile: {e}")
        else:
            st.warning(f"Shapefile not found at {shapefile_path}. Using default coastlines instead.")
            # Add more detailed coastlines as fallback
            ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=1)
            ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=1)
        
        # Add a colorbar
        cb = plt.colorbar(filled_contour, ax=ax, orientation='vertical')
        cb.set_label(data_variable)
        
        # Add title with two lines
        full_title = f"{title_line1}\n{title_line2}"
        ax.set_title(full_title, fontsize=14)
        
        # Set latitude and longitude ticks
        ax.set_xticks(np.linspace(lon_min, lon_max, num=10))
        ax.set_yticks(np.linspace(lat_min, lat_max, num=9))
        
        # Add tick labels
        ax.set_xticklabels([f"{lon:.1f}°E" for lon in np.linspace(lon_min, lon_max, num=10)], fontsize=8)
        ax.set_yticklabels([f"{lat:.1f}°N" for lat in np.linspace(lat_min, lat_max, num=9)], fontsize=8)
        
        # Add legend if significance markers are present
        if add_significance and pvalue_data is not None:
            plt.legend(loc='lower left')
        
        # Display the plot
        st.pyplot(fig)
        
        # Save the plot
        out_file = f"{output_file}.png"
        plt.savefig(out_file, dpi=dpi, bbox_inches='tight')
        
        # Provide download button
        st.success(f"✅ Figure saved as {out_file}")
        with open(out_file, "rb") as f:
            st.download_button("Download PNG", f, file_name=out_file)
            
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.stop()
else:
    st.info("Please upload a NetCDF file to begin.")

# Add some helpful information
st.sidebar.markdown("---")
st.sidebar.info(
    """
    **GitHub Setup Instructions:**
    1. Create a folder named 'shapefiles' in your repository
    2. Add your shapefile (e.g., peri_new.shp) to this folder
    3. Make sure to include all related files (.shx, .dbf, etc.)
    4. The app will automatically look for shapefiles in the 'shapefiles' folder
    """

)

