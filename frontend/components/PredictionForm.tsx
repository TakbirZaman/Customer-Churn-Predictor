"use client";

import { useState } from "react";
import type { CustomerInput, Schema } from "@/lib/api";

type Props = {
  schema: Schema;
  onSubmit: (customer: CustomerInput) => void;
  loading: boolean;
};

const DEFAULTS: CustomerInput = {
  tenure_months: 8,
  monthly_charges: 74,
  total_charges: 592,
  num_support_calls: 2,
  contract_type: "Month-to-month",
  internet_service: "Fiber optic",
  payment_method: "Electronic check",
  partner: "No",
  dependents: "No",
  tech_support: "No",
  online_security: "No",
  paperless_billing: "Yes",
  senior_citizen: 0,
};

const LABELS: Record<string, string> = {
  tenure_months: "Tenure (months)",
  monthly_charges: "Monthly charges (source currency)",
  total_charges: "Total charges (source currency)",
  num_support_calls: "Support calls (last 90d)",
  contract_type: "Contract type",
  internet_service: "Internet service",
  payment_method: "Payment method",
  partner: "Has partner",
  dependents: "Has dependents",
  tech_support: "Tech support add-on",
  online_security: "Online security add-on",
  paperless_billing: "Paperless billing",
  senior_citizen: "Senior citizen",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-[var(--text-muted)]">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] outline-none transition focus:border-[var(--brand)] focus:ring-1 focus:ring-[var(--brand)]";

export default function PredictionForm({ schema, onSubmit, loading }: Props) {
  const [form, setForm] = useState<CustomerInput>(DEFAULTS);

  const update = <K extends keyof CustomerInput>(key: K, value: CustomerInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(form);
      }}
      className="grid grid-cols-2 gap-x-4 gap-y-4"
    >
      {schema.numeric_features.map((key) => (
        <Field key={key} label={LABELS[key] ?? key}>
          <input
            type="number"
            className={inputCls}
            value={form[key as keyof CustomerInput] as number}
            onChange={(e) => update(key as keyof CustomerInput, Number(e.target.value) as never)}
            min={0}
            step={key.includes("charges") ? "0.01" : "1"}
            max={key === "tenure_months" ? 100 : key === "num_support_calls" ? 20 : undefined}
            required
          />
        </Field>
      ))}

      {Object.entries(schema.categorical_features).map(([key, options]) => (
        <Field key={key} label={LABELS[key] ?? key}>
          <select
            className={inputCls}
            value={form[key as keyof CustomerInput] as string}
            onChange={(e) => update(key as keyof CustomerInput, e.target.value as never)}
          >
            {options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </Field>
      ))}

      <Field label={LABELS.senior_citizen}>
        <select
          className={inputCls}
          value={form.senior_citizen}
          onChange={(e) => update("senior_citizen", Number(e.target.value) as never)}
        >
          <option value={0}>No</option>
          <option value={1}>Yes</option>
        </select>
      </Field>

      <button
        type="submit"
        disabled={loading}
        className="col-span-2 mt-2 rounded-lg bg-[var(--brand)] py-2.5 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
      >
        {loading ? "Scoring…" : "Predict churn risk"}
      </button>
    </form>
  );
}
