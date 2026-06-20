import streamlit as st
import pandas as pd
import requests
import json
from datetime import date, datetime

from src.predict import predict_churn
from src.agent import RetentionAgent
from src.test_suite import get_test_suite, get_test_summary, TestCategory
from src.evaluation_runner import EvaluationRunner

st.set_page_config(
    page_title="TeleConnect Churn + Retention App",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("TeleConnect Churn Prediction + Retention Agent")

with st.sidebar:
    st.header("Navigation")
    app_mode = st.radio(
        "Choose a mode:",
        ["Churn Prediction", "Retention Agent"],
        index=0,
    )
    st.markdown("---")
    st.markdown("### Quick Links")
    st.markdown(
        "- Use **Churn Prediction** for single or batch churn risk scoring.\n"
        "- Use **Retention Agent** for natural language retention workflows.\n"
        "- `streamlit run streamlit_combined_app.py` to open this unified app."
    )
    st.markdown("---")
    st.markdown("### Test Customers")
    st.markdown(
        "- **CUST001**: John Smith (High Risk)\n"
        "- **CUST002**: Sarah Johnson (Low Risk)\n"
        "- **CUST003**: Mike Davis (Medium Risk)"
    )

if app_mode == "Churn Prediction":
    st.header("📊 Churn Prediction Explorer")
    st.markdown("Provide a single customer record or upload a CSV to get churn predictions.")

    with st.form("churn_form"):
        age = st.number_input("Age", min_value=18, max_value=120, value=28)
        gender = st.selectbox("Gender", ["male", "female", "other"], index=0)
        tenure_months = st.number_input("Tenure months", min_value=0.0, value=2.0, format="%.2f")
        contract_type = st.selectbox("Contract type", ["month-to-month", "one year", "two year"], index=0)
        monthly_charges = st.number_input("Monthly charges", value=120.0)
        total_charges = st.number_input("Total charges", value=240.0)
        internet_service = st.selectbox("Internet service", ["fiber", "dsl", "none"], index=0)
        phone_service = st.selectbox("Phone service", ["yes", "no"], index=0)
        avg_monthly_gb_used = st.number_input("Avg monthly GB used", value=10.0)
        avg_monthly_minutes = st.number_input("Avg monthly minutes", value=300.0)
        num_support_tickets = st.number_input("Num support tickets", min_value=0, value=0)
        satisfaction_score = st.slider("Satisfaction score", 0.0, 5.0, 3.0)
        payment_method = st.selectbox(
            "Payment method",
            ["electronic check", "mailed check", "bank transfer (automatic)", "credit card (automatic)"],
            index=0,
        )
        num_additional_services = st.number_input("Num additional services", min_value=0, value=1)
        last_interaction_date = st.date_input("Last interaction date", value=date.today())
        customer_id = st.text_input("Customer ID (optional)")
        use_api = st.checkbox("Use API endpoint", value=False)
        api_url = st.text_input("API URL", value="http://localhost:8000/predict")
        submitted = st.form_submit_button("Predict")

    if submitted:
        sample = {
            "age": float(age),
            "gender": gender,
            "tenure_months": float(tenure_months),
            "contract_type": contract_type,
            "monthly_charges": float(monthly_charges),
            "total_charges": float(total_charges),
            "internet_service": internet_service,
            "phone_service": phone_service,
            "avg_monthly_gb_used": float(avg_monthly_gb_used),
            "num_support_tickets": float(num_support_tickets),
            "avg_monthly_minutes": float(avg_monthly_minutes),
            "satisfaction_score": float(satisfaction_score),
            "payment_method": payment_method,
            "num_additional_services": int(num_additional_services),
            "last_interaction_date": last_interaction_date.isoformat(),
        }
        if customer_id:
            sample["customer_id"] = customer_id

        with st.spinner("Running prediction..."):
            result = None
            try:
                if use_api and api_url:
                    try:
                        resp = requests.post(api_url, json=sample, timeout=10)
                        resp.raise_for_status()
                        result = resp.json()
                    except Exception as e:
                        st.error(f"API request failed: {e}")
                        result = predict_churn(sample)
                else:
                    result = predict_churn(sample)
            except FileNotFoundError as error:
                st.error(
                    "Model artifact missing. "
                    "Please add models/churn_model.joblib to the repo or configure MODEL_PATH.\n"
                    f"Details: {error}"
                )
            except Exception as error:
                st.error(f"Prediction failed: {error}")

        if result:
            st.subheader("Prediction")
            st.write("Churn probability:", result.get("churn_probability"))
            st.write("Risk tier:", result.get("risk_tier"))
            st.subheader("Top risk factors")
            for factor in result.get("top_risk_factors", []):
                st.write("-", factor)

    st.markdown("---")
    st.header("Batch predict from CSV")
    uploaded = st.file_uploader("Upload CSV with customer rows", type=["csv"])

    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
            st.write("Preview:")
            st.dataframe(df.head())
            if st.button("Run batch predictions"):
                results = []
                with st.spinner("Predicting..."):
                    for rec in df.to_dict(orient="records"):
                        out = predict_churn(rec)
                        results.append(out)
                res_df = pd.DataFrame(results)
                st.write("Results:")
                st.dataframe(res_df)
        except Exception as e:
            st.error(f"Failed to read uploaded CSV: {e}")

    st.markdown("---")
    st.markdown("For the integrated retention agent, switch to the Retention Agent mode in the sidebar.")

else:
    st.header("🤖 Retention Agent")
    st.markdown(
        "Use natural language to run retention workflows, view tool calls, and evaluate the agent."
    )

    if "agent" not in st.session_state:
        st.session_state.agent = RetentionAgent()
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "combined_user_input" not in st.session_state:
        st.session_state.combined_user_input = ""
    if "pending_user_input" not in st.session_state:
        st.session_state.pending_user_input = None

    def _submit_retention_message():
        if st.session_state.combined_user_input:
            st.session_state.pending_user_input = st.session_state.combined_user_input
            st.session_state.combined_user_input = ""

    def _clear_retention_conversation():
        st.session_state.conversation_history = []
        st.session_state.agent.reset_conversation()
        st.session_state.combined_user_input = ""
        st.session_state.pending_user_input = None

    mode = st.radio(
        "Retention Agent Mode:",
        ["Live Demo", "Test Runner", "Evaluation Results"],
        index=0,
    )

    if mode == "Live Demo":
        st.markdown(
            "Type a customer retention task and the agent will look up the customer, predict churn, recommend offers, and log the interaction."
        )

        for msg in st.session_state.conversation_history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
                    if msg.get("tool_calls"):
                        with st.expander("🔧 Tool Calls Details", expanded=False):
                            for i, tc in enumerate(msg["tool_calls"], 1):
                                st.markdown(f"**Tool {i}: {tc['tool']}**")
                                st.json(tc["params"])
                    if msg.get("tool_results"):
                        with st.expander("📊 Tool Results", expanded=False):
                            for i, tr in enumerate(msg["tool_results"], 1):
                                st.markdown(f"**Result {i}**")
                                st.json(tr)

        user_input = st.text_input(
            "Your message: eg. Check on CUST001' or 'Customer CUST002 threatens to switch",
            placeholder="E.g., 'Check on CUST001' or 'Customer CUST002 threatens to switch'",
            key="combined_user_input",
        )
        st.button("Send", use_container_width=True, on_click=_submit_retention_message)

        if st.session_state.pending_user_input:
            with st.spinner("Agent analyzing..."):
                response = st.session_state.agent.process_user_input(st.session_state.pending_user_input)
            st.session_state.conversation_history.append({
                "role": "user",
                "content": st.session_state.pending_user_input,
            })
            st.session_state.conversation_history.append({
                "role": "assistant",
                "content": response["response"],
                "tool_calls": response.get("tool_calls", []),
                "tool_results": response.get("tool_results", []),
                "status": response.get("status", "unknown"),
            })
            st.session_state.pending_user_input = None

        if st.session_state.conversation_history:
            st.button("🔄 Clear Conversation", on_click=_clear_retention_conversation)

    elif mode == "Test Runner":
        st.markdown("Run the full evaluation suite for the retention agent.")
        summary = get_test_summary()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tests", summary["total_tests"])
        col2.metric("Test Categories", len(summary["by_category"]))
        col3.metric("Coverage", f"{len(summary['by_category'])} categories")

        if st.button("▶️ Run All Tests", use_container_width=True):
            st.session_state.run_tests = True

        selected_category = st.selectbox(
            "Or run by category:",
            ["All"] + [c.value for c in TestCategory],
            key="combined_test_category_select",
        )

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
            report = {
                "timestamp": datetime.now().isoformat(),
                "test_results": [r.to_dict() for r in runner.results],
            }
            st.session_state.evaluation_report = report
            st.session_state.run_tests = False

        if st.session_state.get("evaluation_report"):
            report = st.session_state.evaluation_report
            st.markdown("---")
            st.header("📈 Results Summary")
            passed = sum(1 for r in report["test_results"] if r["passed"])
            total = len(report["test_results"])
            st.metric("Passed", passed)
            st.metric("Failed", total - passed)
            st.metric("Pass Rate", f"{passed/total:.1%}")
            st.metric("Total", total)
            st.download_button(
                label="📥 Download Report as JSON",
                data=json.dumps(report, indent=2),
                file_name=f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )

    else:
        st.header("📊 Evaluation Results & Analysis")
        st.markdown(
            "See the agent’s expected coverage, strengths, and the production roadmap for evaluation-based improvement."
        )
        st.markdown("### Key Findings")
        st.markdown(
            "- Test Coverage: 14 cases across 7 categories\n"
            "- Strong multi-step orchestration and ambiguous input handling\n"
            "- Improvement areas are actionability and boundary detection\n"
        )
        st.markdown("---")
        st.markdown("### Production Roadmap")
        st.markdown(
            "- Add intent detection for simple lookup queries\n"
            "- Add out-of-scope detection before orchestration\n"
            "- Refine competitor-escalation logic with context\n"
            "- Improve user-facing error handling for invalid IDs\n"
        )

    st.markdown("---")
    st.markdown("For churn scoring, choose the Churn Prediction mode in the sidebar.")
