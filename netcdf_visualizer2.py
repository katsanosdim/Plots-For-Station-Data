import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib import colors
import os
import time
import gc
import pandas as pd
import tempfile
import shutil

# Configure the app
st.set_page_config(layout="wide")
st.title("NetCDF Data Visualization Tool")
st.write(f"Created by **Dimitris Katsanos**")
# Create a dedicated temp directory
TEMP_DIR = "netcdf_temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

def cleanup_temp_dir():
    """Clean up temp directory by removing files older than 1 hour"""
    now = time.time()
    for filename in os.listdir(TEMP_DIR):
        filepath = os.path.join(TEMP_DIR, filename)
        if os.path.isfile(filepath):
            file_age = now - os.path.getmtime(filepath)
            if file_age > 3600:  # 1 hour
                try:
                    os.remove(filepath)
                except:
                    pass

def safe_remove(filepath):
    """Safely remove a file with multiple retries"""
    for i in range(5):
        try:
            os.remove(filepath)
            return True
        except PermissionError:
            time.sleep(0.5 * (i + 1))
            gc.collect()
    return False

def is_numeric(data):
    """Check if data is numeric"""
    return data.dtype.kind in 'iufc'  # Integer, unsigned, float, complex

def is_time_related(var_name):
    """Check if variable name indicates time data"""
    time_keywords = ['time', 'date', 'year', 'month', 'day', 'hour', 'minute', 'second']
    return any(kw in var_name.lower() for kw in time_keywords)

def process_data(data_array, scale_factor=40.0):
    """Process data with type checking and conversion"""
    if is_numeric(data_array):
        return data_array.values * scale_factor
    elif np.issubdtype(data_array.dtype, np.datetime64):
        st.warning("Datetime data detected - converting to ordinal numbers")
        return np.array([pd.Timestamp(t).toordinal() for t in data_array.values])
    else:
        raise ValueError(f"Unsupported data type: {data_array.dtype}")

def reduce_to_2d(data_array):
    """Intelligently reduce data to 2D"""
    if data_array.ndim == 2:
        return data_array
    
    # Create a dictionary of dimension indices
    dim_indices = {}
    for dim in data_array.dims:
        if dim not in ['latitude', 'longitude', 'lat', 'lon']:
            dim_indices[dim] = 0
    
    # Reduce dimensions
    return data_array.isel(**dim_indices) if dim_indices else data_array

# Sidebar controls
with st.sidebar:
    st.header("Visualization Settings")
    
    # File upload
    uploaded_file = st.file_uploader("Upload NetCDF file", type=['nc'])
    
    # Region selection
    st.subheader("Region Selection")
    col1, col2 = st.columns(2)
    with col1:
        lat_min = st.number_input("Min Latitude", value=34.0, step=1.0)
        lon_min = st.number_input("Min Longitude", value=19.5, step=1.0)
    with col2:
        lat_max = st.number_input("Max Latitude", value=42.0, step=1.0)
        lon_max = st.number_input("Max Longitude", value=28.5, step=1.0)
    
    # Plot customization
    st.subheader("Plot Settings")
    # Use text_area instead of text_input for multi-line support
    plot_title = st.text_area("Plot title", 
                             "First Line\nSecond Line", 
                             height=60,
                             help="Use '\\n' for a new line")
    #plot_title = st.text_input("Plot title", "Data Visualization")
    color_map = st.selectbox("Colormap", ["BrBG", "RdBu", "viridis", "plasma", "coolwarm", "jet"])
    vmin = st.number_input("Minimum value", value=-40.0, step=1.0)
    vmax = st.number_input("Maximum value", value=40.0, step=1.0)
    n_levels = st.slider("Number of color levels", 10, 100, 41)
    
    # Significance markers
    st.subheader("Statistical Significance")
    p_threshold = st.number_input("P-value threshold", value=0.05, step=0.01)
    marker_style = st.selectbox("Marker style", [".", "o", "x", "+", "s"])
    marker_size = st.slider("Marker size", 1, 10, 1)
    marker_color = st.color_picker("Marker color", "#000000")
    
    # Output options
    st.subheader("Output Options")
    scale_factor = st.number_input("Scale factor", value=40.0, step=1.0)
    output_name = st.text_input("Output filename (without extension)", "output_plot")
    dpi = st.slider("Image DPI", 100, 600, 300)
    
    # Temp file cleanup button
    if st.button("Cleanup Temporary Files"):
        cleanup_temp_dir()
        st.success("Temporary files cleaned up!")

# Display temp file info
temp_files = [f for f in os.listdir(TEMP_DIR) if f.endswith('.nc')]
st.sidebar.info(f"Temporary files: {len(temp_files)}")
if temp_files:
    with st.sidebar.expander("View Temp Files"):
        for file in temp_files[:10]:  # Show first 10
            st.write(file)
        if len(temp_files) > 10:
            st.write(f"...and {len(temp_files)-10} more")

# Main visualization
if uploaded_file is not None:
    # Clean up old temp files first
    cleanup_temp_dir()
    
    # Create temp file in our dedicated directory
    temp_path = os.path.join(TEMP_DIR, f"temp_upload_{int(time.time())}.nc")
    
    try:
        # Save uploaded file
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        # Open with multiple engine attempts
        engines = ['netcdf4', 'h5netcdf', 'scipy']
        data = None
        for engine in engines:
            try:
                data = xr.open_dataset(temp_path, engine=engine)
                break
            except Exception as e:
                st.warning(f"{engine} engine failed: {str(e)}")
                continue
        
        if data is None:
            st.error("Failed to open file with all available engines")
            st.stop()
        
        # Show dataset structure
        with st.expander("Dataset Structure"):
            st.write("**Variables:**", list(data.data_vars))
            st.write("**Dimensions:**", dict(data.dims))
            st.write("**Coordinates:**", list(data.coords))
            st.write("**Data types:**")
            for var in data.data_vars:
                st.write(f"- {var}: {data[var].dtype}")
        
        # Detect coordinate variables
        lat_var = next((v for v in ['latitude', 'lat', 'y'] if v in data.coords), None)
        lon_var = next((v for v in ['longitude', 'lon', 'x'] if v in data.coords), None)
        
        if not lat_var or not lon_var:
            st.error("Could not find latitude/longitude coordinates")
            st.stop()
        
        # Subset data
        subset = data.where(
            (data[lat_var] >= lat_min) & (data[lat_var] <= lat_max) &
            (data[lon_var] >= lon_min) & (data[lon_var] <= lon_max),
            drop=True
        )
        
        # Prepare variable lists excluding time-related variables
        spatial_vars = []
        all_vars = list(data.data_vars)
        
        for var in all_vars:
            # Skip time-related variables by name or type
            if is_time_related(var) or np.issubdtype(data[var].dtype, np.datetime64):
                continue
            
            # Skip 1D variables (likely coordinates)
            if data[var].ndim < 2:
                continue
                
            spatial_vars.append(var)
        
        # Ensure we have at least one spatial variable
        if not spatial_vars:
            st.error("No spatial variables found. Showing all variables as fallback.")
            spatial_vars = all_vars
        
        # Variable selection
        main_var = st.selectbox("Select main variable", spatial_vars)
        pvalue_options = ["None"] + spatial_vars
        pvalue_var = st.selectbox("Select p-value variable", pvalue_options)
        
        try:
            # Process main data
            main_data = reduce_to_2d(subset[main_var])
            processed_data = process_data(main_data, scale_factor)
            
            # Process coordinates
            lat = subset[lat_var].values
            lon = subset[lon_var].values
            
            # Handle different coordinate dimensions
            if lat.ndim == 1 and lon.ndim == 1:
                lon, lat = np.meshgrid(lon, lat)
            elif lat.ndim == 2 and lon.ndim == 2:
                pass  # Already 2D
            else:
                # Try to broadcast to 2D
                if lat.ndim == 1 and processed_data.ndim == 2:
                    lat = np.tile(lat[:, np.newaxis], (1, processed_data.shape[1]))
                if lon.ndim == 1 and processed_data.ndim == 2:
                    lon = np.tile(lon[np.newaxis, :], (processed_data.shape[0], 1))
            
            # Create plot
            fig, ax = plt.subplots(
                subplot_kw={'projection': ccrs.PlateCarree()}, 
                figsize=(12, 8)
            )
            
            # Add map features
            ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=0.5)
            ax.add_feature(cfeature.BORDERS.with_scale('10m'), linestyle='dashed')
            ax.add_feature(cfeature.LAND, facecolor='lightgray')
            ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
            ax.set_extent([lon_min, lon_max, lat_min, lat_max])
            
            # Plot data
            levels = np.linspace(vmin, vmax, n_levels)
            norm = colors.BoundaryNorm(levels, ncolors=256)
            
            # Handle different data dimensions
            try:
                if processed_data.shape == lat.shape:
                    mesh = ax.pcolormesh(lon, lat, processed_data, 
                                       cmap=color_map, norm=norm,
                                       shading='auto')
                else:
                    # Fallback to contourf if dimensions don't match
                    st.warning("Using contourf instead of pcolormesh due to dimension mismatch")
                    mesh = ax.contourf(lon, lat, processed_data, 
                                     levels=levels, cmap=color_map,
                                     norm=norm, extend='both')
            except Exception as e:
                st.error(f"Plotting failed: {str(e)}")
                st.stop()
            
            # Add significance markers if selected
            if pvalue_var != "None":
                try:
                    pdata = reduce_to_2d(subset[pvalue_var])
                    if is_numeric(pdata):
                        pdata_2d = pdata.values
                    else:
                        st.warning("P-value data is not numeric - skipping markers")
                        pdata_2d = None
                    
                    if pdata_2d is not None and pdata_2d.shape == processed_data.shape:
                        mask = pdata_2d < p_threshold
                        ax.scatter(lon[mask], lat[mask],
                                 color=marker_color,
                                 marker=marker_style,
                                 s=marker_size,
                                 label=f'p < {p_threshold}')
                        ax.legend(loc='lower left')
                    elif pdata_2d is not None:
                        st.warning("P-value dimensions don't match main data")
                except Exception as e:
                    st.error(f"Error processing p-value data: {str(e)}")
            
            # Add colorbar and title
            plt.colorbar(mesh, ax=ax, orientation='vertical')
            ax.set_title(plot_title, fontsize=14)
            
            # Show plot
            st.pyplot(fig)
            
            # Save option
            if st.button("Save Plot"):
                save_path = f"{output_name}.png"
                fig.savefig(save_path, dpi=dpi, bbox_inches='tight')
                with open(save_path, "rb") as f:
                    st.download_button(
                        "Download Plot",
                        f,
                        file_name=save_path,
                        mime="image/png"
                    )
        
        except Exception as e:
            st.error(f"Plotting error: {str(e)}")
            st.error(f"Main data type: {subset[main_var].dtype if main_var in subset else 'N/A'}")
            st.error(f"Main data shape: {processed_data.shape if 'processed_data' in locals() else 'N/A'}")
            st.error(f"Lat shape: {lat.shape if 'lat' in locals() else 'N/A'}")
            st.error(f"Lon shape: {lon.shape if 'lon' in locals() else 'N/A'}")
    
    except Exception as e:
        st.error(f"File error: {str(e)}")
    finally:
        # Try to remove temp file, but don't worry if we can't
        try:
            if os.path.exists(temp_path):
                # Delay removal to avoid immediate lock issues
                time.sleep(2)
                safe_remove(temp_path)
        except:
            pass
else:
    st.info("Please upload a NetCDF file")

# Cleanup instructions
with st.expander("Temporary File Management"):
    st.markdown("""
    **Managing Temporary Files:**
    
    The app creates temporary NetCDF files in the `netcdf_temp_files` directory.
    These should be automatically deleted, but if they accumulate:
    
    1. **Manual Cleanup**:
       ```python
       import shutil
       shutil.rmtree('netcdf_temp_files')
       ```
       
    2. **Automatic Cleanup**:
       - Files older than 1 hour are automatically removed
       - Click "Cleanup Temporary Files" in the sidebar
       
    3. **Preventing Buildup**:
       - The app cleans up before each new file upload
       - Uses a dedicated directory for easier management
       
    **Location:** `./netcdf_temp_files/`
    """)