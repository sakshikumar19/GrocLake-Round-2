import streamlit as st
import streamlit.components.v1 as components

from groclake.vectorlake import VectorLake
from groclake.modellake import ModelLake
from groclake.cataloglake import CatalogLake
from groclake.datalake import DataLake
from groclake.agentlake import AgentLake

import logging
from dotenv import load_dotenv
import os

from agents.DiseaseDiagnosisAgent import CropDiseaseDiagnosisAgent
from agents.CropAdvisoryAgent import CropAdvisoryAgent
from agents.MarketInsightsAgent import MarketInsightsAgent
from agents.ClimateAnalysisAgent import ClimateAnalysisAgent
from agents.SoilHealthAgent import SoilHealthAgent
from agents.GuideAgent import GuideAgent

load_dotenv()

class SmartFarmingAgents:
    def __init__(self):
        # Initialize GrocLake tools
        self.vectorlake = VectorLake()
        self.modellake = ModelLake()
        self.cataloglake = CatalogLake()
        self.datalake = DataLake()
        self.agentlake = AgentLake()

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Initialize specialized agents
        self.soil_analyst = SoilHealthAgent(self.vectorlake, self.modellake)
        self.crop_advisor = CropAdvisoryAgent(self.vectorlake, self.modellake)
        self.market_intelligence = MarketInsightsAgent(self.vectorlake, self.modellake)
        self.climate_predictor = ClimateAnalysisAgent(self.vectorlake, self.modellake)
        self.disease_detective = CropDiseaseDiagnosisAgent(self.vectorlake, self.modellake)        
        self.guide_agent = GuideAgent(self.modellake)        

    def load_gradio_component(self):
        """Load the Gradio VLM component."""
        components.html(
            """
            <div style="height: 800px; overflow-y: scroll; border: 1px solid #ccc; border-radius: 10px; padding: 10px;">
                <script type="module" src="https://gradio.s3-us-west-2.amazonaws.com/4.42.0/gradio.js"></script>
                <gradio-app src="https://ganymedenil-qwen2-vl-7b.hf.space" style="width: 100%; height: 100%;"></gradio-app>
            </div>
            """,
            height=850  # Slightly larger than container to account for padding
        ) 
        
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    background_image = os.path.join(base_dir, "agriculture-industry.jpg")

    st.markdown("""
    <style>
    /* Main container background */
    .stMain.st-emotion-cache-bm23a.ekr3hm11 {
        background-image: url('agriculture-industry.jpg');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        position: relative;
    }

    /* Semi-transparent overlay */
    .stMain.st-emotion-cache-bm23a.ekr3hm11::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(255, 255, 255, 0.85);
        z-index: 0;
    }

    /* Main block container - ensure content stays above overlay */
    .st-emotion-cache-yw8pof.ekr3hml4 {
        position: relative;
        z-index: 1;
    }

    /* Rest of your existing styles */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 15px;
        background-color: rgba(255, 255, 255, 0.9);
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e6f2ff;
        transform: scale(1.05);
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🌾 Smart Farming Assistant")
    
    # Initialize agents
    farming_agents = SmartFarmingAgents()
    
    guide = farming_agents.guide_agent
    
    if st.button("🤔 Not sure where to start?"):
        st.session_state.show_guide = True
    
    # Show guide in sidebar if requested
    if st.session_state.get("show_guide", False):
        with st.sidebar:
            guide.display_interface()

    # Tabbed interface for better navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🌱 Crop Advisory", 
        "🌍 Soil Health", 
        "📈 Market Insights", 
        "☁️ Climate Analysis", 
        "🌿 Disease Diagnosis"
    ])

    with tab1:
        st.header("Crop Recommendation Engine")
        farming_agents.crop_advisor.display_advisory_interface()

    with tab2:
        st.header("Soil Health Intelligence")
        farming_agents.soil_analyst.display_soil_analysis_interface()

    with tab3:
        st.header("Market Intelligence")
        farming_agents.market_intelligence.generate_market_insights()
    
    with tab4:
        st.header("Climate Pattern Analysis")
        location = st.text_input("Enter your location:", placeholder="e.g., Bengaluru")
        
        if st.button("Analyze Climate Patterns", key="climate_analysis"):
            with st.spinner('Fetching weather data...'):
                climate_insights = farming_agents.climate_predictor.analyze_climate_data(location)
                st.info(climate_insights)
                
    with tab5:
        st.header("Crop Disease Diagnosis")
        
        # Input method selection
        input_method = st.radio(
            "How would you like to analyze your crop?",
            ["📝 Describe Symptoms", "📷 Upload Image"]
        )
        
        if input_method == "📷 Upload Image":
            st.info("""
            ### Quick Guide for Image Analysis:
            
            1. 📸 **Upload Image**: Click below to upload a clear, well-lit photo of the affected plant parts
            
            2. ❓ **Enter Question**: Copy and paste this exact text:
            ```
            Describe the disease in the image by explaining the visible symptoms, do not take any guesses on what it could be. Just describe the visual appearance of the disease.
            ```
            
            3. ▶️ **Get Analysis**: Click Submit and wait for the description
            
            4. 📋 **Copy Result**: Copy the VLM's description into the text area below
            
            > Note: We're working on automating this process with direct GPU integration!
            """)
            
            # Add Gradio component
            farming_agents.load_gradio_component()
            
            # Add option to proceed with VLM output
            vlm_output = st.text_area(
                "VLM Analysis Output",
                placeholder="Paste the VLM's description here to proceed with disease analysis...",
                help="Copy the description from the VLM above and paste it here for detailed analysis"
            )
            
            if vlm_output:
                farming_agents.disease_detective.analyze_with_description(vlm_output)
                
        else:
            farming_agents.disease_detective.display_interface()
                            
    # Footer with agent credits
    st.markdown("---")
    st.markdown("""
    ### 🤖 Intelligent Agents Powering Your Farming Insights
    - 🌱 **Crop Advisor**: Personalized crop recommendations
    - 🌍 **Soil Analyst**: Comprehensive soil health intelligence
    - 📈 **Market Strategist**: Real-time market trend analysis
    - ☁️ **Climate Predictor**: Advanced weather pattern insights
    - 🌿 **Disease Detector**: Precise crop health diagnostics
    """)

if __name__ == "__main__":
    main()