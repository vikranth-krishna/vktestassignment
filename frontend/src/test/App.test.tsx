import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";

const meta = {
  first_delivery_day: "2026-01-01",
  last_delivery_day: "2026-01-31",
  default_cutoff_hour: 9,
  timezone: "Europe/London",
  actual_points: 1488,
  forecast_points: 19856,
};

const forecast = {
  delivery_day: "2026-01-15",
  cutoff: "2026-01-14T09:00:00Z",
  cutoff_hour: 9,
  forecast_runs_used: ["2026-01-14T07:30:00Z"],
  summary: { hours: 2, mean_forecast_mw: 12000, min_forecast_mw: 11000, max_forecast_mw: 13000, total_forecast_mwh: 24000 },
  band: { p10_error_mw: -400, p90_error_mw: 4300, samples: 300 },
  points: [
    { target: "2026-01-15T00:00:00Z", forecast_mw: 11000, published: "2026-01-14T07:30:00Z", horizon_h: 16.5, actual_mw: 9500, error_mw: 1500, low_mw: 6700, high_mw: 11400 },
    { target: "2026-01-15T01:00:00Z", forecast_mw: 13000, published: "2026-01-14T07:30:00Z", horizon_h: 17.5, actual_mw: 11000, error_mw: 2000, low_mw: 8700, high_mw: 13400 },
  ],
};

function mockFetch(routes: Record<string, () => Response>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const path = url.split("?")[0];
      const handler = routes[path];
      return handler ? handler() : new Response(JSON.stringify({ detail: "not found" }), { status: 404 });
    }),
  );
}

const json = (body: unknown, status = 200) => () => new Response(JSON.stringify(body), { status });

afterEach(() => vi.unstubAllGlobals());

describe("App", () => {
  it("shows the decision view with the forecast summary", async () => {
    mockFetch({ "/api/meta": json(meta), "/api/forecast": json(forecast) });
    render(<App />);
    expect(await screen.findByText("Average wind forecast")).toBeInTheDocument();
    expect(screen.getByText("12,000 MW")).toBeInTheDocument();
    expect(screen.getByText("07:30")).toBeInTheDocument();
  });

  it("hides actuals until the user asks to reveal them", async () => {
    mockFetch({ "/api/meta": json(meta), "/api/forecast": json(forecast) });
    render(<App />);
    await screen.findByText("Average wind forecast");
    await userEvent.click(screen.getByText("Hour by hour table"));
    expect(screen.queryByRole("columnheader", { name: "Actual" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByLabelText("Reveal what actually happened"));
    expect(screen.getByRole("columnheader", { name: "Actual" })).toBeInTheDocument();
    expect(screen.getByText("+1,500 MW")).toBeInTheDocument();
  });

  it("surfaces API errors instead of failing silently", async () => {
    mockFetch({ "/api/meta": json(meta), "/api/forecast": json({ detail: "outside the available range" }, 404) });
    render(<App />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("outside the available range"));
  });
});
