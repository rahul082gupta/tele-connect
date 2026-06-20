"""
Streamlit UI for the Retention Agent Demo.

Live interface showing:
- Real-time agent responses
- Tool calls and results
- Evaluation metrics
- Test suite runner
"""

import streamlit as st
import json
from datetime import datetime
from typing import Any, Dict, List

from src.agent import RetentionAgent
from src.test_suite import get_test_suite, get_test_summary, get_tests_by_category, TestCategory
from src.evaluation_runner import EvaluationRunner


# Page configuration
st.set_page_config(
    page_title="TeleConnect Retention Agent",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
        font-weight: 500;
    }
    .tool-success { color: #2ecc71; font-weight: bold; }
    .tool-error { color: #e74c3c; font-weight: bold; }
    .risk-high { background-color: #ffe6e6; padding: 10px; border-radius: 5px; }
    .risk-medium { background-color: #fff3cd; padding: 10px; border-radius: 5px; }
    .risk-low { background-color: #d4edda; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ========== SIDEBAR ==========

with st.sidebar:
    st.title("🎯 TeleConnect Retention Agent")
    st.markdown("---")
    
    mode = st.radio(
        "Select Mode:",
        ["Live Demo", "Test Runner", "Evaluation Results"],
        help="Choose between interactive demo, test execution, or viewing results",
    )
    
    st.markdown("---")
    st.markdown("### 📚 Quick Reference")
    st.markdown("""
**Test Customers:**
- **CUST001**: John Smith (High Risk)
- **CUST002**: Sarah Johnson (Low Risk)
- **CUST003**: Mike Davis (Medium Risk)

**Try These Inputs:**
- "Analyze CUST001"
- "Customer CUST002 is threatening legal action"
- "No customer ID provided"
- "Change CUST001's plan"

**Unified App:** Run `streamlit run streamlit_combined_app.py` for both churn prediction and retention in one interface.
    """)


# ========== MODE 1: LIVE DEMO ==========

if mode == "Live Demo":
    st.header("🤖 Live Retention Agent Demo")
    
    st.markdown("""
    Type a natural language request and the agent will:
    1. Look up the customer
    2. Predict churn risk
    3. Recommend retention offers
    4. Suggest next steps
    
    **Try**: "I have a customer CUST001 on the phone who might churn"
    """)
    
    # Initialize agent in session state
    if "agent" not in st.session_state:
        st.session_state.agent = RetentionAgent()
    
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    
    # Chat interface
    chat_col = st.container()
    
    # Display conversation history
    for msg in st.session_state.conversation_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
                
                # Display tool calls if present
                if msg.get("tool_calls"):
                    with st.expander("🔧 Tool Calls Details", expanded=False):
                        for i, tc in enumerate(msg["tool_calls"], 1):
                            st.markdown(f"**Tool {i}: {tc['tool']}**")
                            st.json(tc["params"])
                
                # Display tool results if present
                if msg.get("tool_results"):
                    with st.expander("📊 Tool Results", expanded=False):
                        for i, tr in enumerate(msg["tool_results"], 1):
                            st.markdown(f"**Result {i}**")
                            st.json(tr)
    
    # User input
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        user_input = st.text_input(
            "Your message:",
            placeholder="E.g., 'Check on CUST001' or 'Customer CUST002 threatens to switch'",
            key="user_input",
        )
    with col2:
        send_btn = st.button("Send", use_container_width=True)
    
    if send_btn and user_input:
        # Display user message
        st.session_state.conversation_history.append({
            "role": "user",
            "content": user_input,
        })
        
        # Get agent response
        with st.spinner("Agent analyzing..."):
            response = st.session_state.agent.process_user_input(user_input)
        
        # Store response in history
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": response["response"],
            "tool_calls": response.get("tool_calls", []),
            "tool_results": response.get("tool_results", []),
            "status": response.get("status", "unknown"),
        })
        
        st.rerun()
    
    # Clear conversation button
    if st.session_state.conversation_history:
        if st.button("🔄 Clear Conversation"):
            st.session_state.conversation_history = []
            st.session_state.agent.reset_conversation()
            st.rerun()


# ========== MODE 2: TEST RUNNER ==========

elif mode == "Test Runner":
    st.header("🧪 Test Suite Runner")
    
    st.markdown("""
    Run the evaluation suite to test the agent across 14 different scenarios.
    
    **Test Categories:**
    - Single-tool happy path
    - Multi-step tool chaining
    - Ambiguous input handling
    - Out-of-scope requests
    - Escalation triggers
    - Model disagreement
    - Edge cases
    """)
    
    # Test suite overview
    summary = get_test_summary()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tests", summary["total_tests"])
    with col2:
        st.metric("Test Categories", len(summary["by_category"]))
    with col3:
        st.metric("Coverage", f"{len(summary['by_category'])} categories")
    
    st.markdown("---")
    
    # Category breakdown
    st.markdown("### Tests by Category")
    cat_cols = st.columns(len(summary["by_category"]))
    for col, (cat_name, count) in zip(cat_cols, summary["by_category"].items()):
        with col:
            st.metric(cat_name.replace("_", " ").title(), count)
    
    st.markdown("---")
    
    # Run tests button
    col1, col2, col3 = st.columns([0.3, 0.3, 0.4])
    
    with col1:
        if st.button("▶️ Run All Tests", use_container_width=True, key="run_all"):
            st.session_state.run_tests = True
    
    with col2:
        selected_category = st.selectbox(
            "Or run by category:",
            ["All"] + [c.value for c in TestCategory],
            key="test_category_select",
        )
    
    # Test execution
    if st.session_state.get("run_tests", False):
        st.info("🔄 Running evaluation suite... This may take a minute.")
        
        runner = EvaluationRunner()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        runner.test_suite = get_test_suite()
        runner.results = []
        
        for i, test_case in enumerate(runner.test_suite, 1):
            status_text.text(f"Running test {i}/{len(runner.test_suite)}: {test_case.test_id}")
            progress_bar.progress(i / len(runner.test_suite))
            
            evaluation = runner.run_single_test(test_case)
            runner.results.append(evaluation)
        
        progress_bar.progress(1.0)
        status_text.text("✅ Evaluation complete!")
        
        # Generate report
        from src.evaluation import EvaluationReport
        report = EvaluationReport(
            timestamp=datetime.now().isoformat(),
            test_results=runner.results,
        )
        
        st.session_state.evaluation_report = report
        st.session_state.run_tests = False
    
    # Display results if available
    if st.session_state.get("evaluation_report"):
        report = st.session_state.evaluation_report
        
        st.markdown("---")
        st.markdown("### 📈 Results Summary")
        
        summary_dict = report.to_dict()["summary"]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Passed", summary_dict["passed"])
        with col2:
            st.metric("Failed", summary_dict["failed"])
        with col3:
            st.metric("Pass Rate", f"{summary_dict['pass_rate']:.1%}")
        with col4:
            st.metric("Total", summary_dict["total_tests"])
        
        # Category breakdown
        st.markdown("### Category Breakdown")
        categories = report.get_category_breakdown()
        
        cat_data = []
        for cat_name, stats in categories.items():
            cat_data.append({
                "Category": cat_name.replace("_", " ").title(),
                "Pass Rate": f"{stats['pass_rate']:.1%}",
                "Avg Score": f"{stats['avg_score']:.2f}/5.0",
                "Passed": f"{stats['passed']}/{stats['total']}",
            })
        
        st.dataframe(cat_data, use_container_width=True)
        
        # Rubric scores
        st.markdown("### Rubric Scores")
        rubric_scores = report.get_average_rubric_scores()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Factual Correctness", f"{rubric_scores.get('factual_correctness', 0):.2f}/5.0")
        with col2:
            st.metric("Tool Use", f"{rubric_scores.get('tool_use_appropriateness', 0):.2f}/5.0")
        with col3:
            st.metric("Actionability", f"{rubric_scores.get('actionability', 0):.2f}/5.0")
        with col4:
            st.metric("Hallucination", f"{rubric_scores.get('hallucination_detection', 0):.2f}/5.0")
        
        # Individual test results
        st.markdown("### Individual Test Results")
        
        test_data = []
        for result in report.test_results:
            test_data.append({
                "Test ID": result.test_id,
                "Category": result.test_case.category.value.replace("_", " ").title(),
                "Status": "✅ PASS" if result.passed else "❌ FAIL",
                "Avg Score": f"{result.get_average_rubric_score():.2f}",
                "Description": result.test_case.description[:40] + "..." if len(result.test_case.description) > 40 else result.test_case.description,
            })
        
        st.dataframe(test_data, use_container_width=True, hide_index=True)
        
        # Export option
        report_json = json.dumps(report.to_dict(), indent=2)
        st.download_button(
            label="📥 Download Report as JSON",
            data=report_json,
            file_name=f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )


# ========== MODE 3: EVALUATION RESULTS ==========

else:  # Evaluation Results
    st.header("📊 Evaluation Results & Analysis")
    
    st.markdown("""
    ### Key Findings
    
    **Test Coverage**: 14 comprehensive test cases across 7 categories
    
    **What Was Evaluated:**
    - Tool Selection Accuracy: How well the agent selects appropriate tools
    - Parameter Extraction: Whether required parameters are correctly identified
    - Response Completeness: If responses contain all necessary information
    - Hallucination Detection: Whether responses stay grounded in tool results
    - Factual Correctness: Accuracy relative to tool outputs
    - Tool Use Appropriateness: Correct orchestration and order
    - Actionability: Whether reps can act on recommendations
    
    ### Test Categories
    
    1. **Single-Tool Happy Path** (T001)
       - Basic customer lookup functionality
       
    2. **Multi-Step Chaining** (T002, T003)
       - Full workflow: lookup → predict → offers → log
       - High-risk customer identification
       
    3. **Ambiguous Input Handling** (T004, T005, T006)
       - Missing customer IDs
       - Vague references
       - Partial information
       
    4. **Out-of-Scope Requests** (T007, T008)
       - Requests beyond agent capabilities
       - Unrelated inquiries
       
    5. **Escalation Triggers** (T009, T010, T011)
       - Legal threats
       - Angry customers
       - Competitor comparisons
       
    6. **Model Disagreement** (T012)
       - Profile contradictions
       - Intuition vs. model
       
    7. **Edge Cases** (T013, T014)
       - New customers
       - Invalid references
    """)
    
    st.markdown("---")
    
    st.markdown("""
    ### Expected Results
    
    **High-Performing Areas:**
    - ✅ Multi-step tool orchestration (tools called in correct order)
    - ✅ Appropriate escalation for legal/urgent cases
    - ✅ Graceful handling of ambiguous input
    
    **Potential Challenges:**
    - ⚠️ Hallucination detection in speculative language
    - ⚠️ Parameter extraction accuracy for edge cases
    - ⚠️ Response completeness for out-of-scope requests
    
    ### Production Roadmap
    
    **CI/CD Integration:**
    - Run evaluation suite on every commit
    - Set pass-rate thresholds (e.g., >85% to merge)
    - Track metrics over time with automated dashboards
    - Alert on regressions in tool selection or escalation accuracy
    - Use real LLM API (GPT-4, Claude) instead of mock for final validation
    - Integrate human evaluation feedback loop
    - Load-test with 1000s of concurrent retention rep requests
    - Monitor hallucination score and trigger retraining if >0.15
    """)
    
    st.info("💡 Run the test suite in 'Test Runner' mode to see live results!")
