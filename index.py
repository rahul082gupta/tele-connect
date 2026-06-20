from src.predict import predict_churn


sample_customer = {

    "age": 28,

    "gender": "male",

    "tenure_months": 2,

    "contract_type": "month-to-month",

    "monthly_charges": 120,

    "total_charges": 240,

    "internet_service": "fiber",

    "phone_service": "yes",

    "avg_monthly_gb_used": 450,

    "num_support_tickets": 8,

    "avg_monthly_minutes": 150,

    "satisfaction_score": 2,

    "payment_method": "electronic check",

    "num_additional_services": 1,

    "last_interaction_date": "2026-05-15"

}

result = predict_churn(
    sample_customer
)

print(result)