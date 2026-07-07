"use client";

import { useEffect, useState } from "react";
import { Radar, Activity, TrendingUp, Database } from "lucide-react";
import { api, type CustomerInput, type Metadata, type PredictionResult } from "@/lib/api";
import PredictionForm from "@/components/PredictionForm";
import RiskGauge from "@/components/RiskGauge";
import FeatureImportanceChart from "@/components/FeatureImportanceChart";
import BatchUpload from "@/components/BatchUpload";

export default function Home() {
  const [meta, setMeta] = useState<Metadata | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [metaError, setMetaError] = useState<string | null>(null);

  useEffect(() => {
    api
      .metadata()
      .then(setMeta)
      .catch((e) => setMetaError(e instanceof Error ? e.message : "Could not reach the API"));
  }, []);

  const handlePredict = async (customer: CustomerInput) => {
    setLoading(true);
    try {
      const res = await api.predict(customer);
      setResult(res);
    } catch {
      // surfaced via absence of result; keep UI calm
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
      {/* header */}
      <header className="mb-10 flex flex-wrap items-start justify-between gap-6">
        <div className="flex items-start gap-3">
          <div className="relative mt-1 flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)]">
            <Radar size={18} className="text-[var(--brand)]" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight">Churn Radar</h1>
            <p className="text-sm text-[var(--text-muted)]">
              Score subscriber churn risk one customer at a time, or upload a book of business.
            </p>
          </div>
        </div>

        {meta && (
          <div className="flex gap-3">
            <MetricChip icon={<TrendingUp size={12} />} label="ROC-AUC" value={meta.metrics.roc_auc.toFixed(3)} />
            <MetricChip icon={<Activity size={12} />} label="Recall" value={`${(meta.metrics.recall * 100).toFixed(0)}%`} />
            <MetricChip icon={<Database size={12} />} label="Trained on" value={`${meta.metrics.train_rows.toLocaleString()} rows`} />
          </div>
        )}
      </header>

      {metaError && (
        <div className="mb-6 rounded-lg border border-[var(--risk)]/40 bg-[var(--risk-dim)] px-4 py-3 text-sm text-[var(--risk)]">
          Can&apos;t reach the model API at the configured URL. Make sure the FastAPI backend is running
          (see README) — {metaError}
        </div>
      )}

      {/* single prediction */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 lg:col-span-3">
          <h2 className="font-display mb-5 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            Customer profile
          </h2>
          {meta ? (
            <PredictionForm schema={meta.schema} onSubmit={handlePredict} loading={loading} />
          ) : (
            <p className="text-sm text-[var(--text-faint)]">Loading model schema…</p>
          )}
        </div>

        <div className="flex flex-col items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 lg:col-span-2">
          <h2 className="font-display mb-2 self-start text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            Predicted risk
          </h2>
          {result ? (
            <RiskGauge probability={result.churn_probability} riskLevel={result.risk_level} />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center py-10 text-center">
              <Radar size={32} className="mb-3 text-[var(--text-faint)]" />
              <p className="text-sm text-[var(--text-faint)]">
                Fill in a profile and run a prediction to see the risk gauge.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* feature importance */}
      {meta && (
        <section className="mt-6 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6">
          <h2 className="font-display mb-1 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            What drives churn in this model
          </h2>
          <p className="mb-4 text-xs text-[var(--text-faint)]">
            Relative importance across all training examples — not specific to the customer above.
          </p>
          <FeatureImportanceChart data={meta.feature_importance} />
        </section>
      )}

      {/* batch upload */}
      <section className="mt-6 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6">
        <h2 className="font-display mb-1 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
          Bulk scoring
        </h2>
        <p className="mb-4 text-xs text-[var(--text-faint)]">
          Upload a CSV of your customer base to flag every at-risk account at once.
        </p>
        <BatchUpload />
      </section>

      <footer className="mt-10 text-center text-xs text-[var(--text-faint)]">
        Random Forest classifier · trained on synthetic demo data · replace with your own export to go live
      </footer>
    </div>
  );
}

function MetricChip({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2">
      <span className="text-[var(--brand)]">{icon}</span>
      <div>
        <div className="text-[10px] uppercase tracking-wide text-[var(--text-faint)]">{label}</div>
        <div className="font-data text-sm font-semibold">{value}</div>
      </div>
    </div>
  );
}
