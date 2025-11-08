// src/api.ts
import axios from "axios";

const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8001";

export type KPIResponse = {
  rows: number;
  columns: string[];
  data: Record<string, unknown>[];
};

export type ABSampleResponse = {
  sample: {
    [key: string]: {
      success: number;
      total: number;
    };
  };
};

export type ABTestResult = {
  p_value: number;
  chi2: number;
  significant: boolean;
};

export async function runSQL(
  sqlFile: string,
  params: Array<{ name: string; type: string; value: string }>
): Promise<KPIResponse> {
  const res = await axios.post(`${API_BASE}/kpi/query`, {
    sql_file: sqlFile,
    params,
  });
  return res.data as KPIResponse;
}

export async function getABSample(): Promise<ABSampleResponse> {
  const res = await axios.get(`${API_BASE}/ab/sample`);
  return res.data as ABSampleResponse;
}

export async function runABTest(payload: {
  a_success: number;
  a_total: number;
  b_success: number;
  b_total: number;
  alpha: number;
}): Promise<ABTestResult> {
  const res = await axios.post(`${API_BASE}/ab/test`, payload);
  return res.data as ABTestResult;
}

export async function trainML(): Promise<unknown> {
  const res = await axios.post(`${API_BASE}/ml/train`);
  return res.data;
}

export async function latestML(): Promise<unknown> {
  const res = await axios.get(`${API_BASE}/ml/latest`);
  return res.data;
}
