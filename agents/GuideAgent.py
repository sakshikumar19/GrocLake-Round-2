import streamlit as st
from typing import List, Dict
import datetime

class GuideAgent:
    def __init__(self, modellake):
        self.modellake = modellake
        self.initialize_session_state()
        
    def initialize_session_state(self):
        """Initialize chat history and session variables"""
        if "guide_messages" not in st.session_state:
            st.session_state.guide_messages = []
            welcome_msg = {
                "role": "assistant",
                "content": """👋 Welcome! I'm your Smart Farming Assistant Guide. 

I'll help you navigate to the right tool based on your needs. Whether you're looking to:
• Plan your crops
• Check your soil
• Monitor markets
• Track weather
• Diagnose plant issues

Just tell me what you're trying to accomplish, and I'll guide you to the most suitable tool!

What's on your mind today?""",
                "timestamp": datetime.datetime.now().strftime("%H:%M")
            }
            st.session_state.guide_messages.append(welcome_msg)
            
        # Add timestamps to existing messages if they don't have one
        for message in st.session_state.guide_messages:
            if "timestamp" not in message:
                message["timestamp"] = datetime.datetime.now().strftime("%H:%M")
            
        if "conversation_context" not in st.session_state:
            st.session_state.conversation_context = {
                "last_tool_suggested": None,
                "user_concerns": [],
                "previous_topics": set()
            }

    def get_tool_suggestion(self, user_message: str) -> str:
        """Generate contextual tool suggestions based on user input"""
        context = self._get_conversation_context()
        
        suggestion_prompt = {
            "messages": [
                {
                    "role": "system",
                    "content": """You are an expert farming assistant with deep knowledge of agriculture. Your role is to:
1. Understand the farmer's needs and concerns
2. Provide helpful, practical advice
3. Guide them to the most relevant tool while explaining its benefits. Your job is only to suggest the tool and nothing else!
4. Maintain a warm, supportive tone

Available Tools:
- Crop Advisory (🌱): Personalized crop recommendations, planting schedules, growing guides
- Soil Health (🌍): Soil testing, nutrient analysis, improvement recommendations
- Market Insights (📈): Price trends, market demand, profit optimization
- Climate Analysis (☁️): Weather forecasting, climate pattern analysis
- Disease Diagnosis (🌿): Plant health assessment, disease identification, treatment advice

Previous context: """ + context
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "token_size": 2048
        }
        
        try:
            response = self.modellake.chat_complete(suggestion_prompt)
            return response['answer']
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble generating a response right now. Could you please try again?"

    def _get_conversation_context(self) -> str:
        """Build context string from conversation history"""
        context = []
        if st.session_state.conversation_context["last_tool_suggested"]:
            context.append(f"Last tool suggested: {st.session_state.conversation_context['last_tool_suggested']}")
        if st.session_state.conversation_context["user_concerns"]:
            context.append(f"Previous concerns: {', '.join(st.session_state.conversation_context['user_concerns'][-3:])}")
        return ". ".join(context)

    def _update_conversation_context(self, user_message: str, response: str):
        """Update conversation context with new information"""
        # Extract tool mention from response
        tools = ["Crop Advisory", "Soil Health", "Market Insights", "Climate Analysis", "Disease Diagnosis"]
        for tool in tools:
            if tool in response:
                st.session_state.conversation_context["last_tool_suggested"] = tool
                break
                
        # Store user concern
        st.session_state.conversation_context["user_concerns"].append(user_message)
        if len(st.session_state.conversation_context["user_concerns"]) > 5:
            st.session_state.conversation_context["user_concerns"].pop(0)

    def display_interface(self):
        """Display enhanced chat interface"""
        st.markdown("### 🧭 Smart Farming Guide")
        
        # Chat container with custom styling
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.guide_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    if "timestamp" in message:  # Check if timestamp exists
                        st.caption(f"sent at {message['timestamp']}")

        # Chat input with error handling
        try:
            if prompt := st.chat_input("Ask me anything about farming or our tools..."):
                # Add user message
                user_message = {
                    "role": "user",
                    "content": prompt,
                    "timestamp": datetime.datetime.now().strftime("%H:%M")
                }
                st.session_state.guide_messages.append(user_message)
                
                # Get and add response
                with st.spinner("Thinking..."):
                    response = self.get_tool_suggestion(prompt)
                    assistant_message = {
                        "role": "assistant",
                        "content": response,
                        "timestamp": datetime.datetime.now().strftime("%H:%M")
                    }
                    st.session_state.guide_messages.append(assistant_message)
                    
                    # Update context
                    self._update_conversation_context(prompt, response)
                    
                # Rerun to update display
                st.rerun()
                
        except Exception as e:
            st.error(f"Sorry, I encountered an error. Please try again or refresh the page. Error: {str(e)}")
            
        # Add clear chat button
        if st.button("Clear Chat History"):
            st.session_state.guide_messages = []
            st.session_state.conversation_context = {
                "last_tool_suggested": None,
                "user_concerns": [],
                "previous_topics": set()
            }
            self.initialize_session_state()
            st.rerun()