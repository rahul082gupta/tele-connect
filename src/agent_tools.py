"""
Tool definitions for the Retention Agent.

This module defines all the tools available to the retention agent,
including their schemas, descriptions, and implementations.
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from src.predict import predict_churn


# ========== TOOL SCHEMAS ==========

@dataclass
class ToolCall:
    """Represents a tool call made by the agent."""
    name: str
    parameters: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "parameters": self.parameters}


# ========== TOOL: PREDICT_CHURN ==========

PREDICT_CHURN_SCHEMA = {
    "name": "predict_churn",
    "description": "Predicts customer churn probability using the trained ML model. Accepts customer features and returns churn probability (0-1), risk tier (low/medium/high), and top risk factors.",
    "parameters": {
        "type": "object",
        "properties": {
            "age": {"type": "number", "description": "Customer age (18-120)"},
            "gender": {"type": "string", "enum": ["male", "female", "other"], "description": "Customer gender"},
            "tenure_months": {"type": "number", "description": "Months as customer"},
            "contract_type": {"type": "string", "enum": ["month-to-month", "one year", "two year"], "description": "Contract type"},
            "monthly_charges": {"type": "number", "description": "Monthly charges ($)"},
            "total_charges": {"type": "number", "description": "Total charges to date ($)"},
            "internet_service": {"type": "string", "enum": ["fiber", "dsl", "none"], "description": "Internet service type"},
            "phone_service": {"type": "string", "enum": ["yes", "no"], "description": "Phone service enabled"},
            "avg_monthly_gb_used": {"type": "number", "description": "Average GB used per month"},
            "num_support_tickets": {"type": "number", "description": "Number of support tickets"},
            "avg_monthly_minutes": {"type": "number", "description": "Average minutes used per month"},
            "satisfaction_score": {"type": "number", "description": "Satisfaction score (0-5)"},
            "payment_method": {"type": "string", "enum": ["electronic check", "mailed check", "bank transfer (automatic)", "credit card (automatic)"], "description": "Payment method"},
            "num_additional_services": {"type": "number", "description": "Number of additional services"},
            "last_interaction_date": {"type": "string", "description": "Last interaction date (YYYY-MM-DD)"},
        },
        "required": ["age", "gender", "tenure_months", "contract_type", "monthly_charges", "total_charges", 
                     "internet_service", "phone_service", "avg_monthly_gb_used", "num_support_tickets",
                     "avg_monthly_minutes", "satisfaction_score", "payment_method", "num_additional_services",
                     "last_interaction_date"],
    }
}


def execute_predict_churn(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the predict_churn tool."""
    try:
        result = predict_churn(params)
        return {
            "success": True,
            "churn_probability": result.get("churn_probability", 0.0),
            "risk_tier": result.get("risk_tier", "unknown"),
            "top_risk_factors": result.get("top_risk_factors", []),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Prediction failed: {str(e)}",
        }


# ========== TOOL: LOOKUP_CUSTOMER ==========

# Mock customer database
CUSTOMER_DATABASE = {
    "CUST001": {
        "customer_id": "CUST001",
        "name": "John Smith",
        "age": 28,
        "gender": "male",
        "tenure_months": 2,
        "contract_type": "month-to-month",
        "monthly_charges": 120.0,
        "total_charges": 240.0,
        "internet_service": "fiber",
        "phone_service": "yes",
        "avg_monthly_gb_used": 450.0,
        "num_support_tickets": 8,
        "avg_monthly_minutes": 150.0,
        "satisfaction_score": 2.0,
        "payment_method": "electronic check",
        "num_additional_services": 1,
        "last_interaction_date": "2026-05-15",
        "account_status": "active",
    },
    "CUST002": {
        "customer_id": "CUST002",
        "name": "Sarah Johnson",
        "age": 45,
        "gender": "female",
        "tenure_months": 24,
        "contract_type": "two year",
        "monthly_charges": 85.0,
        "total_charges": 2040.0,
        "internet_service": "dsl",
        "phone_service": "yes",
        "avg_monthly_gb_used": 50.0,
        "num_support_tickets": 2,
        "avg_monthly_minutes": 200.0,
        "satisfaction_score": 4.5,
        "payment_method": "bank transfer (automatic)",
        "num_additional_services": 3,
        "last_interaction_date": "2026-06-01",
        "account_status": "active",
    },
    "CUST003": {
        "customer_id": "CUST003",
        "name": "Mike Davis",
        "age": 35,
        "gender": "male",
        "tenure_months": 6,
        "contract_type": "month-to-month",
        "monthly_charges": 95.0,
        "total_charges": 570.0,
        "internet_service": "fiber",
        "phone_service": "no",
        "avg_monthly_gb_used": 300.0,
        "num_support_tickets": 5,
        "avg_monthly_minutes": 100.0,
        "satisfaction_score": 2.5,
        "payment_method": "electronic check",
        "num_additional_services": 0,
        "last_interaction_date": "2026-04-20",
        "account_status": "active",
    },
}

LOOKUP_CUSTOMER_SCHEMA = {
    "name": "lookup_customer",
    "description": "Retrieves a customer profile by ID. Returns demographics, contract, tenure, charges, and satisfaction.",
    "parameters": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "The customer ID (e.g., CUST001)"},
        },
        "required": ["customer_id"],
    }
}


def execute_lookup_customer(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the lookup_customer tool."""
    customer_id = params.get("customer_id", "").upper()
    if customer_id in CUSTOMER_DATABASE:
        return {
            "success": True,
            "customer": CUSTOMER_DATABASE[customer_id],
        }
    else:
        return {
            "success": False,
            "error": f"Customer {customer_id} not found in database.",
            "available_customers": list(CUSTOMER_DATABASE.keys()),
        }


# ========== TOOL: GET_RETENTION_OFFERS ==========

RETENTION_OFFERS = {
    "low": {
        "month-to-month": [
            {"id": "OFF001", "name": "Loyalty Bonus", "description": "5% discount on monthly charges", "discount_percent": 5},
            {"id": "OFF002", "name": "Free Upgrade Month", "description": "One month free service", "value": "$95"},
        ],
        "one year": [
            {"id": "OFF003", "name": "Contract Extension", "description": "Extend to 2-year contract for 10% discount", "discount_percent": 10},
        ],
        "two year": [
            {"id": "OFF004", "name": "Premium Services Upgrade", "description": "Free premium services for 3 months", "value": "$30/month"},
        ],
    },
    "medium": {
        "month-to-month": [
            {"id": "OFF005", "name": "Retention Discount", "description": "10% discount for 12 months", "discount_percent": 10},
            {"id": "OFF006", "name": "Service Enhancement", "description": "Free upgrade to fiber", "value": "Worth $30/month"},
            {"id": "OFF007", "name": "Contract Incentive", "description": "Switch to 1-year contract, get 8% discount", "discount_percent": 8},
        ],
        "one year": [
            {"id": "OFF008", "name": "Mid-Tier Upgrade", "description": "Free device upgrade worth $200", "value": "$200"},
        ],
        "two year": [
            {"id": "OFF009", "name": "Loyalty Extension", "description": "Renew 2-year contract for 7% discount", "discount_percent": 7},
        ],
    },
    "high": {
        "month-to-month": [
            {"id": "OFF010", "name": "Save-Customer Package", "description": "15% discount + free premium support for 6 months", "discount_percent": 15},
            {"id": "OFF011", "name": "Executive Offer", "description": "Switch to 2-year contract for 20% discount", "discount_percent": 20},
            {"id": "OFF012", "name": "Premium Concierge", "description": "Free dedicated account manager for 6 months", "value": "Premium support"},
        ],
        "one year": [
            {"id": "OFF013", "name": "High-Risk Retention", "description": "12% discount + free device + priority support", "discount_percent": 12},
        ],
        "two year": [
            {"id": "OFF014", "name": "VIP Retention", "description": "10% discount on current contract", "discount_percent": 10},
        ],
    },
}

GET_RETENTION_OFFERS_SCHEMA = {
    "name": "get_retention_offers",
    "description": "Returns retention offers filtered by risk tier and contract type.",
    "parameters": {
        "type": "object",
        "properties": {
            "risk_tier": {"type": "string", "enum": ["low", "medium", "high"], "description": "Customer risk tier"},
            "contract_type": {"type": "string", "enum": ["month-to-month", "one year", "two year"], "description": "Customer contract type"},
        },
        "required": ["risk_tier", "contract_type"],
    }
}


def execute_get_retention_offers(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the get_retention_offers tool."""
    risk_tier = params.get("risk_tier", "").lower()
    contract_type = params.get("contract_type", "").lower()
    
    if risk_tier in RETENTION_OFFERS and contract_type in RETENTION_OFFERS[risk_tier]:
        offers = RETENTION_OFFERS[risk_tier][contract_type]
        return {
            "success": True,
            "risk_tier": risk_tier,
            "contract_type": contract_type,
            "offers": offers,
            "offer_count": len(offers),
        }
    else:
        return {
            "success": False,
            "error": f"No offers found for risk tier '{risk_tier}' and contract type '{contract_type}'.",
        }


# ========== TOOL: LOG_INTERACTION ==========

LOG_INTERACTION_SCHEMA = {
    "name": "log_interaction",
    "description": "Records the outcome of a retention conversation in the system.",
    "parameters": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Customer ID"},
            "interaction_type": {"type": "string", "enum": ["offer_presented", "escalated", "retention_successful", "retention_failed", "no_action"], "description": "Type of interaction"},
            "offer_id": {"type": "string", "description": "Offer ID if applicable"},
            "notes": {"type": "string", "description": "Additional notes about the interaction"},
            "outcome": {"type": "string", "description": "Outcome summary"},
        },
        "required": ["customer_id", "interaction_type"],
    }
}


INTERACTION_LOG = []


def execute_log_interaction(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the log_interaction tool."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "customer_id": params.get("customer_id"),
        "interaction_type": params.get("interaction_type"),
        "offer_id": params.get("offer_id"),
        "notes": params.get("notes", ""),
        "outcome": params.get("outcome", ""),
    }
    INTERACTION_LOG.append(log_entry)
    return {
        "success": True,
        "message": f"Interaction logged for customer {params.get('customer_id')}",
        "log_entry_id": len(INTERACTION_LOG),
    }


# ========== TOOL: ESCALATE_TO_SUPERVISOR ==========

ESCALATE_TO_SUPERVISOR_SCHEMA = {
    "name": "escalate_to_supervisor",
    "description": "Transfers the case to a human supervisor with full context summary.",
    "parameters": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Customer ID"},
            "reason": {"type": "string", "description": "Reason for escalation"},
            "context_summary": {"type": "string", "description": "Summary of conversation and findings"},
            "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "description": "Priority level"},
        },
        "required": ["customer_id", "reason"],
    }
}


def execute_escalate_to_supervisor(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the escalate_to_supervisor tool."""
    escalation = {
        "timestamp": datetime.now().isoformat(),
        "customer_id": params.get("customer_id"),
        "reason": params.get("reason"),
        "context_summary": params.get("context_summary", ""),
        "priority": params.get("priority", "medium"),
        "status": "escalated",
    }
    return {
        "success": True,
        "message": f"Case escalated to supervisor for customer {params.get('customer_id')}",
        "escalation_id": f"ESC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "escalation_details": escalation,
    }


# ========== TOOL REGISTRY ==========

TOOLS = {
    "predict_churn": {
        "schema": PREDICT_CHURN_SCHEMA,
        "execute": execute_predict_churn,
    },
    "lookup_customer": {
        "schema": LOOKUP_CUSTOMER_SCHEMA,
        "execute": execute_lookup_customer,
    },
    "get_retention_offers": {
        "schema": GET_RETENTION_OFFERS_SCHEMA,
        "execute": execute_get_retention_offers,
    },
    "log_interaction": {
        "schema": LOG_INTERACTION_SCHEMA,
        "execute": execute_log_interaction,
    },
    "escalate_to_supervisor": {
        "schema": ESCALATE_TO_SUPERVISOR_SCHEMA,
        "execute": execute_escalate_to_supervisor,
    },
}


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Get all tool schemas for the LLM."""
    return [tool["schema"] for tool in TOOLS.values()]


def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name."""
    if tool_name not in TOOLS:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    try:
        return TOOLS[tool_name]["execute"](parameters)
    except Exception as e:
        return {"success": False, "error": f"Tool execution failed: {str(e)}"}
