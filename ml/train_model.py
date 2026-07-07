"""
Trains a customer churn prediction model and exports everything the API needs to serve it:
  - churn_model.pkl        trained classifier
  - preprocessor.pkl       fitted encoder/scaler pipeline
  - metrics.json           accuracy, precision, recall, f1, roc_auc, confusion matrix
  - feature_importance.json
  - schema.json            column names/types the API expects, for frontend form generation
"""
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("/home/claude/churn-predictor/ml/customer_churn.csv")

TARGET = "churn"
DROP_COLS = ["customer_id"]
y = df[TARGET]
X = df.drop(columns=[TARGET] + DROP_COLS)

numeric_features = ["tenure_months", "monthly_charges", "total_charges", "num_support_calls"]
categorical_features = [c for c in X.columns if c not in numeric_features and c != "senior_citizen"]
binary_passthrough = ["senior_citizen"]

preprocessor = ColumnTransformer(transformers=[
    ("num", StandardScaler(), numeric_features),
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ("bin", "passthrough", binary_passthrough),
])

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

X_train_t = preprocessor.fit_transform(X_train)
X_test_t = preprocessor.transform(X_test)

model = RandomForestClassifier(
    n_estimators=300, max_depth=10, min_samples_leaf=5,
    class_weight="balanced", random_state=42, n_jobs=-1
)
model.fit(X_train_t, y_train)

y_pred = model.predict(X_test_t)
y_proba = model.predict_proba(X_test_t)[:, 1]

metrics = {
    "accuracy": round(accuracy_score(y_test, y_pred), 4),
    "precision": round(precision_score(y_test, y_pred), 4),
    "recall": round(recall_score(y_test, y_pred), 4),
    "f1_score": round(f1_score(y_test, y_pred), 4),
    "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
    "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    "train_rows": len(X_train),
    "test_rows": len(X_test),
    "churn_rate": round(float(y.mean()), 4),
}
print(json.dumps(metrics, indent=2))
print(classification_report(y_test, y_pred))

# Feature importance mapped back to readable names
feature_names = (
    numeric_features
    + list(preprocessor.named_transformers_["cat"].get_feature_names_out(categorical_features))
    + binary_passthrough
)
importances = model.feature_importances_
feat_imp = sorted(
    [{"feature": f, "importance": round(float(i), 4)} for f, i in zip(feature_names, importances)],
    key=lambda x: -x["importance"]
)[:12]

schema = {
    "numeric_features": numeric_features,
    "categorical_features": {
        col: sorted(X[col].dropna().unique().tolist()) for col in categorical_features
    },
    "binary_features": binary_passthrough,
}

joblib.dump(model, "/home/claude/churn-predictor/backend/churn_model.pkl")
joblib.dump(preprocessor, "/home/claude/churn-predictor/backend/preprocessor.pkl")
with open("/home/claude/churn-predictor/backend/metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)
with open("/home/claude/churn-predictor/backend/feature_importance.json", "w") as f:
    json.dump(feat_imp, f, indent=2)
with open("/home/claude/churn-predictor/backend/schema.json", "w") as f:
    json.dump(schema, f, indent=2)

print("\nSaved model artifacts to backend/")
