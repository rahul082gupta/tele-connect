import pytest

from src.agent import RetentionAgent


@pytest.fixture
def agent():
    return RetentionAgent()


def test_competitor_switch_does_not_escalate(agent):
    user_input = "CUST003 said a competitor offered them a better deal. Should I match it?"
    result = agent.process_user_input(user_input)

    assert result["status"] != "escalated"
    assert any(call["tool"] == "lookup_customer" for call in result["tool_calls"])
    assert any(call["tool"] == "predict_churn" for call in result["tool_calls"])
    assert any(call["tool"] == "get_retention_offers" for call in result["tool_calls"])
    assert "competitor" in result["response"].lower()


def test_invalid_customer_id_returns_graceful_message(agent):
    user_input = "Long-term customer CUST999 with 300+ months tenure - need to check status"
    result = agent.process_user_input(user_input)

    assert result["status"] == "invalid_customer"
    assert result["tool_calls"] == []
    assert "couldn't find a customer" in result["response"].lower()
    assert "c360" not in result["response"].lower()
