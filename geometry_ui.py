import streamlit as st
import requests
import json

st.set_page_config(page_title="Rectangle Geometry Calculator", page_icon="📐")

st.title("📐 Rectangle Geometry Calculator")
st.subheader("Calculate area and perimeter of rectangles")

# Input fields for rectangle dimensions
length = st.number_input("Length", min_value=0.1, value=5.0, step=0.1)
width = st.number_input("Width", min_value=0.1, value=3.0, step=0.1)

# Create tabs for different calculation options
tab1, tab2, tab3 = st.tabs(["Area", "Perimeter", "Both"])

with tab1:
    if st.button("Calculate Area", key="area_btn"):
        with st.spinner("Calculating area..."):
            try:
                payload = {
                    "length": length,
                    "width": width
                }
                response = requests.post("http://localhost:8004/run", json=payload)
                
                if response.ok:
                    data = response.json()
                    st.success(f"Area calculation successful!")
                    
                    # Display the result
                    st.markdown("### Result")
                    st.markdown(data["result"])
                    
                    # Create a visual representation of the rectangle
                    st.markdown("### Visualization")
                    # Scale the rectangle for display
                    scale = 50
                    rect_height = min(width * scale, 300)
                    rect_width = min(length * scale, 600)
                    
                    # Draw the rectangle using HTML/CSS
                    st.markdown(f"""
                    <div style="
                        width: {rect_width}px;
                        height: {rect_height}px;
                        background-color: #4CAF50;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-weight: bold;
                    ">
                        {length} × {width}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Failed to calculate area: {str(e)}")

with tab2:
    if st.button("Calculate Perimeter", key="perimeter_btn"):
        with st.spinner("Calculating perimeter..."):
            try:
                payload = {
                    "length": length,
                    "width": width
                }
                response = requests.post("http://localhost:8005/run", json=payload)
                
                if response.ok:
                    data = response.json()
                    st.success(f"Perimeter calculation successful!")
                    
                    # Display the result
                    st.markdown("### Result")
                    st.markdown(data["result"])
                    
                    # Create a visual representation of the rectangle
                    st.markdown("### Visualization")
                    # Scale the rectangle for display
                    scale = 50
                    rect_height = min(width * scale, 300)
                    rect_width = min(length * scale, 600)
                    
                    # Draw the rectangle using HTML/CSS with highlighted perimeter
                    st.markdown(f"""
                    <div style="
                        width: {rect_width}px;
                        height: {rect_height}px;
                        border: 3px solid #FF5722;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: black;
                        font-weight: bold;
                    ">
                        {length} × {width}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Failed to calculate perimeter: {str(e)}")

with tab3:
    if st.button("Calculate Both", key="both_btn"):
        with st.spinner("Calculating area and perimeter..."):
            try:
                # Call both services
                area_payload = {"length": length, "width": width}
                perimeter_payload = {"length": length, "width": width}
                
                area_response = requests.post("http://localhost:8004/run", json=area_payload)
                perimeter_response = requests.post("http://localhost:8005/run", json=perimeter_payload)
                
                if area_response.ok and perimeter_response.ok:
                    area_data = area_response.json()
                    perimeter_data = perimeter_response.json()
                    
                    st.success("Calculations successful!")
                    
                    # Create columns for results
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### Area")
                        st.markdown(area_data["result"])
                    
                    with col2:
                        st.markdown("### Perimeter")
                        st.markdown(perimeter_data["result"])
                    
                    # Create a visual representation of the rectangle
                    st.markdown("### Visualization")
                    # Scale the rectangle for display
                    scale = 50
                    rect_height = min(width * scale, 300)
                    rect_width = min(length * scale, 600)
                    
                    # Draw the rectangle using HTML/CSS with area fill and perimeter border
                    st.markdown(f"""
                    <div style="
                        width: {rect_width}px;
                        height: {rect_height}px;
                        background-color: rgba(76, 175, 80, 0.5);
                        border: 3px solid #FF5722;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: black;
                        font-weight: bold;
                    ">
                        {length} × {width}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if not area_response.ok:
                        st.error(f"Area calculation error: {area_response.status_code} - {area_response.text}")
                    if not perimeter_response.ok:
                        st.error(f"Perimeter calculation error: {perimeter_response.status_code} - {perimeter_response.text}")
            except Exception as e:
                st.error(f"Failed to calculate: {str(e)}")

# Add some helpful information
st.markdown("---")
st.markdown("""
### How to use this calculator:
1. Enter the length and width of your rectangle
2. Choose which calculation you want to perform (Area, Perimeter, or Both)
3. Click the corresponding calculation button
4. View the results and visualization

### Formulas used:
- Area = Length × Width
- Perimeter = 2 × (Length + Width)
""")

# Add information about running the services
st.sidebar.title("Service Information")
st.sidebar.info("""
Make sure the following services are running:
- Area Agent: http://localhost:8004
- Perimeter Agent: http://localhost:8005

To start the services, run:
python -m agents.area_agent.__main__
python -m agents.perimeter_agent.__main__
```
""") 