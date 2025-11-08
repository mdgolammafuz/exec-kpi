// src/api.ts
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8001",
});

export type KPIResponse = {
  rows: number;
  columns: string[];
  data: Record<string, unknown>[];
};

export type SQLParam = {
  name: string;
  type: string;
  value: string | number;
};

export type ABSampleResponse = {
  sample: Record<string, { success: number; total: number }>;
};

export type ABTestPayload = {
  a_success: number;
  a_total: number;
  b_success: number;
  b_total: number;
  alpha: number;
};

export type ABTestResult = {
  p_value: number;
  chi2: number;
  significant: boolean;
};

export const runSQL = (sql_file: string, params?: SQLParam[]) =>
  api
    .post<KPIResponse>("/kpi/query", { sql_file, params })
    .then((res) => res.data);

export const getABSample = () =>
  api.get<ABSampleResponse>("/ab/sample").then((res) => res.data);

export const runABTest = (payload: ABTestPayload) =>
  api.post<ABTestResult>("/ab/test", payload).then((res) => res.data);

// ML are placeholders for now
export const trainML = (target: string) =>
  api.post("/ml/train", { target }).then((res) => res.data);

export const latestML = () =>
  api.get("/ml/latest").then((res) => res.data);
