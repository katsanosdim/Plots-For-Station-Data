import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title('NOA Data Explorer')
st.text('This is a web app to explore NOA Daily data')

st.sidebar.title('Navigation')
uploaded_file = st.sidebar.file_uploader('Upload your file here')

if uploaded_file:
    st.header('NOA Daily Data Statistics')
    df = pd.read_csv(uploaded_file)
    # Normalize column names
    df.columns = df.columns.str.strip().str.upper()

    st.write("Columns in your file:", df.columns.tolist())
    st.write(df.describe())

    st.header('Data Header')
    st.write(df.head())

# Let the user pick a column to plot *This one worked
    #selected_column = st.selectbox("Select a column to plot against DAY", options=[col for col in df.columns if col != 'DAY'])
# Convert columns to numeric & create datetime
df['YEAR'] = pd.to_numeric(df['YEAR'], errors='coerce')
df['MONTH'] = pd.to_numeric(df['MONTH'], errors='coerce')
df['DAY'] = pd.to_numeric(df['DAY'], errors='coerce')
df['DATE'] = pd.to_datetime(df[['YEAR', 'MONTH', 'DAY']], errors='coerce')
# Plot the selected column
   # fig, ax = plt.subplots()
    #ax.plot(df['DAY'], df[selected_column], marker='o')
    #ax.set_xlabel('DAY')
   # ax.set_ylabel(selected_column.title())
    #ax.set_title(f'{selected_column.title()} vs. DAY')
# Variable to plot
variable = st.selectbox("Select a variable to plot", [col for col in df.columns if col not in ['YEAR', 'MONTH', 'DAY', 'DATE']])

# Month filter
months = ['All'] + sorted(df['MONTH'].dropna().unique().astype(int).tolist())
selected_month = st.selectbox("Select a month", months)

if selected_month != 'All':
    df_filtered = df[df['MONTH'] == selected_month]
else:
    df_filtered = df

df_filtered = df_filtered.dropna(subset=['DATE', variable])    
#    fig, ax = plt.subplots(1,1)
    #ax.scatter(x=df['DAY'], y=df['MAXTEMP'])
#    ax.plot(df['DAY'], df['MAXTEMP'], marker='o')


#    ax.set_xlabel('Day')
#    ax.set_ylabel('Max Temperature')
#    ax.set_title('Daily Max Temperature')
# Plot
fig, ax = plt.subplots()
ax.plot(df_filtered['DATE'], df_filtered[variable], marker='o', markersize=3)
ax.set_xlabel('Date')
ax.set_ylabel(variable.title())
ax.set_title(f"{variable.title()} for Month: {selected_month}" if selected_month != 'All' else f"{variable.title()} - All Months")
ax.grid(True)
fig.autofmt_xdate()
st.pyplot(fig)