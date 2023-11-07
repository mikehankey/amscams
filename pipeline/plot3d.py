import plotly.graph_objects as go

# Sample data: latitudes, longitudes, and elevations
latitudes = [40.7128, 34.0522, 41.8781, 37.7749]
longitudes = [-74.0060, -118.2437, -87.6298, -122.4194]
elevations = [10, 20, 15, 25]

# Create the 3D scatter plot
fig = go.Figure()

# Add the Earth sphere
fig.add_trace(go.Surface(
    z=[[0, 0], [0, 0]],
    showscale=False,
    colorscale="Blues",
    cmin=0,
    cmax=1,
    opacity=0.4,
    surfacecolor=[[0, 1], [1, 0]]
))

# Add the scatter points for cities
fig.add_trace(go.Scatter3d(
    x=latitudes,
    y=longitudes,
    z=elevations,
    mode="markers",
    marker=dict(
        size=10,
        color=elevations,
        colorscale="Viridis"
    )
))

# Set the aspect ratio and axis labels
fig.update_layout(
    scene=dict(
        aspectmode="cube",
        xaxis=dict(title="Latitude"),
        yaxis=dict(title="Longitude"),
        zaxis=dict(title="Elevation")
    )
)

# Show the plot
fig.show()
