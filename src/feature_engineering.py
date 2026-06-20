import pandas as pd
import numpy as np


def create_features(df):

    df = df.copy()

    # Monthly value over tenure

    tenure_denom = (
        df["tenure_months"] + 1
    ).replace({0: np.nan})

    df["charge_per_month_of_tenure"] = (
        df["total_charges"]
        / tenure_denom
    )

    # Support intensity

    df["support_ticket_rate"] = (
        df["num_support_tickets"]
        / tenure_denom
    )

    # Usage intensity

    df["usage_per_month"] = (
        (
            df["avg_monthly_gb_used"]
            +
            df["avg_monthly_minutes"]
        )
        /
        tenure_denom
    )

    # Customer value

    df["customer_lifetime_value"] = (
        df["monthly_charges"]
        *
        df["tenure_months"]
    )

    return df