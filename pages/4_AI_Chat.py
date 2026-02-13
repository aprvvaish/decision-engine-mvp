"""
AI Portfolio Assistant - Chat with your portfolio data
Powered by Claude API
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
from datetime import datetime

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
    }
    .assistant-message {
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 AI Portfolio Assistant")
st.caption("Ask me anything about your portfolios, stocks, or investment strategy")

# Database connection
DB_PATH = "scan_results.db"

# ============================================================================
# HELPER FUNCTIONS TO GET CONTEXT
# ============================================================================

def get_portfolio_context():
    """Get all portfolio data for context"""
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Get portfolio list
        portfolios_query = """
        SELECT name, initial_capital, strategy, created_at 
        FROM portfolios
        ORDER BY created_at DESC
        """
        portfolios_df = pd.read_sql_query(portfolios_query, conn)
        
        # Get latest stock prices
        prices_query = """
        SELECT ticker, close_price, rsi, date
        FROM scan_results
        WHERE date IN (
            SELECT MAX(date) FROM scan_results GROUP BY ticker
        )
        """
        prices_df = pd.read_sql_query(prices_query, conn)
        
        # Get recent signals
        signals_query = """
        SELECT ticker, date, buy_signal, momentum_signal
        FROM scan_results
        WHERE (buy_signal = 1 OR momentum_signal = 1)
        AND date >= date('now', '-30 days')
        ORDER BY date DESC
        LIMIT 10
        """
        signals_df = pd.read_sql_query(signals_query, conn)
        
        conn.close()
        
        return {
            'portfolios': portfolios_df.to_dict('records') if not portfolios_df.empty else [],
            'prices': prices_df.to_dict('records') if not prices_df.empty else [],
            'signals': signals_df.to_dict('records') if not signals_df.empty else []
        }
    except Exception as e:
        return {'error': str(e)}

def get_stock_details(ticker):
    """Get detailed info for a specific stock"""
    try:
        conn = sqlite3.connect(DB_PATH)
        
        query = f"""
        SELECT 
            ticker,
            close_price,
            sma_50,
            sma_200,
            rsi,
            macd,
            volume,
            buy_signal,
            momentum_signal,
            date
        FROM scan_results
        WHERE ticker = '{ticker}'
        ORDER BY date DESC
        LIMIT 1
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            return df.iloc[0].to_dict()
        return None
    except Exception as e:
        return {'error': str(e)}

# ============================================================================
# LLM INTEGRATION
# ============================================================================

def call_ollama(messages, context=None):
    """
    Call Ollama (local LLM) with conversation history
    
    Setup:
    1. Install Ollama: https://ollama.com/download
    2. Run: ollama pull llama3.1
    3. pip install ollama
    """
    
    try:
        import ollama
        
        # Build system prompt with context
        system_prompt = """You are an AI assistant helping with stock portfolio analysis for Indian equities.

You have access to the user's portfolio data, stock prices, and technical indicators.

Key capabilities:
- Analyze portfolio performance
- Explain technical indicators
- Suggest investment strategies
- Answer questions about stocks
- Provide market insights

Guidelines:
- Be concise and actionable
- Use ₹ for Indian Rupees
- Cite specific data when available
- Acknowledge limitations
- Don't give definitive buy/sell advice (educational only)
- Use emojis sparingly for clarity

Context about available data:
- Portfolio allocations and performance
- Stock prices and technical indicators (RSI, MACD, SMA)
- Recent BUY and Momentum signals
- Multiple investment strategies (Equal Weight, Max Sharpe, etc.)
"""
        
        if context:
            system_prompt += f"\n\nCurrent data snapshot:\n{json.dumps(context, indent=2)}"
        
        # Convert messages to Ollama format
        ollama_messages = []
        
        # Add system message
        ollama_messages.append({
            'role': 'system',
            'content': system_prompt
        })
        
        # Add conversation history
        for msg in messages:
            ollama_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        # Call Ollama
        response = ollama.chat(
            model='llama3.1',
            messages=ollama_messages
        )
        
        return response['message']['content']
        
    except ImportError:
        return """
        ⚠️ **Ollama not installed**
        
        To use AI chat:
        
        **Step 1:** Install Ollama
        - Windows/Mac: Download from https://ollama.com/download
        - Linux: `curl -fsSL https://ollama.com/install.sh | sh`
        
        **Step 2:** Download the model
        ```bash
        ollama pull llama3.1
        ```
        
        **Step 3:** Install Python package
        ```bash
        pip install ollama
        ```
        
        **Step 4:** Refresh this page
        
        That's it! 100% free and runs locally on your computer.
        """
    
    except Exception as e:
        if "connection refused" in str(e).lower():
            return """
            ⚠️ **Ollama not running**
            
            The Ollama service isn't running. Please start it:
            
            **Windows/Mac:** 
            - Open Ollama app from Applications
            - Or run: `ollama serve` in terminal
            
            **Linux:**
            ```bash
            ollama serve
            ```
            
            Then refresh this page.
            """
        elif "model" in str(e).lower():
            return """
            ⚠️ **Model not found**
            
            Please download the Llama 3.1 model:
            
            ```bash
            ollama pull llama3.1
            ```
            
            Then refresh this page.
            """
        else:
            return f"Error calling Ollama: {str(e)}\n\nMake sure Ollama is installed and running."

# ============================================================================
# CHAT INTERFACE
# ============================================================================

# Initialize session state
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []
    
    # Add welcome message
    st.session_state.chat_messages.append({
        "role": "assistant",
        "content": """👋 Hello! I'm your AI Portfolio Assistant.

I can help you with:
- 📊 Portfolio performance analysis
- 📈 Stock recommendations
- 🎯 Strategy comparisons
- 💡 Investment insights
- 📚 Educational explanations

Try asking:
- "Which portfolio performed best?"
- "What are the top signals right now?"
- "Explain the Maximum Sharpe strategy"
- "Should I rebalance my portfolio?"
- "Find oversold stocks with good fundamentals"

What would you like to know?"""
    })

# Display chat history
for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about your portfolio..."):
    # Add user message
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get context
    with st.spinner("Analyzing your data..."):
        context = get_portfolio_context()
    
    # Prepare messages for API (last 10 messages for context)
    api_messages = []
    for msg in st.session_state.chat_messages[-10:]:
        if msg["role"] != "system":
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # Generate response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Call Ollama (local, free)
        full_response = call_ollama(api_messages, context)
        
        message_placeholder.markdown(full_response)
    
    # Add assistant response to history
    st.session_state.chat_messages.append({
        "role": "assistant",
        "content": full_response
    })

# Sidebar with quick actions
with st.sidebar:
    st.header("Quick Actions")
    
    if st.button("🔄 New Conversation"):
        st.session_state.chat_messages = []
        st.rerun()
    
    st.divider()
    
    st.subheader("Example Questions")
    
    example_questions = [
        "What are my current portfolios?",
        "Which stocks have recent signals?",
        "Compare Equal Weight vs Max Sharpe",
        "Find stocks with RSI < 30",
        "What's the best portfolio for ₹20L → ₹1Cr?",
        "Explain momentum strategy",
        "Should I rebalance?",
        "What are the risks in my portfolio?"
    ]
    
    for question in example_questions:
        if st.button(question, key=question):
            # Simulate user asking this question
            st.session_state.chat_messages.append({
                "role": "user",
                "content": question
            })
            st.rerun()
    
    st.divider()
    
    st.subheader("Settings")
    
    st.info("**Using:** Ollama (Free, Local)")
    st.caption("Runs on your computer, 100% private")
    
    if st.checkbox("Show debug info"):
        st.write("**Context Data:**")
        context = get_portfolio_context()
        st.json(context)
    
    st.divider()
    
    st.subheader("📦 Ollama Status")
    
    # Check Ollama status
    try:
        import ollama
        models = ollama.list()
        st.success("✅ Ollama installed")
        
        # Check if llama3.1 is available
        has_llama = any('llama3.1' in str(m) for m in models.get('models', []))
        if has_llama:
            st.success("✅ Llama 3.1 model ready")
        else:
            st.warning("⚠️ Llama 3.1 not found")
            st.code("ollama pull llama3.1")
    except ImportError:
        st.error("❌ Ollama not installed")
        st.markdown("[Install Ollama](https://ollama.com/download)")
    except Exception as e:
        st.error(f"❌ Ollama not running: {str(e)}")
        st.code("ollama serve")

# Footer
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.caption("💡 **Tip:** Ask specific questions for better answers")

with col2:
    st.caption("⚠️ **Disclaimer:** Educational purposes only, not financial advice")

# Help section
with st.expander("ℹ️ How to use AI Assistant"):
    st.markdown("""
    ### Getting Started
    
    1. **Ask natural questions** - No special syntax needed
    2. **Be specific** - "Which portfolio gained most last month?" vs "How am I doing?"
    3. **Follow-up questions** - I remember our conversation context
    
    ### What I Can Do
    
    - 📊 **Analyze portfolios** - Performance, gains, losses
    - 📈 **Stock research** - Technical indicators, signals
    - 🎯 **Strategy help** - Explain and compare strategies
    - 💡 **Insights** - Identify opportunities and risks
    - 📚 **Education** - Learn about investing concepts
    
    ### Setup Ollama (Free & Local)
    
    **Step 1: Install Ollama**
    - Windows/Mac: Download from https://ollama.com/download
    - Linux: `curl -fsSL https://ollama.com/install.sh | sh`
    
    **Step 2: Download Model**
    ```bash
    ollama pull llama3.1
    ```
    
    **Step 3: Install Python Package**
    ```bash
    pip install ollama
    ```
    
    **Step 4: Start Ollama**
    - Windows/Mac: Open Ollama app
    - Linux: `ollama serve`
    
    **Step 5: Refresh This Page**
    
    That's it! 100% free, runs locally, completely private.
    
    ### Why Ollama?
    
    ✅ **Free** - No API costs  
    ✅ **Private** - Data stays on your computer  
    ✅ **Fast** - No network latency  
    ✅ **Offline** - Works without internet  
    ✅ **Quality** - Llama 3.1 is excellent  
    
    ### Tips
    
    - Start broad, then ask follow-ups
    - Ask for explanations of technical terms
    - Request specific data (dates, numbers)
    - Compare multiple options
    
    ### Example Conversations
    
    **Portfolio Analysis:**
    ```
    You: "How are my portfolios doing?"
    AI: "You have 3 portfolios totaling ₹45L..."
    You: "Which one should I focus on?"
    AI: "Based on performance, Aggressive Growth..."
    ```
    
    **Stock Research:**
    ```
    You: "Find me oversold stocks"
    AI: "Found 3 stocks with RSI < 30..."
    You: "Tell me more about CIPLA"
    AI: "CIPLA is currently at ₹1,330..."
    ```
    
    **Learning:**
    ```
    You: "What is RSI?"
    AI: "RSI (Relative Strength Index) is..."
    You: "How should I use it?"
    AI: "RSI is best used for..."
    ```
    """)
