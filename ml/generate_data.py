"""
Generates a realistic synthetic telecom customer churn dataset.
Swap this out with a client's real export (same column names) with zero code changes downstream.
"""
import numpy as np
import pandas as pd

np.random.seed(42)
N = 5000

contract_types = np.random.choice(["Month-to-month", "One year", "Two year"], N, p=[0.55, 0.25, 0.20])
internet_service = np.random.choice(["Fiber optic", "DSL", "No"], N, p=[0.45, 0.35, 0.20])
payment_method = np.random.choice(
    ["Electronic check", "Mailed check", "Bank transfer", "Credit card"], N, p=[0.35, 0.2, 0.225, 0.225]
)

tenure_months = np.random.exponential(scale=24, size=N).clip(0, 72).astype(int)
monthly_charges = np.round(np.random.normal(65, 30, N).clip(18, 120), 2)
total_charges = np.round(monthly_charges * tenure_months * np.random.uniform(0.9, 1.1, N), 2)

senior_citizen = np.random.choice([0, 1], N, p=[0.84, 0.16])
partner = np.random.choice(["Yes", "No"], N, p=[0.48, 0.52])
dependents = np.random.choice(["Yes", "No"], N, p=[0.3, 0.7])
tech_support = np.random.choice(["Yes", "No", "No internet"], N, p=[0.29, 0.49, 0.22])
online_security = np.random.choice(["Yes", "No", "No internet"], N, p=[0.29, 0.49, 0.22])
paperless_billing = np.random.choice(["Yes", "No"], N, p=[0.59, 0.41])
num_support_calls = np.random.poisson(1.5, N).clip(0, 10)

# --- churn probability driven by realistic business logic ---
churn_score = (
    -0.06 * tenure_months
    + 0.025 * monthly_charges
    + 0.9 * (contract_types == "Month-to-month")
    + 0.5 * (internet_service == "Fiber optic")
    + 0.6 * (payment_method == "Electronic check")
    + 0.45 * (tech_support == "No")
    + 0.4 * (online_security == "No")
    + 0.5 * num_support_calls
    + 0.25 * (paperless_billing == "Yes")
    - 0.5 * (partner == "Yes")
    - 0.4 * (dependents == "Yes")
    + np.random.normal(0, 0.6, N)
)
churn_prob = 1 / (1 + np.exp(-(churn_score - 3.0)))
churn = (np.random.rand(N) < churn_prob).astype(int)

df = pd.DataFrame({
    "customer_id": [f"CUST-{10000+i}" for i in range(N)],
    "tenure_months": tenure_months,
    "monthly_charges": monthly_charges,
    "total_charges": total_charges,
    "contract_type": contract_types,
    "internet_service": internet_service,
    "payment_method": payment_method,
    "senior_citizen": senior_citizen,
    "partner": partner,
    "dependents": dependents,
    "tech_support": tech_support,
    "online_security": online_security,
    "paperless_billing": paperless_billing,
    "num_support_calls": num_support_calls,
    "churn": churn,
})

df.to_csv("/home/claude/churn-predictor/ml/customer_churn.csv", index=False)
print(f"Generated {N} rows. Churn rate: {df['churn'].mean():.1%}")
print(df.head())
