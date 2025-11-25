#!/usr/bin/env python3
"""
A/B Testing Pipeline Verification Script

This script demonstrates the end-to-end A/B testing pipeline:
1. Queries ab_metrics from BigQuery
2. Calls /ab/test endpoint with the metrics
3. Displays formatted results with interpretation

Usage:
    python verify_ab_pipeline.py

Requirements:
    - google-cloud-bigquery
    - requests
    
Environment:
    Uses default GCP credentials (gcloud auth application-default login)
"""

import json
import sys
import os

try:
    from google.cloud import bigquery
    import requests
except ImportError:
    print("ERROR: Missing dependencies. Install with:")
    print("  pip install google-cloud-bigquery requests")
    sys.exit(1)


# Configuration
PROJECT_ID = "exec-kpi"
DATASET = "execkpi_execkpi"
API_BASE = "https://execkpi-backend-latest.onrender.com"


def get_bq_client():
    """Initialize BigQuery client with default credentials."""
    return bigquery.Client(project=PROJECT_ID)


def query_ab_metrics():
    """Query ab_metrics from BigQuery and return as dict."""
    print(f"[INFO] Querying ab_metrics from {PROJECT_ID}.{DATASET}...")
    print()
    
    client = get_bq_client()
    query = f"""
    SELECT 
        ab_group,
        users,
        converters,
        conversion_rate
    FROM `{PROJECT_ID}.{DATASET}.ab_metrics`
    ORDER BY ab_group
    """
    
    try:
        df = client.query(query).result().to_dataframe()
    except Exception as e:
        print(f"[ERROR] BigQuery query failed: {e}")
        print()
        print("Troubleshooting:")
        print("1. Run: dbt build --select ab_group ab_metrics")
        print("2. Check GCP credentials: gcloud auth application-default login")
        print("3. Verify dataset exists: exec-kpi.execkpi_execkpi")
        sys.exit(1)
    
    if df.empty:
        print("[ERROR] No data returned from ab_metrics")
        print("Run: dbt build --select ab_group ab_metrics")
        sys.exit(1)
    
    # Print table
    print("BigQuery Results:")
    print("-" * 75)
    print(f"{'Group':<10} {'Users':<12} {'Converters':<14} {'Conv. Rate':<14}")
    print("-" * 75)
    for _, row in df.iterrows():
        rate_pct = row['conversion_rate'] * 100
        print(f"{row['ab_group']:<10} {row['users']:<12,} {row['converters']:<14,} {rate_pct:<14.2f}%")
    print("-" * 75)
    print()
    
    # Convert to dict for API call
    metrics = {}
    for _, row in df.iterrows():
        metrics[row['ab_group']] = {
            'total': int(row['users']),
            'success': int(row['converters']),
            'rate': float(row['conversion_rate'])
        }
    
    return metrics


def call_ab_test(metrics):
    """Call /ab/test endpoint with metrics and return results."""
    print(f"[INFO] Calling {API_BASE}/ab/test...")
    print()
    
    payload = {
        "a_success": metrics['A']['success'],
        "a_total": metrics['A']['total'],
        "b_success": metrics['B']['success'],
        "b_total": metrics['B']['total'],
        "alpha": 0.05
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/ab/test",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API call failed: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check backend is running: curl https://execkpi-backend-latest.onrender.com/healthz")
        print("2. Verify API_BASE is correct")
        sys.exit(1)


def display_results(metrics, result):
    """Display formatted test results with statistical interpretation."""
    print("=" * 80)
    print("A/B TEST RESULTS")
    print("=" * 80)
    print()
    
    # Group statistics
    print("GROUP STATISTICS:")
    print("-" * 80)
    a_rate = metrics['A']['rate'] * 100
    b_rate = metrics['B']['rate'] * 100
    print(f"  Group A: {metrics['A']['success']:,} / {metrics['A']['total']:,} users = {a_rate:.2f}%")
    print(f"  Group B: {metrics['B']['success']:,} / {metrics['B']['total']:,} users = {b_rate:.2f}%")
    print()
    
    # Uplift
    uplift_pct = result['uplift'] * 100
    print(f"UPLIFT: {uplift_pct:+.2f} percentage points")
    print()
    
    # Sample Ratio Mismatch
    srm_p = result['srm_p']
    srm_status = "PASS" if srm_p > 0.001 else "FAIL"
    print(f"SAMPLE RATIO MISMATCH (SRM) CHECK:")
    print(f"   SRM p-value: {srm_p:.4f} [{srm_status}]")
    if srm_p > 0.001:
        print("   Groups are balanced (50/50 split verified)")
    else:
        print("   WARNING: Groups are imbalanced! Check randomization.")
    print()
    
    # Statistical significance
    p_value = result['p_value']
    ci_low, ci_high = result['ci_95']
    significant = result['significant']
    
    print(f"STATISTICAL TEST (Two-Proportion Z-Test):")
    print(f"   Null hypothesis: conversion_rate_A = conversion_rate_B")
    print(f"   p-value: {p_value:.4f}")
    print(f"   95% Confidence Interval: [{ci_low*100:+.2f}%, {ci_high*100:+.2f}%]")
    print()
    
    if significant:
        print(f"   Result: SIGNIFICANT (p < 0.05)")
        print(f"   Decision: Reject null hypothesis")
        print(f"   Interpretation: Group B has a significant {uplift_pct:+.2f}pp difference vs Group A")
    else:
        print(f"   Result: NOT SIGNIFICANT (p >= 0.05)")
        print(f"   Decision: Fail to reject null hypothesis")
        print(f"   Interpretation: No statistically significant difference detected")
    print()
    
    # Interpretation for synthetic data context
    print("=" * 80)
    print("INTERPRETATION (Synthetic Data Context):")
    print("=" * 80)
    print()
    
    if not significant and abs(uplift_pct) < 1.0:
        print("EXPECTED RESULT (Null finding is correct):")
        print()
        print("   This is synthetic data with NO REAL TREATMENT applied.")
        print("   The fact that we found no significant difference validates our framework.")
        print()
        print("   What this demonstrates:")
        print("   - Hash-based randomization produced balanced groups (SRM passed)")
        print("   - Statistical test correctly identified no treatment effect")
        print("   - Framework is ready to detect real differences in production")
        print()
        print("   In production with actual experiments, this same code will detect uplift.")
    else:
        print("UNEXPECTED RESULT:")
        print()
        print("   This is synthetic data, so we should not see significant differences.")
        print("   Possible causes:")
        print("   - Random variation (5% chance of Type I error at alpha=0.05)")
        print("   - Data quality issue in source tables")
        print("   - Hash collision in assignment logic")
        print()
        print("   Action: Investigate source data or re-run test.")
    
    print()
    print("=" * 80)


def main():
    """Main execution flow."""
    print()
    print("=" * 80)
    print("ExecKPI A/B Testing Pipeline Verification")
    print("=" * 80)
    print()
    print(f"Configuration:")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Dataset: {DATASET}")
    print(f"  API: {API_BASE}")
    print()
    
    try:
        # Step 1: Query metrics from BigQuery
        metrics = query_ab_metrics()
        
        # Step 2: Call API for statistical test
        result = call_ab_test(metrics)
        
        # Step 3: Display formatted results
        display_results(metrics, result)
        
        print("[SUCCESS] Pipeline verification complete!")
        print()
        
    except KeyboardInterrupt:
        print()
        print("[INFO] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()