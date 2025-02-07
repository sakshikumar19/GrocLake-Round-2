import streamlit as st

class GuideAgent:
    def __init__(self, modellake):
        self.modellake = modellake
        self.initialize_session_state()
        
    def initialize_session_state(self):
        """Initialize chat history"""
        if "guide_messages" not in st.session_state:
            st.session_state.guide_messages = []
            welcome_msg = {
                "role": "assistant",
                "content": """👋 Hi! I can help you find the right tool for your farming needs.

Tell me what you're looking to do, and I'll suggest the best tool for you!

For example:
- "I want to know what crops to plant"
- "My plants have yellow spots"
- "Need to check market prices"
- "Worried about soil quality"
- "Want to plan for weather changes"
"""
            }
            st.session_state.guide_messages.append(welcome_msg)

    def get_tool_suggestion(self, user_message: str) -> str:
        """Get a simple tool suggestion based on user's need"""
        suggestion_prompt = {
            "messages": [
                {
                    "role": "system",
                    "content": """You are a farming assistant. Based on the user's need, suggest ONE of these tools:

Tools:
1. Crop Advisory (🌱) - For what to plant, when to plant, growing advice
2. Soil Health (🌍) - For soil testing and nutrient analysis
3. Market Insights (📈) - For prices and market trends
4. Climate Analysis (☁️) - For weather planning
5. Disease Diagnosis (🌿) - For plant health issues

Give a simple, friendly response that:
1. Shows you understand their need
2. Suggests the most relevant tool
3. Explains why that tool will help them"""
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "token_size": 1024
        }
        
        response = self.modellake.chat_complete(suggestion_prompt)
        return response['answer']

    def display_interface(self):
        """Display simple chat interface"""
        st.markdown("### 🧭 Smart Farming Guide")
        
        # Display chat history
        for message in st.session_state.guide_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("What do you need help with?"):
            # Add user message
            st.session_state.guide_messages.append({"role": "user", "content": prompt})
            
            # Get and add suggestion
            suggestion = self.get_tool_suggestion(prompt)
            st.session_state.guide_messages.append({"role": "assistant", "content": suggestion})
            
            # Refresh display
            st.experimental_rerun()
