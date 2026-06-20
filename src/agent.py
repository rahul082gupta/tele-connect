"""
Retention Agent Orchestration with Tool Calling.

This module implements the core agent that orchestrates tool calls
to assist retention representatives with at-risk customers.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.agent_tools import (
    get_tool_schemas,
    execute_tool,
    ToolCall,
    CUSTOMER_DATABASE,
)


class MessageRole(Enum):
    """Message roles in the conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_RESULT = "tool"


@dataclass
class Message:
    """Represents a message in the conversation."""
    role: MessageRole
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None


class RetentionAgent:
    """
    Retention Agent that orchestrates tools to help retention representatives.
    
    The agent:
    1. Accepts natural language input from a representative
    2. Chains tools in the correct order (lookup customer, predict churn, get offers)
    3. Handles ambiguous/incomplete inputs gracefully
    4. Recognizes when to escalate
    5. Produces actionable recommendations
    """
    
    def __init__(self, model_name: str = "mock"):
        """
        Initialize the retention agent.
        
        Args:
            model_name: The LLM model to use ("openai", "anthropic", or "mock")
        """
        self.model_name = model_name
        self.conversation_history: List[Message] = []
        self.tool_schemas = get_tool_schemas()
        self.max_tool_calls = 10
        self.escalation_keywords = [
            "legal",
            "lawsuit",
            "complain",
            "dispute",
            "angry",
            "cancel",
            "close account",
            "switch",
        ]
    
    def reset_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []
    
    def add_message(self, role: MessageRole, content: str):
        """Add a message to the conversation history."""
        self.conversation_history.append(Message(role=role, content=content))
    
    def _should_escalate(self, user_input: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if a conversation should be escalated based on keywords.
        
        Returns:
            Tuple of (should_escalate, reason)
        """
        input_lower = user_input.lower()
        for keyword in self.escalation_keywords:
            if keyword in input_lower:
                return True, f"Detected escalation trigger: '{keyword}'"
        return False, None
    
    def _is_out_of_scope_request(self, user_input: str) -> Tuple[bool, Optional[str]]:
        """Detect requests that are outside the agent's retention support scope."""
        text_lower = user_input.lower()

        if "contract" in text_lower and any(word in text_lower for word in ["change", "modify", "update", "switch", "upgrade", "downgrade"]):
            return True, "This agent cannot make contract changes directly. Please consult the account manager."

        if "billing" in text_lower and any(word in text_lower for word in ["fix", "change", "adjust", "refund", "resolve", "issue", "dispute"]):
            return True, "Billing changes are outside my scope. Please escalate to billing support."

        if any(phrase in text_lower for phrase in ["change plan", "change package", "modify plan", "modify account", "transfer plan"]):
            return True, "I can provide retention guidance, but I cannot make account changes on behalf of the customer."

        if any(phrase in text_lower for phrase in ["what's the weather", "what is the weather", "stock price", "calendar", "appointment"]):
            return True, "That request is outside the retention agent's capabilities."

        return False, None

    def _is_lookup_only_request(self, text: str) -> bool:
        """Detect explicit lookup-only queries that should not trigger the full retention workflow."""
        text_lower = text.lower()
        lookup_phrases = ["look up", "lookup", "find", "retrieve", "pull up", "show me", "get info on", "check on"]
        follow_up_phrases = ["recommend", "retention", "offer", "predict", "analysis", "risk", "churn", "help keep", "keep them", "match it"]

        if any(phrase in text_lower for phrase in lookup_phrases):
            if not any(phrase in text_lower for phrase in follow_up_phrases):
                return True
        return False
    
    def _extract_customer_id(self, text: str) -> Optional[str]:
        """Extract customer ID from text."""
        # Look for patterns like CUST### or customer id ###
        match = re.search(r'CUST\d{3}', text.upper())
        if match:
            return match.group(0)
        
        # Look for available customers mentioned
        for customer_id in CUSTOMER_DATABASE.keys():
            if customer_id.lower() in text.lower():
                return customer_id
        
        return None
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the agent."""
        tool_descriptions = "\n".join([
            f"- {schema['name']}: {schema['description']}"
            for schema in self.tool_schemas
        ])
        
        return f"""You are a helpful retention agent for TeleConnect, a telecommunications company.
Your role is to assist retention representatives in real-time by:
1. Looking up customer information
2. Running churn prediction analysis
3. Suggesting appropriate retention offers
4. Logging interactions
5. Escalating complex cases when needed

Available tools:
{tool_descriptions}

Guidelines:
- Always look up the customer first if a customer ID is provided
- Run churn prediction to understand risk level
- Suggest retention offers based on risk tier and contract type
- Be specific and actionable in recommendations
- Escalate if the customer is threatening to leave or has legal concerns
- If customer ID is not provided and not clear, ask for it

Tool calling format:
When you need to call a tool, format it as: TOOL_CALL[tool_name]{{param1: value1, param2: value2}}

Respond naturally and helpfully to the representative."""
    
    def _parse_tool_calls(self, response: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Parse tool calls from the agent response.
        
        Expected format: TOOL_CALL[tool_name]{{param1: value1, param2: value2}}
        """
        tool_calls = []
        pattern = r'TOOL_CALL\[(\w+)\]\{\{(.+?)\}\}'
        
        for match in re.finditer(pattern, response, re.DOTALL):
            tool_name = match.group(1)
            params_str = match.group(2)
            
            # Parse parameters (simple JSON-like format)
            try:
                params = {}
                for param in params_str.split(','):
                    key, value = param.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    params[key] = value
                tool_calls.append((tool_name, params))
            except Exception:
                continue
        
        return tool_calls
    
    def _mock_llm_response(self, conversation_history: List[Message], system_prompt: str) -> str:
        """
        Mock LLM response (since we don't have API keys in the demo).
        
        This implements basic reasoning logic to orchestrate tools.
        """
        # Get the latest user message
        user_messages = [m for m in conversation_history if m.role == MessageRole.USER]
        if not user_messages:
            return "I need more information to help you."
        
        latest_user_input = user_messages[-1].content
        customer_id = self._extract_customer_id(latest_user_input)
        
        # Check for out-of-scope requests first
        out_of_scope, out_of_scope_reason = self._is_out_of_scope_request(latest_user_input)
        if out_of_scope:
            reason = out_of_scope_reason or "The request is outside the agent's retention scope."
            return f"""I can help with retention guidance, but I cannot execute that request.

{reason}

If you need customer details, please ask for a lookup or retention recommendation.
"""

        # Check for escalation
        should_escalate, escalation_reason = self._should_escalate(latest_user_input)
        if should_escalate:
            reason = escalation_reason or "Based on the conversation context"
            return f"""I'm detecting a concerning situation that requires immediate supervisor attention.

**Escalation Reason:** {reason}

{latest_user_input}

I'm escalating this case to a supervisor who can provide better assistance.

TOOL_CALL[escalate_to_supervisor]{{customer_id: {customer_id or 'UNKNOWN'}, reason: {reason}, priority: high}}"""
        
        # Build response with tool calls
        if not customer_id:
            return """I'd be happy to help with retention, but I need a customer ID to proceed.

Could you provide the customer ID? For example: CUST001, CUST002, or CUST003.

Or you can describe the situation and I'll try to assist:
- "Tell me about CUST001"
- "Look up customer CUST002"
- "What's the status of CUST003"
"""
        
        # Standard flow: lookup -> predict -> get offers
        response = f"Let me analyze this customer and prepare retention recommendations.\n\n"
        response += f"TOOL_CALL[lookup_customer]{{customer_id: {customer_id}}}\n"
        
        return response
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and return agent response with tool calls.
        
        Returns:
            Dict with:
            - response: The agent's final response
            - tool_calls: List of tool calls made
            - tool_results: Results from each tool call
            - messages: Complete conversation history
        """
        # Add user message to history
        self.add_message(MessageRole.USER, user_input)
        
        # Check for escalation first
        should_escalate, escalation_reason = self._should_escalate(user_input)
        if should_escalate:
            customer_id = self._extract_customer_id(user_input) or "UNKNOWN"
            
            result = execute_tool("escalate_to_supervisor", {
                "customer_id": customer_id,
                "reason": escalation_reason or "Customer situation requires supervisor review",
                "context_summary": user_input,
                "priority": "high",
            })
            
            response = f"""⚠️ **CASE ESCALATED TO SUPERVISOR**

{escalation_reason}

A supervisor has been notified and will contact you shortly regarding this case.

**Escalation ID:** {result.get('escalation_id', 'N/A')}"""
            
            return {
                "response": response,
                "tool_calls": [{"tool": "escalate_to_supervisor", "params": {
                    "customer_id": customer_id,
                    "reason": escalation_reason,
                }}],
                "tool_results": [result],
                "messages": self.conversation_history,
                "status": "escalated",
            }

        # Check for out-of-scope requests after escalation handling
        out_of_scope, out_of_scope_reason = self._is_out_of_scope_request(user_input)
        if out_of_scope:
            response = f"""⚠️ **REQUEST OUT OF SCOPE**

{out_of_scope_reason}

I can still help with customer lookups or retention guidance, but I cannot make account changes or handle unrelated requests.
"""
            self.add_message(MessageRole.ASSISTANT, response)
            return {
                "response": response,
                "tool_calls": [],
                "tool_results": [],
                "messages": self.conversation_history,
                "status": "out_of_scope",
            }
        if should_escalate:
            customer_id = self._extract_customer_id(user_input) or "UNKNOWN"
            
            result = execute_tool("escalate_to_supervisor", {
                "customer_id": customer_id,
                "reason": escalation_reason or "Customer situation requires supervisor review",
                "context_summary": user_input,
                "priority": "high",
            })
            
            response = f"""⚠️ **CASE ESCALATED TO SUPERVISOR**

{escalation_reason}

A supervisor has been notified and will contact you shortly regarding this case.

**Escalation ID:** {result.get('escalation_id', 'N/A')}"""
            
            return {
                "response": response,
                "tool_calls": [{"tool": "escalate_to_supervisor", "params": {
                    "customer_id": customer_id,
                    "reason": escalation_reason,
                }}],
                "tool_results": [result],
                "messages": self.conversation_history,
                "status": "escalated",
            }
        
        # Extract customer ID
        customer_id = self._extract_customer_id(user_input)
        
        if not customer_id:
            response = """I need a customer ID to assist with retention.

**Available test customers:**
- CUST001: John Smith (high risk, month-to-month)
- CUST002: Sarah Johnson (low risk, two year)
- CUST003: Mike Davis (medium risk, month-to-month)

Please provide a customer ID or describe the customer situation with more details."""
            
            self.add_message(MessageRole.ASSISTANT, response)
            return {
                "response": response,
                "tool_calls": [],
                "tool_results": [],
                "messages": self.conversation_history,
                "status": "incomplete_info",
            }

        # Handle invalid or unknown customer IDs gracefully without invoking tools
        if customer_id not in CUSTOMER_DATABASE:
            response = f"""I couldn't find a customer with ID {customer_id} in the current retention database.

Please verify the ID or use one of the available test customers: CUST001, CUST002, or CUST003.
If this is a hypothetical or long-tenure customer, I can only look up supported demo profiles in this environment.
"""
            self.add_message(MessageRole.ASSISTANT, response)
            return {
                "response": response,
                "tool_calls": [],
                "tool_results": [],
                "messages": self.conversation_history,
                "status": "invalid_customer",
            }

        if self._is_lookup_only_request(user_input):
            lookup_result = execute_tool("lookup_customer", {"customer_id": customer_id})
            tool_calls_made = [{"tool": "lookup_customer", "params": {"customer_id": customer_id}}]
            tool_results = [lookup_result]

            if not lookup_result.get("success"):
                response = f"❌ {lookup_result.get('error', 'Failed to look up customer')}"
                self.add_message(MessageRole.ASSISTANT, response)
                return {
                    "response": response,
                    "tool_calls": tool_calls_made,
                    "tool_results": tool_results,
                    "messages": self.conversation_history,
                    "status": "error",
                }

            customer = lookup_result.get("customer", {})
            response = f"Here is the customer information for {customer.get('name', 'the customer')} (ID: {customer_id}).\n\n" \
                       f"- Tenure: {customer.get('tenure_months')} months\n" \
                       f"- Contract: {customer.get('contract_type')}\n" \
                       f"- Monthly Charges: ${customer.get('monthly_charges')}\n" \
                       f"- Satisfaction Score: {customer.get('satisfaction_score')}/5.0\n" \
                       f"- Customer Status: {customer.get('account_status')}\n\n" \
                       f"If you want retention recommendations for this customer, just ask for an analysis or retention offers."
            self.add_message(MessageRole.ASSISTANT, response)
            return {
                "response": response,
                "tool_calls": tool_calls_made,
                "tool_results": tool_results,
                "messages": self.conversation_history,
                "status": "lookup_complete",
            }

        # Standard orchestration: lookup -> predict -> offers -> log
        tool_calls_made = []
        tool_results = []
        
        # Step 1: Look up customer
        lookup_result = execute_tool("lookup_customer", {"customer_id": customer_id})
        tool_calls_made.append({"tool": "lookup_customer", "params": {"customer_id": customer_id}})
        tool_results.append(lookup_result)
        
        if not lookup_result.get("success"):
            response = f"❌ {lookup_result.get('error', 'Failed to look up customer')}"
            self.add_message(MessageRole.ASSISTANT, response)
            return {
                "response": response,
                "tool_calls": tool_calls_made,
                "tool_results": tool_results,
                "messages": self.conversation_history,
                "status": "error",
            }
        
        customer = lookup_result.get("customer", {})
        
        # Step 2: Predict churn
        # Convert customer data for prediction
        prediction_params = {
            "age": float(customer.get("age", 0)),
            "gender": customer.get("gender", "male"),
            "tenure_months": float(customer.get("tenure_months", 0)),
            "contract_type": customer.get("contract_type", "month-to-month"),
            "monthly_charges": float(customer.get("monthly_charges", 0)),
            "total_charges": float(customer.get("total_charges", 0)),
            "internet_service": customer.get("internet_service", "none"),
            "phone_service": customer.get("phone_service", "no"),
            "avg_monthly_gb_used": float(customer.get("avg_monthly_gb_used", 0)),
            "num_support_tickets": float(customer.get("num_support_tickets", 0)),
            "avg_monthly_minutes": float(customer.get("avg_monthly_minutes", 0)),
            "satisfaction_score": float(customer.get("satisfaction_score", 3)),
            "payment_method": customer.get("payment_method", "electronic check"),
            "num_additional_services": int(customer.get("num_additional_services", 0)),
            "last_interaction_date": customer.get("last_interaction_date", "2026-06-20"),
        }
        
        prediction_result = execute_tool("predict_churn", prediction_params)
        tool_calls_made.append({"tool": "predict_churn", "params": prediction_params})
        tool_results.append(prediction_result)
        
        if not prediction_result.get("success"):
            response = f"⚠️ Could not run prediction: {prediction_result.get('error', 'Unknown error')}"
            self.add_message(MessageRole.ASSISTANT, response)
            return {
                "response": response,
                "tool_calls": tool_calls_made,
                "tool_results": tool_results,
                "messages": self.conversation_history,
                "status": "error",
            }
        
        churn_probability = prediction_result.get("churn_probability", 0.0)
        risk_tier = prediction_result.get("risk_tier", "unknown")
        risk_factors = prediction_result.get("top_risk_factors", [])
        
        # Step 3: Get retention offers
        offers_result = execute_tool("get_retention_offers", {
            "risk_tier": risk_tier,
            "contract_type": customer.get("contract_type", "month-to-month"),
        })
        tool_calls_made.append({"tool": "get_retention_offers", "params": {
            "risk_tier": risk_tier,
            "contract_type": customer.get("contract_type", "month-to-month"),
        }})
        tool_results.append(offers_result)
        
        # Build comprehensive response
        response = f"""## 📊 **Retention Analysis for {customer.get('name', 'Customer')}**

### Customer Profile
- **ID:** {customer.get('customer_id')}
- **Age:** {customer.get('age')} | **Tenure:** {customer.get('tenure_months')} months
- **Contract:** {customer.get('contract_type')} | **Monthly Charge:** ${customer.get('monthly_charges')}
- **Satisfaction Score:** {customer.get('satisfaction_score')}/5.0
- **Status:** {customer.get('account_status')}

### Churn Risk Assessment
- **Churn Probability:** {churn_probability:.1%}
- **Risk Tier:** 🔴 **{risk_tier.upper()}** 
- **Top Risk Factors:**
"""
        
        for i, factor in enumerate(risk_factors[:3], 1):
            response += f"  {i}. {factor}\n"
        
        # Add offers if available
        if offers_result.get("success") and offers_result.get("offers"):
            response += f"\n### 💰 **Recommended Retention Offers** ({offers_result.get('offer_count')} available)\n"
            for offer in offers_result.get("offers", [])[:3]:  # Top 3 offers
                if "discount_percent" in offer:
                    response += f"- **{offer['name']}:** {offer['description']} ({offer['discount_percent']}% discount)\n"
                else:
                    response += f"- **{offer['name']}:** {offer['description']} ({offer.get('value', 'Premium offer')})\n"

        if "competitor" in user_input.lower():
            response += "\n**Note:** The customer mentioned a competitor offer. Use this information to frame the conversation around our value proposition and current retention catalog rather than promising to match competitor pricing exactly.\n"
        
        response += f"\n### 📋 **Recommendations**\n"
        if churn_probability > 0.7:
            response += "1. **URGENT:** Present top offer immediately\n"
            response += "2. Emphasize value and benefits of staying\n"
            response += "3. Consider escalation if customer resistant\n"
        elif churn_probability > 0.4:
            response += "1. Present retention offer proactively\n"
            response += "2. Address top risk factors in conversation\n"
            response += "3. Monitor satisfaction - may need follow-up\n"
        else:
            response += "1. Low risk - routine support sufficient\n"
            response += "2. Maintain satisfaction through good service\n"
        
        # Log the interaction
        log_result = execute_tool("log_interaction", {
            "customer_id": customer_id,
            "interaction_type": "offer_presented",
            "notes": f"Risk tier: {risk_tier}, Churn probability: {churn_probability:.1%}",
        })
        tool_calls_made.append({"tool": "log_interaction", "params": {"customer_id": customer_id, "interaction_type": "offer_presented"}})
        tool_results.append(log_result)
        
        self.add_message(MessageRole.ASSISTANT, response)
        
        return {
            "response": response,
            "tool_calls": tool_calls_made,
            "tool_results": tool_results,
            "messages": self.conversation_history,
            "status": "success",
        }
