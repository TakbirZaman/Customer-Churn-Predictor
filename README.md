# Customer Churn Predictor

Upload customers, see who is likely to leave. I wanted to try a full ML + app loop, not just a notebook.

What it does:
- Predict churn for one customer or bulk CSV
- Shows risk score + reason
- Simple dashboard to browse results

Stack: Python (scikit-learn), React frontend, Node backend

Run it:
```bash
# train / backend
cd ml
pip install -r requirements.txt
python train.py
# frontend
cd ../frontend
npm install
npm run dev
```
Try with `sample_customers.csv`.
