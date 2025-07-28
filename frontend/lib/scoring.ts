import type { DashboardMetrics } from './api';

interface MetricConfig {
  weight: number;
  min?: number;
  max?: number;
}

interface MetricsConfig {
  firstResponseTimeSeconds: MetricConfig;
  avgIssueResolutionSeconds: MetricConfig;
  prReviewTimeSeconds: MetricConfig;
}

const SECONDS_IN_DAY = 86400;

// TODO: We should cosider refining these default min/max values.
//  We cad do sampling repositories and using statistical measures (like percentiles) 
const DEFAULT_MIN_TIME = 0;
const DEFAULT_MAX_TIME_RESPONSE = 7 * SECONDS_IN_DAY; // 7 days in seconds
const DEFAULT_MAX_TIME_RESOLUTION = 30 * SECONDS_IN_DAY; // 30 days in seconds
const DEFAULT_MAX_TIME_PR_REVIEW = 5 * SECONDS_IN_DAY; // 5 days in seconds


const METRIC_CONFIGS: MetricsConfig = {
  firstResponseTimeSeconds: {
    weight: 0.40, 
    min: DEFAULT_MIN_TIME,
    max: DEFAULT_MAX_TIME_RESPONSE
  },
  avgIssueResolutionSeconds: {
    weight: 0.20, 
    min: DEFAULT_MIN_TIME,
    max: DEFAULT_MAX_TIME_RESOLUTION
  },
  prReviewTimeSeconds: {
    weight: 0.40, 
    min: DEFAULT_MIN_TIME,
    max: DEFAULT_MAX_TIME_PR_REVIEW
  }
};

function normalizeMetric(currentValue: number, minValue: number, maxValue: number): number {
  if (minValue === maxValue) {
    // Avoid division by zero; if min and max are same, score 100 if current is at that value, else 0.
    return currentValue === minValue ? 100 : 0;
  }
  const cappedValue = Math.max(minValue, Math.min(currentValue, maxValue));
  const normalized = (maxValue - cappedValue) / (maxValue - minValue);
  return Math.max(0, Math.min(normalized * 100, 100));
}

export function calculateOsScore(metrics: DashboardMetrics): number {
  let totalWeightedScore = 0;

  for (const key in METRIC_CONFIGS) {
    const metricKey = key as keyof MetricsConfig;
    const config = METRIC_CONFIGS[metricKey];
    if (metrics.hasOwnProperty(metricKey)) {
      const rawValue = metrics[metricKey as keyof DashboardMetrics] as number;
      
      const minValue = config.min ?? DEFAULT_MIN_TIME;
      
      let maxValue: number;
      if (config.max !== undefined) {
        maxValue = config.max;
      } else {
        if (metricKey === 'firstResponseTimeSeconds') {
          maxValue = DEFAULT_MAX_TIME_RESPONSE;
        } else if (metricKey === 'avgIssueResolutionSeconds') {
          maxValue = DEFAULT_MAX_TIME_RESOLUTION;
        } else if (metricKey === 'prReviewTimeSeconds') {
          maxValue = DEFAULT_MAX_TIME_PR_REVIEW;
        } else {
          console.warn(`Metric ${metricKey} is missing a 'max' configuration and a specific default.`);
          maxValue = DEFAULT_MAX_TIME_RESPONSE; // Assign a generic default to prevent errors
        }
      }
      const normalizedScore = normalizeMetric(rawValue, minValue, maxValue);
      totalWeightedScore += normalizedScore * config.weight;
    }
  }
  return parseFloat(totalWeightedScore.toFixed(2));
}