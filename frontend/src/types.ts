export interface Meta {
  first_delivery_day: string;
  last_delivery_day: string;
  default_cutoff_hour: number;
  timezone: string;
  actual_points: number;
  forecast_points: number;
}

export interface ForecastPoint {
  target: string;
  forecast_mw: number;
  published: string;
  horizon_h: number;
  actual_mw: number | null;
  error_mw: number | null;
  low_mw: number | null;
  high_mw: number | null;
}

export interface Band {
  p10_error_mw: number;
  p90_error_mw: number;
  samples: number;
}

export interface DayForecast {
  delivery_day: string;
  cutoff: string;
  cutoff_hour: number;
  forecast_runs_used: string[];
  summary: {
    hours: number;
    mean_forecast_mw: number | null;
    min_forecast_mw: number | null;
    max_forecast_mw: number | null;
    total_forecast_mwh: number | null;
  };
  band: Band | null;
  points: ForecastPoint[];
}

export interface Summary {
  n: number;
  mae_mw?: number;
  rmse_mw?: number;
  bias_mw?: number;
  mae_bias_removed_mw?: number;
  mape_pct?: number | null;
  median_abs_error_mw?: number;
  p90_abs_error_mw?: number;
  error_p10_mw?: number;
  error_p50_mw?: number;
  error_p90_mw?: number;
  mean_actual_mw?: number;
}

export interface Accuracy {
  first_day: string;
  last_day: string;
  cutoff_hour: number;
  overall: Summary;
  by_day: (Summary & { date: string })[];
  by_hour: { hour: number; n: number; mae_mw: number; bias_mw: number }[];
  histogram: { from_mw: number; to_mw: number; count: number }[];
  by_horizon: { from_h: number; to_h: number; n: number; mae_mw: number; bias_mw: number }[];
}
