const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Schema = {
  numeric_features: string[];
  categorical_features: Record<string, string[]>;
  binary_features: string[];
};

export type Metrics = {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  roc_auc: number;
  confusion_matrix: number[][];
  train_rows: number;
  test_rows: number;
  churn_rate: number;
};

export type FeatureImportance = { feature: string; importance: number }[];

export type Metadata = {
  metrics: Metrics;
  feature_importance: FeatureImportance;
  schema: Schema;
};

export type CustomerInput = {
  tenure_months: number;
  monthly_charges: number;
  total_charges: number;
  num_support_calls: number;
  contract_type: string;
  internet_service: string;
  payment_method: string;
  partner: string;
  dependents: string;
  tech_support: string;
  online_security: string;
  paperless_billing: string;
  senior_citizen: number;
};

export type PredictionResult = {
  churn_probability: number;
  risk_level: "Low" | "Medium" | "High";
  prediction: "Churn" | "Stay";
  explanation?: { top_factors: { feature: string; value: string | number; reference_value: string | number; probability_difference: number }[] };
  explanation_method?: string;
};

export type BatchResult = {
  summary: {
    total_customers: number;
    predicted_churn_count: number;
    avg_churn_probability: number;
    high_risk_count: number;
  };
  rows: Record<string, unknown>[];
};

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || `Request failed: ${res.status}`));
  }
  return res.json();
}

export const api = {
  metadata: () => req<Metadata>("/metadata"),
  predict: (customer: CustomerInput) =>
    req<PredictionResult>("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(customer),
    }),
  predictBatch: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return req<BatchResult>("/predict-batch", { method: "POST", body: form });
  },
};
