"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FeatureImportance } from "@/lib/api";

const NICE_NAME: Record<string, string> = {
  tenure_months: "Tenure",
  monthly_charges: "Monthly charges",
  total_charges: "Total charges",
  num_support_calls: "Support calls",
  "contract_type_Month-to-month": "Month-to-month contract",
  "contract_type_Two year": "Two-year contract",
  "contract_type_One year": "One-year contract",
  "payment_method_Electronic check": "Pays by e-check",
  "internet_service_Fiber optic": "Fiber internet",
  "online_security_No": "No online security",
  "tech_support_No": "No tech support",
  "partner_No": "No partner",
  "partner_Yes": "Has partner",
};

export default function FeatureImportanceChart({ data }: { data: FeatureImportance }) {
  const chartData = data
    .slice(0, 8)
    .map((d) => ({ name: NICE_NAME[d.feature] ?? d.feature, value: d.importance }))
    .reverse();

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
        <XAxis type="number" tick={{ fill: "var(--text-faint)", fontSize: 11 }} axisLine={{ stroke: "var(--border)" }} tickLine={false} />
        <YAxis
          type="category"
          dataKey="name"
          width={140}
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          axisLine={{ stroke: "var(--border)" }}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: "var(--surface-2)" }}
          contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "var(--text)" }}
          formatter={((v: number) => [(Number(v ?? 0) * 100).toFixed(1) + "%", "Importance"]) as never}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {chartData.map((_, i) => (
            <Cell key={i} fill="var(--brand)" opacity={0.55 + (i / chartData.length) * 0.45} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
