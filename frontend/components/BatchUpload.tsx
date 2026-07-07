"use client";

import { useRef, useState } from "react";
import { UploadCloud, FileSpreadsheet } from "lucide-react";
import { api, type BatchResult } from "@/lib/api";

const RISK_COLOR: Record<string, string> = {
  Low: "var(--safe)",
  Medium: "var(--warn)",
  High: "var(--risk)",
};

export default function BatchUpload() {
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BatchResult | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setError(null);
    setLoading(true);
    setFileName(file.name);
    try {
      const res = await api.predictBatch(file);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
          dragOver ? "border-[var(--brand)] bg-[var(--brand-dim)]" : "border-[var(--border)] bg-[var(--surface-2)]"
        }`}
      >
        <UploadCloud size={28} className="text-[var(--text-muted)]" />
        <p className="text-sm text-[var(--text-muted)]">
          Drop a customer CSV here, or <span className="text-[var(--brand)]">browse</span>
        </p>
        <p className="text-xs text-[var(--text-faint)]">
          Needs the same columns as the single-prediction form
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
      </div>

      {loading && <p className="mt-4 text-sm text-[var(--text-muted)]">Scoring {fileName}…</p>}
      {error && <p className="mt-4 text-sm text-[var(--risk)]">{error}</p>}

      {result && (
        <div className="mt-6">
          <div className="mb-4 grid grid-cols-4 gap-3">
            <Stat label="Customers" value={result.summary.total_customers} />
            <Stat label="Predicted to churn" value={result.summary.predicted_churn_count} accent="var(--risk)" />
            <Stat label="High risk" value={result.summary.high_risk_count} accent="var(--warn)" />
            <Stat label="Avg. probability" value={`${(result.summary.avg_churn_probability * 100).toFixed(1)}%`} />
          </div>

          <div className="thin-scroll max-h-72 overflow-auto rounded-lg border border-[var(--border)]">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-[var(--surface-2)] text-[var(--text-muted)]">
                <tr>
                  <th className="px-3 py-2 font-medium">Customer</th>
                  <th className="px-3 py-2 font-medium">Tenure</th>
                  <th className="px-3 py-2 font-medium">Contract</th>
                  <th className="px-3 py-2 font-medium">Probability</th>
                  <th className="px-3 py-2 font-medium">Risk</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr key={i} className="border-t border-[var(--border)]">
                    <td className="px-3 py-2 font-data text-[var(--text-muted)]">
                      {String(row.customer_id ?? `#${i + 1}`)}
                    </td>
                    <td className="px-3 py-2">{String(row.tenure_months ?? "—")}</td>
                    <td className="px-3 py-2">{String(row.contract_type ?? "—")}</td>
                    <td className="px-3 py-2 font-data">
                      {typeof row.churn_probability === "number"
                        ? `${(row.churn_probability * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className="rounded-full px-2 py-0.5 text-[10px] font-medium uppercase"
                        style={{
                          color: RISK_COLOR[String(row.risk_level)] ?? "var(--text-muted)",
                          backgroundColor: `${RISK_COLOR[String(row.risk_level)] ?? "#888"}1a`,
                        }}
                      >
                        {String(row.risk_level ?? "—")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-[var(--text-faint)]">
        <FileSpreadsheet size={11} /> {label}
      </div>
      <div className="font-data mt-1 text-lg font-semibold" style={{ color: accent ?? "var(--text)" }}>
        {value}
      </div>
    </div>
  );
}
