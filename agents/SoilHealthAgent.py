from geopy.geocoders import Nominatim
import streamlit as st
import pandas as pd
import json
import plotly.express as px
import os

base_dir = os.path.dirname(os.path.abspath(__file__))

file_path = os.path.join(base_dir, "..", "data", "tab2-soil-health.csv")

class SoilHealthAgent:
    def __init__(self, vectorlake, modellake):
        self.vectorlake = vectorlake
        self.modellake = modellake
        self.soil_data = None
        self.geolocator = Nominatim(user_agent="smart_farming_app")
        self.load_data()

    def load_data(self):
        """Load and preprocess soil health data"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError("Soil health data file not found")

            # Load the data
            df = pd.read_csv(file_path)
            
            # Check if DataFrame is empty
            if df.empty:
                raise ValueError("Soil health data file is empty")

            # Reset index to handle any index-related issues
            df = df.reset_index(drop=True)
            
            # Clean and preprocess data
            # Fill missing Region with Site_name if available
            df['Region'] = df['Region'].fillna(df['Site_name'])
            
            # Fill missing numerical values with median (more robust than mean)
            df['Soil_BD'] = pd.to_numeric(df['Soil_BD'], errors='coerce')
            df['MAT'] = pd.to_numeric(df['MAT'], errors='coerce')
            df['MAP'] = pd.to_numeric(df['MAP'], errors='coerce')
            
            df['Soil_BD'].fillna(df['Soil_BD'].median(), inplace=True)
            df['MAT'].fillna(df['MAT'].median(), inplace=True)
            df['MAP'].fillna(df['MAP'].median(), inplace=True)
            
            # Ensure critical columns are not null
            df['Soil_type'] = df['Soil_type'].fillna('Unknown')
            df['Soil_drainage'] = df['Soil_drainage'].fillna('Moderate')
            df['Site_name'] = df['Site_name'].fillna('Unknown Site')
            df['Region'] = df['Region'].fillna('Unknown Region')
            
            # Drop any remaining rows with all null values
            df = df.dropna(how='all')
            
            # Create soil type profiles
            for soil_type in df['Soil_type'].unique():
                soil_data = df[df['Soil_type'] == soil_type]
                vector = {
                    "vector_type": "soil_profile",
                    "vector_document": json.dumps({
                        "soil_type": soil_type,
                        "avg_bd": float(soil_data['Soil_BD'].mean()),
                        "avg_mat": float(soil_data['MAT'].mean()),
                        "avg_map": float(soil_data['MAP'].mean()),
                        "typical_drainage": soil_data['Soil_drainage'].mode()[0]
                    })
                }
                self.vectorlake.push(vector)
            
            # Add derived metrics
            df['soil_quality_score'] = self._calculate_soil_quality_score(df)
            
            self.soil_data = df  # Changed from self._soil_data to self.soil_data
            return True

        except Exception as e:
            st.error(f"Error loading soil data: {str(e)}")
            self._initialize_default_data()
            return False

    def _calculate_soil_quality_score(self, df):
        """Calculate a soil quality score based on available metrics"""
        # Normalize values between 0 and 1
        bd_score = 1 - abs(df['Soil_BD'] - 1.3) / 0.5  # Optimal BD around 1.3
        bd_score = bd_score.clip(0, 1)
        
        # Simple scoring system
        return (bd_score * 100).round()

    def _initialize_default_data(self):
        """Initialize with default values if data loading fails"""
        self.soil_data = pd.DataFrame({  # Changed from self._soil_data to self.soil_data
            'Soil_type': ['Sandy loam', 'Alluvial loam', 'Clay loam'],
            'Soil_drainage': ['Dry', 'Wet', 'Moderate'],
            'Soil_BD': [1.35, 1.22, 1.28],
            'MAT': [26.0, 22.9, 24.5],
            'MAP': [1190.0, 1593.0, 1350.0],
            'Region': ['Default Region 1', 'Default Region 2', 'Default Region 3'],
            'Site_name': ['Default Site 1', 'Default Site 2', 'Default Site 3'],
            'soil_quality_score': [85, 78, 82]
        })
        st.warning("Using default soil data due to loading error.")
        
    def display_soil_analysis_interface(self):
        """Create an interactive soil analysis interface"""
        # Display data source information
        st.info("ℹ️ Analyzing soil health data from research sites across India")

        # Supported languages (matching crop advisory agent)
        supported_languages = {
            'en': 'English',
            'hi': 'Hindi',
            'ml': 'Malayalam',
            'ta': 'Tamil',
            'te': 'Telugu'
        }

        # Create a form to prevent automatic reruns
        with st.form("soil_analysis_form"):
            # Create two columns for the main interface
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Soil characteristics input
                soil_type = st.selectbox(
                    "🌱 Soil Type",
                    options=sorted(self.soil_data['Soil_type'].unique())
                )
                
                drainage = st.selectbox(
                    "💧 Soil Drainage",
                    options=sorted(self.soil_data['Soil_drainage'].unique())
                )
                
                # Location input (new addition)
                location = st.text_input("📍 Location (optional)", placeholder="Enter city or region")
            
            with col2:
                # Display current soil quality score
                current_soil = self.soil_data[self.soil_data['Soil_type'] == soil_type].iloc[0]
                st.metric(
                    "Soil Quality Score",
                    f"{current_soil['soil_quality_score']:.0f}%",
                    delta=None,
                    help="Score based on soil density and other characteristics"
                )

            # Language selection
            enable_translation = st.checkbox("Enable Translation")
            lang_code = 'en'
            if enable_translation:
                lang_code = st.selectbox(
                    "Select Language",
                    options=list(supported_languages.keys()),
                    format_func=lambda x: supported_languages[x]
                )

            # Analysis button inside the form
            submitted = st.form_submit_button("🔍 Analyze Soil Health")

        # Only process when form is submitted
        if submitted:
            with st.spinner("Analyzing soil characteristics..."):
                # Prepare input for AI recommendation
                input_vector = {
                    "soil_type": soil_type,
                    "drainage": drainage,
                    "soil_density": current_soil['Soil_BD'],
                    "temperature": current_soil['MAT'],
                    "precipitation": current_soil['MAP']
                }

                # Generate AI recommendations
                analysis_prompt = {
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are an expert agricultural soil scientist. Provide comprehensive soil health analysis and recommendations."""
                        },
                        {
                            "role": "user",
                            "content": f"Analyze these soil conditions: {json.dumps(input_vector)}"
                        }
                    ],
                    "token_size": 1024
                }
                
                # Get recommendations from modellake
                recommendations = self.modellake.chat_complete(analysis_prompt)
                
                # Translate if needed
                if lang_code != 'en':
                    translation_prompt = {
                        "messages": [
                            {
                                "role": "system",
                                "content": f"Translate the following soil health recommendations to {supported_languages[lang_code]}"
                            },
                            {
                                "role": "user",
                                "content": recommendations['answer']
                            }
                        ],
                        "token_size": 1024
                    }
                    recommendations = self.modellake.chat_complete(translation_prompt)

                # Display metrics
                m1, m2, m3 = st.columns(3)
                
                with m1:
                    st.metric(
                        "Soil Density",
                        f"{current_soil['Soil_BD']:.2f} g/cm³",
                        delta="Optimal" if 1.1 <= current_soil['Soil_BD'] <= 1.4 else "Needs attention"
                    )
                
                with m2:
                    st.metric(
                        "Temperature",
                        f"{current_soil['MAT']:.1f}°C",
                        delta="Normal range" if 20 <= current_soil['MAT'] <= 30 else "Outside optimal range"
                    )
                
                with m3:
                    st.metric(
                        "Precipitation",
                        f"{current_soil['MAP']:.0f} mm",
                        delta="Adequate" if current_soil['MAP'] >= 1000 else "Low"
                    )

                # Create tabs for detailed analysis
                tab1, tab2 = st.tabs(["📊 Analysis", "💡 Recommendations"])
                
                with tab1:
                    # Soil distribution plot
                    fig = px.box(
                        self.soil_data,
                        x='Soil_type',
                        y=['Soil_BD', 'MAT', 'MAP'],
                        title='Soil Characteristics Distribution'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Regional statistics
                    st.subheader("Regional Soil Profiles")
                    regional_stats = self.soil_data.groupby('Soil_type').agg({
                        'Soil_BD': ['mean', 'std'],
                        'MAT': ['mean', 'std'],
                        'MAP': ['mean', 'std']
                    }).round(2)
                    st.dataframe(regional_stats)
                
                with tab2:
                    # Display AI-generated recommendations
                    st.markdown(recommendations['answer'])

                    # Optional location-based analysis if location provided
                    if location:
                        location_analysis, geo_data = self.analyze_soil_characteristics(
                            location, soil_type, drainage
                        )
                        if geo_data:
                            st.subheader(f"🌍 Location Insights for {location}")
                            st.write(location_analysis)
                        
    def _generate_recommendations(self, soil_data):
        """Generate specific recommendations based on soil characteristics"""
        recommendations = {
            "Management Practices": [],
            "Improvement Suggestions": [],
            "Crop Recommendations": []
        }
        
        # Soil density recommendations
        if soil_data['Soil_BD'] > 1.4:
            recommendations["Management Practices"].append(
                "Soil is compacted. Consider deep tillage and adding organic matter."
            )
        elif soil_data['Soil_BD'] < 1.1:
            recommendations["Management Practices"].append(
                "Soil is loose. Consider compaction management and soil stabilization."
            )
        
        # Drainage recommendations
        if soil_data['Soil_drainage'] == 'Dry':
            recommendations["Improvement Suggestions"].extend([
                "Implement mulching to retain moisture",
                "Consider installing drip irrigation",
                "Add organic matter to improve water retention"
            ])
        elif soil_data['Soil_drainage'] == 'Wet':
            recommendations["Improvement Suggestions"].extend([
                "Improve drainage through channels or raised beds",
                "Consider installing drainage tiles",
                "Choose water-tolerant crops"
            ])
        
        # Crop recommendations based on soil type
        soil_crop_map = {
            'Sandy loam': ["Carrots", "Potatoes", "Beans", "Lettuce"],
            'Alluvial loam': ["Rice", "Wheat", "Maize", "Vegetables"],
            'Clay loam': ["Wheat", "Cotton", "Soybean", "Sorghum"]
        }
        
        if soil_data['Soil_type'] in soil_crop_map:
            recommendations["Crop Recommendations"].extend(
                f"Suitable for {crop}" for crop in soil_crop_map[soil_data['Soil_type']]
            )
        
        return recommendations
    
    def analyze_soil_characteristics(self, location, soil_type, drainage):
        """Analyze soil characteristics and provide recommendations"""
        try:
            # Geocode location
            location_data = self.geolocator.geocode(location)
            if location_data:
                # Find similar soil profiles
                query_vector = {
                    "location": {
                        "lat": location_data.latitude,
                        "lon": location_data.longitude
                    },
                    "soil_type": soil_type,
                    "drainage": drainage
                }

                similar_profiles = self.vectorlake.search({
                    "query": json.dumps(query_vector),
                    "vector_type": "soil_profile",
                    "num_items": 3
                })

                # Generate AI analysis
                analysis_prompt = {
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are an expert soil scientist. Analyze soil characteristics and provide detailed recommendations
                            focusing on:
                            1. Soil fertility and quality assessment
                            2. Recommended crops for this soil type
                            3. Soil management practices
                            4. Potential challenges and solutions"""
                        },
                        {
                            "role": "user",
                            "content": f"Analyze these soil conditions: {json.dumps(query_vector)} with similar profiles: {json.dumps(similar_profiles)}"
                        }
                    ],
                    "token_size": 1024

                }
                
                analysis = self.modellake.chat_complete(analysis_prompt)
                return analysis['answer'], location_data
            else:
                return "Location not found. Please enter a valid location.", None

        except Exception as e:
            return f"Error analyzing soil: {str(e)}", None