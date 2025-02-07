import streamlit as st
import pandas as pd
import json
import plotly.express as px
import os

base_dir = os.path.dirname(os.path.abspath(__file__))

file_path = os.path.join(base_dir, "..", "data", "tab3-market_insights.csv")

class MarketInsightsAgent:
    def __init__(self, vectorlake, modellake):
        self.vectorlake = vectorlake
        self.modellake = modellake
        self._market_data = None
        self.supported_languages = {
            'en': 'English',
            'hi': 'Hindi',
            'ml': 'Malayalam',
            'ta': 'Tamil',
            'te': 'Telugu'
        }
    
    @property
    def market_data(self):
        """Lazy load market data only when needed"""
        if self._market_data is None:
            self.load_data()
        return self._market_data
    
    def query_market_knowledge(self, commodity, query_type="trend"):
        """Query vector database for market insights."""
        # Defining different types of market analysis prompts
        prompt_templates = {
            "trend": "Analyze the price trend for {commodity} over the past year. Consider seasonality and market dynamics.",
            "prediction": "Based on historical data, what is the likely price trajectory for {commodity} in the coming months?",
            "recommendation": "What trading recommendations can you provide for {commodity} given current market conditions?",
            "risk": "What are the key market risks and opportunities for {commodity} trading?"
        }
        
        search_results = self.vectorlake.search({
            "query": f"market data for {commodity}",
            "vector_type": "market_data",
            "num_items": 10
        })
        
        context = {
            "commodity": commodity,
            "market_data": search_results.get('results', []),
            "current_conditions": self.get_current_conditions(commodity)
        }
        
        chat_request = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a specialized agricultural commodities analyst. Provide detailed market insights based on the data provided."
                },
                {
                    "role": "user",
                    "content": prompt_templates[query_type].format(commodity=commodity) + "\nContext: " + json.dumps(context)
                }
            ],
            "token_size": 1024
        }
        
        response = self.modellake.chat_complete(chat_request)
        return response.get('answer', 'No insights available')
    
    def generate_market_insights(self):
        """Generate comprehensive market insights with optional features."""
        try:
            if self.market_data is None:
                st.error("No market data available")
                return
                        
            # Commodity selection first
            commodities = self.market_data['Commodity'].unique()
            selected_commodity = st.selectbox("Select Commodity", commodities)
            
            # Display price trends and visualizations
            self.display_market_metrics(selected_commodity)
            
            # Optional features in expander
            with st.expander("Additional Analysis Options"):
                enable_translation = st.checkbox("Enable Translation", value=False)
                lang_code = 'en'
                if enable_translation:
                    lang_code = st.selectbox(
                        "Select Language",
                        options=list(self.supported_languages.keys()),
                        format_func=lambda x: self.supported_languages[x]
                    )
            
            # RAG-powered insights
            st.subheader("🤖 AI Market Analysis")
            
            # Use tabs for different analyses
            trend_tab, pred_tab, risk_tab = st.tabs(["📈 Trend", "🎯 Prediction", "⚠️ Risk"])
            
            with trend_tab:
                trend_insights = self.query_market_knowledge(selected_commodity, "trend")
                if enable_translation and lang_code != 'en':
                    trend_insights = self.translate_insights(trend_insights, lang_code)
                st.write(trend_insights)
            
            with pred_tab:
                prediction_insights = self.query_market_knowledge(selected_commodity, "prediction")
                if enable_translation and lang_code != 'en':
                    prediction_insights = self.translate_insights(prediction_insights, lang_code)
                st.write(prediction_insights)
            
            with risk_tab:
                risk_insights = self.query_market_knowledge(selected_commodity, "risk")
                if enable_translation and lang_code != 'en':
                    risk_insights = self.translate_insights(risk_insights, lang_code)
                st.write(risk_insights)
            
            # Trading recommendations
            st.subheader("💡 Trading Recommendations")
            recs = self.query_market_knowledge(selected_commodity, "recommendation")
            if enable_translation and lang_code != 'en':
                recs = self.translate_insights(recs, lang_code)
            st.info(recs)
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Stack trace:", exc_info=True)
    
    def load_data(self):
        """Load market data and create vector embeddings."""
        try:
            # Load the CSV file
            df = pd.read_csv(file_path)
            
            # Process data
            df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'], format='%Y-%B')
            df = df.sort_values('Date')
            df['YoY_Growth'] = df.groupby('Commodity')['Price per Quintal'].pct_change(12) * 100
            df['MA3'] = df.groupby('Commodity')['Price per Quintal'].rolling(window=3).mean().reset_index(0, drop=True)
            df['Volatility'] = df.groupby('Commodity')['Price per Quintal'].rolling(window=3).std().reset_index(0, drop=True)
            
            self._market_data = df
            
            return True
        except Exception as e:
            st.error(f"Error loading market data: {str(e)}")
            return False


    def display_market_metrics(self, commodity):
        df = self.market_data[self.market_data['Commodity'] == commodity].copy()

        # Convert Year and Month into a proper Date format
        df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str), format='%Y-%B')

        # Group by Date and calculate the mean price
        df_grouped = df.groupby('Date').agg({'Price per Quintal': 'mean'}).reset_index()

        # Plotly visualization
        fig = px.line(
            df_grouped,
            x='Date',
            y='Price per Quintal',
            title=f'{commodity} Price per Quintal Over Time',
            labels={'Price per Quintal': 'Price (₹/Quintal)'},
            markers=True  # Adds data points
        )

        # Display in Streamlit
        st.plotly_chart(fig, use_container_width=True)
            
        # Current metrics
        latest = df.iloc[-1]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Current Price",
                f"₹{latest['Price per Quintal']:,.2f}",
                f"{latest['YoY_Growth']:+.1f}% YoY"
            )
        with col2:
            st.metric(
                "3-Month Average",
                f"₹{latest['MA3']:,.2f}"
            )
        with col3:
            st.metric(
                "Volatility",
                f"₹{latest['Volatility']:,.2f}"
            )
    
    def get_current_conditions(self, commodity):
        """Get current market conditions for a commodity."""
        if commodity not in self.market_data['Commodity'].unique():
            return {}
            
        latest = self.market_data[self.market_data['Commodity'] == commodity].iloc[-1]
        return {
            "price": latest['Price per Quintal'],
            "yoy_growth": latest['YoY_Growth'],
            "volatility": latest['Volatility'],
            "moving_avg": latest['MA3']
        }