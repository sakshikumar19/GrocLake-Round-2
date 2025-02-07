import streamlit as st
import pandas as pd
import json
import plotly.express as px
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.abspath(os.path.join(base_dir, "..", "data", "tab1-crop_advisory.csv"))

print("Resolved file path:", file_path)

if not os.path.exists(file_path):
    print("Error: File not found!")

class CropAdvisoryAgent:
    def __init__(self, vectorlake, modellake):
        self.vectorlake = vectorlake
        self.modellake = modellake
        self._crop_data = None
        self.supported_languages = {
            'en': 'English',
            'hi': 'Hindi',
            'ml': 'Malayalam',
            'ta': 'Tamil',
            'te': 'Telugu'
        }

    @property
    def crop_data(self):
        if self._crop_data is None:
            self.load_data()
        return self._crop_data

    def load_data(self):
        """Load and preprocess crop advisory data"""
        try:
            df = pd.read_csv(file_path)
            
            # Adding derived features
            df['soil_quality_score'] = (df['ph'] - 7).abs()  # Optimal pH is 7
            df['climate_score'] = (df['temperature'] - df['temperature'].mean()) / df['temperature'].std() + \
                                (df['humidity'] - df['humidity'].mean()) / df['humidity'].std()
            
            # Create crop clusters
            unique_crops = df['crop recommendation'].unique()
            for crop in unique_crops:
                crop_data = df[df['crop recommendation'] == crop]
                vector = {
                    "vector_type": "crop_profile",
                    "vector_document": json.dumps({
                        "crop": crop,
                        "avg_temp": crop_data['temperature'].mean(),
                        "avg_humidity": crop_data['humidity'].mean(),
                        "avg_ph": crop_data['ph'].mean(),
                        "avg_rainfall": crop_data['rainfall'].mean(),
                        "nutrient_requirements": {
                            "N": crop_data['Nitrogen'].mean(),
                            "P": crop_data['Phosphorous'].mean(),
                            "K": crop_data['Potassium'].mean()
                        }
                    })
                }
                self.vectorlake.push(vector)
            
            self._crop_data = df
            return True
        except Exception as e:
            st.error(f"Error loading crop data: {str(e)}")
            return False

    def get_crop_recommendations(self, conditions, lang_code='en'):
        """Generate intelligent crop recommendations"""
        try:
            input_vector = {
                "N": conditions['nitrogen'],
                "P": conditions['phosphorus'],
                "K": conditions['potassium'],
                "temperature": conditions['temperature'],
                "humidity": conditions['humidity'],
                "ph": conditions['ph'],
                "rainfall": conditions['rainfall']
            }

            # Find similar crop profiles
            similar_crops = self.vectorlake.search({
                "query": json.dumps(input_vector),
                "vector_type": "crop_profile",
                "num_items": 3
            })

            # Generate AI insights
            analysis_prompt = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert agricultural advisor. Analyze the conditions and recommend suitable crops."
                    },
                    {
                        "role": "user",
                        "content": f"Given these conditions {json.dumps(input_vector)} and similar crop profiles {json.dumps(similar_crops)}, provide detailed cultivation recommendations."
                    }
                ],
                "token_size": 1024

            }
            
            recommendations = self.modellake.chat_complete(analysis_prompt)
            
            # Translate if needed
            if lang_code != 'en':
                translation_prompt = {
                    "messages": [
                        {
                            "role": "system",
                            "content": f"Translate the following agricultural advice to {self.supported_languages[lang_code]}"
                        },
                        {
                            "role": "user",
                            "content": recommendations['answer']
                        }
                        ],
                    "token_size": 1024
                }
                recommendations = self.modellake.chat_complete(translation_prompt)

            return recommendations['answer']

        except Exception as e:
            return f"Error generating recommendations: {str(e)}"

    def display_advisory_interface(self):
        """Create an interactive crop advisory interface"""
        
        # Create an interactive form for input
        with st.form("crop_conditions_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nitrogen = st.slider("Nitrogen (N)", 0, 140, 80)
                phosphorus = st.slider("Phosphorus (P)", 0, 140, 50)
                potassium = st.slider("Potassium (K)", 0, 140, 50)
                ph = st.slider("pH Level", 0.0, 14.0, 7.0, 0.1)

            with col2:
                temperature = st.slider("Temperature (°C)", 0.0, 40.0, 25.0, 0.1)
                humidity = st.slider("Humidity (%)", 0, 100, 65)
                rainfall = st.slider("Annual Rainfall (mm)", 0, 500, 200)

            # Language selection
            enable_translation = st.checkbox("Enable Translation")
            lang_code = 'en'
            if enable_translation:
                lang_code = st.selectbox(
                    "Select Language",
                    options=list(self.supported_languages.keys()),
                    format_func=lambda x: self.supported_languages[x]
                )

            # This submit button prevents automatic reruns
            submitted = st.form_submit_button("Get Recommendations")

        if submitted:
            conditions = {
                "nitrogen": nitrogen,
                "phosphorus": phosphorus,
                "potassium": potassium,
                "temperature": temperature,
                "humidity": humidity,
                "ph": ph,
                "rainfall": rainfall
            }

            with st.spinner("Analyzing conditions..."):
                recommendations = self.get_crop_recommendations(conditions, lang_code)
                
                # Display recommendations in an engaging way
                st.success("🎯 Crop Recommendations Generated!")
                st.markdown(recommendations)

                if self.crop_data is not None:
                    fig = px.scatter(
                        self.crop_data,
                        x='temperature',
                        y='humidity',
                        color='crop recommendation',
                        size='rainfall',
                        hover_data=['ph', 'Nitrogen', 'Phosphorous', 'Potassium'],
                        title='Crop Distribution by Growing Conditions'
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.subheader("📊 Optimal Growing Conditions")
                    optimal_conditions = self.crop_data.groupby('crop recommendation').agg({
                        'temperature': ['mean', 'std'],
                        'humidity': ['mean', 'std'],
                        'rainfall': ['mean', 'std']
                    }).round(2)
                    st.dataframe(optimal_conditions)