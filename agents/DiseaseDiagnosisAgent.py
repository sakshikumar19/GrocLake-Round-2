import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, Any
import json
import os

base_dir = os.path.dirname(os.path.abspath(__file__))

file_path = os.path.join(base_dir, "..", "data", "tab5-crop_diseases.csv")

class CropDiseaseDiagnosisAgent:
    def __init__(self, vectorlake, modellake):
        self.vectorlake = vectorlake
        self.modellake = modellake
        self._disease_data = None
        self.disease_embedding_cache = {}
    
    def safe_split(self, value):
        """Safely split string values, handle non-string types."""
        if pd.isna(value):
            return []
        if isinstance(value, (int, float)):
            return [str(value)]
        try:
            return [x.strip() for x in str(value).split(';') if x.strip()]
        except:
            return [str(value)]
    
    def load_disease_data(self):
        """Load and preprocess disease data with error handling."""
        try:
            # Load disease data from CSV
            df = pd.read_csv(file_path)
            df = df.replace('N/A', np.nan)
            df.dropna(subset=['Symptoms'], inplace=True)
            
            # Create and cache embeddings
            for _, row in df.iterrows():
                metadata = {
                    "crop": row['Crop'],
                    "disease": row['Disease'],
                    "symptoms": self.safe_split(row['Symptoms']),
                    "identification": self.safe_split(row['Identification']),
                    "management": self.safe_split(row['Management']),
                    "severity": str(row.get('Severity', 'Unknown')),
                    "spread_rate": str(row.get('SpreadRate', 'Unknown'))
                }
                
                vector = {
                    "vector_type": "crop_disease",
                    "vector_document": f"{row['Crop']} {row['Disease']} {row['Symptoms']}",
                    "metadata": metadata
                }
                
                self.disease_embedding_cache[row['Disease']] = vector
                self.vectorlake.push(vector)
            
            self._disease_data = df
            return True
            
        except Exception as e:
            st.error(f"Error loading disease data: {str(e)}")
            # Log additional details for debugging
            st.error(f"Data types in DataFrame: {df.dtypes}")
            problematic_rows = df[~df['Symptoms'].apply(lambda x: isinstance(x, str))]
            if not problematic_rows.empty:
                st.error(f"Problematic rows:\n{problematic_rows}")
            return False
        
    def get_additional_information(self) -> Dict[str, Any]:
        """Collect additional information from user for better diagnosis."""
        st.markdown("### Additional Context")
        
        col1, col2 = st.columns(2)
        
        with col1:
            crop_type = st.selectbox(
                "Crop Type",
                ['Rice', 'Wheat', 'Corn', 'Potato', 'Tomato', 'Other'],
                help="Select your crop type"
            )
            
            if crop_type == 'Other':
                crop_type = st.text_input("Specify crop type")
            
            duration = st.select_slider(
                "Symptom Duration",
                options=['1-3 days', '4-7 days', '1-2 weeks', '2-4 weeks', 'Over a month'],
                help="How long have you noticed these symptoms?"
            )
            
            spread = st.select_slider(
                "Spread Rate",
                options=['Not spreading', 'Slowly', 'Moderately', 'Rapidly', 'Very rapidly'],
                help="How quickly are the symptoms spreading?"
            )
        
        with col2:
            affected_area = st.select_slider(
                "Affected Area",
                options=['<10%', '10-25%', '25-50%', '50-75%', '>75%'],
                help="Approximate percentage of crop affected"
            )
            
            weather = st.multiselect(
                "Recent Weather Conditions",
                ['Heavy rain', 'High humidity', 'Drought', 'Normal conditions', 'Temperature fluctuations'],
                help="Select all weather conditions from the past 2 weeks"
            )
            
            previous_treatment = st.text_area(
                "Previous Treatments (if any)",
                help="Describe any treatments already attempted"
            )
        
        return {
            "crop_type": crop_type,
            "duration": duration,
            "spread": spread,
            "affected_area": affected_area,
            "weather": weather,
            "previous_treatment": previous_treatment
        }

    def analyze_disease(self, symptoms: str, additional_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform RAG-based disease analysis."""
        # Prepare context for model
        context = f"""
        Crop Type: {additional_info['crop_type']}
        Symptoms: {symptoms}
        Duration: {additional_info['duration']}
        Spread Rate: {additional_info['spread']}
        Affected Area: {additional_info['affected_area']}
        Weather Conditions: {', '.join(additional_info['weather'])}
        Previous Treatments: {additional_info['previous_treatment']}
        """
        
        # Vector search for similar cases
        search_results = self.vectorlake.search({
            "query": f"{additional_info['crop_type']} {symptoms}",
            "vector_type": "crop_disease",
            "num_items": 3,
            "similarity_threshold": 0.7
        })
        
        # Prepare analysis prompt
        analysis_prompt = {
            "messages": [
                {
                    "role": "system",
                    "content": """You are an agricultural disease analyst specializing in precise, 
                    practical diagnosis and recommendations. Focus on actionable insights and clear, 
                    evidence-based analysis."""
                },
                {
                    "role": "user",
                    "content": f"""
                    Analyze the following case:
                    
                    {context}
                    
                    Similar cases in database: {json.dumps(search_results.get('results', []))}
                    
                    Provide a structured analysis including:
                    1. Initial Assessment
                       - Symptom analysis
                       - Environmental factors
                       - Progression assessment
                    
                    2. Potential Causes
                       - Primary disease candidates
                       - Contributing factors
                       - Risk assessment
                    
                    3. Management Recommendations
                       - Immediate actions
                       - Treatment options
                       - Preventive measures
                    
                    4. Monitoring Guidelines
                       - Key indicators to track
                       - Warning signs
                       - When to seek expert help
                    """
                }
            ]
        }
        
        # Get analysis from model
        analysis = self.modellake.chat_complete(analysis_prompt)
        
        return {
            "matched_diseases": search_results.get('results', []),
            "analysis": analysis.get('answer', 'Analysis unavailable'),
            "confidence_score": len(search_results.get('results', [])) / 3 * 100
        }


    def display_analysis_results(self, result: Dict[str, Any]):
        """Display analysis results in a structured format."""
        st.markdown("## 📊 Analysis Results")
        
        # Confidence score
        # st.progress(result['confidence_score']/100,
        #            text=f"Analysis Confidence: {result['confidence_score']:.2f}%")
        
        # Main analysis
        st.markdown("### 🔍 Detailed Analysis")
        st.write(result['analysis'])
        
        # Similar cases
        if result['matched_diseases']:
            st.markdown("### 📚 Similar Cases")
            for case in result['matched_diseases']:
                with st.expander(f"🌾 {case['metadata']['disease']} in {case['metadata']['crop']}"):
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown("**Common Symptoms:**")
                        for symptom in case['metadata']['symptoms']:
                            st.markdown(f"• {symptom}")
                    
                    with cols[1]:
                        st.markdown("**Management Strategies:**")
                        for strategy in case['metadata']['management']:
                            st.markdown(f"• {strategy}")
        
        # Final recommendations
        st.markdown("### 🎯 Key Takeaways")
        st.info("""
        Remember to:
        1. Document the progression of symptoms
        2. Take photos for tracking changes
        3. Follow management recommendations consistently
        4. Consult local agricultural experts for confirmation
        """)

    def get_additional_information(self) -> Dict[str, Any]:
        """Collect additional information using session state to prevent reloads."""
        if 'additional_info' not in st.session_state:
            st.session_state.additional_info = {
                'crop_type': 'Rice',
                'duration': '1-3 days',
                'spread': 'Not spreading',
                'affected_area': '<10%',
                'weather': [],
                'previous_treatment': ''
            }
        
        st.markdown("### Additional Context")
        
        col1, col2 = st.columns(2)
        
        with col1:
            crop_type = st.selectbox(
                "Crop Type",
                ['Rice', 'Wheat', 'Corn', 'Potato', 'Tomato', 'Other'],
                key='crop_select',
                help="Select your crop type"
            )
            
            if crop_type == 'Other':
                crop_type = st.text_input("Specify crop type", key='other_crop')
            
            duration = st.select_slider(
                "Symptom Duration",
                options=['1-3 days', '4-7 days', '1-2 weeks', '2-4 weeks', 'Over a month'],
                key='duration_slider',
                help="How long have you noticed these symptoms?"
            )
            
            spread = st.select_slider(
                "Spread Rate",
                options=['Not spreading', 'Slowly', 'Moderately', 'Rapidly', 'Very rapidly'],
                key='spread_slider',
                help="How quickly are the symptoms spreading?"
            )
        
        with col2:
            affected_area = st.select_slider(
                "Affected Area",
                options=['<10%', '10-25%', '25-50%', '50-75%', '>75%'],
                key='area_slider',
                help="Approximate percentage of crop affected"
            )
            
            weather = st.multiselect(
                "Recent Weather Conditions",
                ['Heavy rain', 'High humidity', 'Drought', 'Normal conditions', 'Temperature fluctuations'],
                key='weather_select',
                help="Select all weather conditions from the past 2 weeks"
            )
            
            previous_treatment = st.text_area(
                "Previous Treatments (if any)",
                key='treatment_text',
                help="Describe any treatments already attempted"
            )
        
        # Update session state
        st.session_state.additional_info = {
            "crop_type": crop_type,
            "duration": duration,
            "spread": spread,
            "affected_area": affected_area,
            "weather": weather,
            "previous_treatment": previous_treatment
        }
        
        return st.session_state.additional_info

    def display_interface(self):
        """Display the direct symptom input interface."""
        if 'symptoms' not in st.session_state:
            st.session_state.symptoms = ''
        
        st.markdown("### Describe Symptoms")
        symptoms = st.text_area(
            "Describe the symptoms in detail",
            value=st.session_state.symptoms,
            key='symptoms_area',
            placeholder="e.g., yellow spots on leaves, wilting stalks...",
            help="Be as specific as possible about appearance, location, and progression of symptoms"
        )
        
        if symptoms:
            additional_info = self.get_additional_information()
            
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("🔍 Analyze Disease", type="primary", key='analyze_btn'):
                    st.session_state.analyze_clicked = True
                    with st.spinner("Analyzing symptoms and generating recommendations..."):
                        if not self._disease_data:
                            self.load_disease_data()
                        result = self.analyze_disease(symptoms, additional_info)
                        self.display_analysis_results(result)

    def analyze_with_description(self, description: str):
        """Analyze disease based on VLM description."""
        if description:
            with st.expander("📷 VLM Analysis", expanded=True):
                st.info(description)
            
            additional_info = self.get_additional_information()
            
            if st.button("🔍 Analyze Disease", type="primary", key='vlm_analyze_btn'):
                with st.spinner("Analyzing symptoms and generating recommendations..."):
                    if not self._disease_data:
                        self.load_disease_data()
                    result = self.analyze_disease(description, additional_info)
                    self.display_analysis_results(result)