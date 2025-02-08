import streamlit as st
import json
import subprocess
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

class ClimateAnalysisAgent:
    def __init__(self, vectorlake, modellake):
        self.vectorlake = vectorlake
        self.modellake = modellake
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.weather_fetch_script = os.path.join(base_dir, "..", "weather_fetch.mjs")
        
        # Install Node.js modules at startup
        try:
            project_root = os.path.dirname(self.weather_fetch_script)
            subprocess.run(
                ["npm", "install", "node-fetch@2.6.7", "moment@2.29.4", "query-string@7.1.1"],
                cwd=project_root,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            st.error(f"Failed to install Node.js modules: {e.stderr}")
        
        self.geolocator = Nominatim(user_agent="climate_analysis_app") 
               
        self.supported_languages = {
            'en': 'English',
            'hi': 'Hindi',
            'ml': 'Malayalam',
            'ta': 'Tamil',
            'te': 'Telugu'
        }

    def get_coordinates(self, location_name):
        """Get coordinates with increased timeout and retries"""
        try:
            # Configure geocoder with increased timeout
            self.geolocator = Nominatim(
                user_agent="climate_analysis_app",
                timeout=5  # Increased timeout
            )
            
            # Try up to 3 times
            for attempt in range(3):
                try:
                    location = self.geolocator.geocode(
                        location_name,
                        exactly_one=True,
                        language="en"
                    )
                    if location:
                        return {
                            'coords': f"{location.latitude},{location.longitude}",
                            'display_name': location.address
                        }
                except GeocoderTimedOut:
                    if attempt == 2:  # Last attempt
                        # Fallback to basic coordinates for known locations
                        fallback_coords = {
                            'varanasi': {'coords': '25.3176,82.9739', 'display_name': 'Varanasi, Uttar Pradesh, India'},
                            'delhi': {'coords': '28.6139,77.2090', 'display_name': 'Delhi, India'},
                            'mumbai': {'coords': '19.0760,72.8777', 'display_name': 'Mumbai, Maharashtra, India'},
                            # Add more as needed
                        }
                        
                        location_key = location_name.lower().strip()
                        if location_key in fallback_coords:
                            return fallback_coords[location_key]
                    
                    continue
            
            st.error("Unable to geocode location. Please try again or use a different location.")
            return None
            
        except Exception as e:
            st.error(f"Geocoding error: {str(e)}")
            return None
    
    def reflect_on_location(self, location_name):
        reflection_prompt = {
            "messages": [
                {
                    "role": "system",
                    "content": """You are a location validation expert. Your task is to:
1. Correct spelling errors
2. Standardize location format (City, State/Province, Country)
3. Remove any unnecessary details
4. Return ONLY the normalized location name without any explanation"""
                },
                {
                    "role": "user",
                    "content": f"Normalize this location: {location_name}"
                }
            ],
            "token_size": 512
        }
        
        try:
            normalized_location = self.modellake.chat_complete(reflection_prompt)
            return normalized_location['answer'].strip()
        except Exception as e:
            return location_name

    def fetch_weather_data(self, location_name):
        try:
            normalized_location = self.reflect_on_location(location_name)
            location_data = self.get_coordinates(normalized_location)
            
            if not location_data:
                st.error("Could not find coordinates for the location.")
                return None
                
            script_path = os.path.abspath(self.weather_fetch_script)
            project_root = os.path.dirname(script_path)
            
            try:
                # Install dependencies
                subprocess.run(
                    ["npm", "install"],
                    cwd=project_root,
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                # Run with --experimental-modules flag
                result = subprocess.run(
                    ["node", "--experimental-modules", script_path, "weather", location_data['coords']],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if result.stderr:
                    st.error(f"Script output error: {result.stderr}")
                    return None
                    
                weather_data = json.loads(result.stdout)
                return {'data': weather_data, 'location': location_data['display_name']}
                
            except subprocess.CalledProcessError as e:
                st.error(f"Error executing weather script: {e.stderr}")
                return None
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            return None
            
    def fetch_climate_events(self, location_name):
        try:
            location_data = self.get_coordinates(location_name)
            if not location_data:
                return None
                
            result = subprocess.run(
                ["node", self.weather_fetch_script, "events", location_data['coords']],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            if result.returncode != 0:
                st.error(f"Error fetching climate events: {result.stderr}")
                return None

            events_data = json.loads(result.stdout)
            return events_data
            
        except Exception as e:
            return None

    def generate_ai_insights(self, weather_data, events_data, lang_code='en'):
        try:
            # Get current weather values
            current_weather = {
                'temperature': f"{round((weather_data['data']['temperature'] - 32) * 5/9, 1)}°C",
                'windSpeed': f"{weather_data['data']['windSpeed']} mph",
                'precipitationIntensity': f"{weather_data['data']['precipitationIntensity']} mm/hr"
            }

            analysis_prompt = {
                "messages": [
                    {
                        "role": "system",
                        "content": """You are a climate and agricultural expert. Focus on:
    1. Current weather impact on agriculture
    2. Short-term weather recommendations
    3. Safety precautions if needed
    Use the provided temperature, wind speed, and precipitation data."""
                    },
                    {
                        "role": "user",
                        "content": f"""Current weather conditions in Varanasi:
    Temperature: {current_weather['temperature']}
    Wind Speed: {current_weather['windSpeed']}
    Precipitation: {current_weather['precipitationIntensity']}

    Provide a brief analysis focusing on agricultural and safety implications."""
                    }
                ],
                "token_size": 1024
            }
            
            insights = self.modellake.chat_complete(analysis_prompt)
            
            if lang_code != 'en':
                translation_prompt = {
                    "messages": [
                        {
                            "role": "system",
                            "content": f"Translate to {self.supported_languages[lang_code]}"
                        },
                        {
                            "role": "user",
                            "content": insights['answer']
                        }
                    ],
                    "token_size": 1024
                }
                insights = self.modellake.chat_complete(translation_prompt)

            return insights['answer']
        
        except Exception as e:
            return f"Error generating insights: {str(e)}"
    
    def analyze_climate_data(self, location_name):
        weather_data = self.fetch_weather_data(location_name)
        events_data = self.fetch_climate_events(location_name)

        if not weather_data:
            st.error("Failed to retrieve climate data.")
            return None

        enable_translation = st.checkbox("Enable Translation", key=f"translate_{location_name}")
        lang_code = 'en'
        if enable_translation:
            lang_code = st.selectbox(
                "Select Language",
                options=list(self.supported_languages.keys()),
                format_func=lambda x: self.supported_languages[x],
                key=f"lang_select_{location_name}"
            )

        # Extract weather values properly
        weather_values = (weather_data.get('data', {})
                        .get('data', {})
                        .get('timelines', [{}])[0]
                        .get('intervals', [{}])[0]
                        .get('values', {}))

        with st.spinner("Generating climate insights..."):
            insights = self.generate_ai_insights({'data': weather_values}, events_data, lang_code)
        
        st.subheader(f"📍 Climate Analysis for {weather_data.get('location', location_name)}")
        
        if weather_values:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Temperature", f"{round((weather_values.get('temperature', 0) - 32) * 5/9, 1)}°C")
            with col2:
                st.metric("Wind Speed", f"{weather_values.get('windSpeed', 0)} mph")
            with col3:
                st.metric("Precipitation", f"{weather_values.get('precipitationIntensity', 0)} mm/hr")
        else:
            st.warning("Weather data not available")
                    
        with st.expander("🔬 AI Climate Insights", expanded=True):
            st.markdown(insights)
        
        return weather_data