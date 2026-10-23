import { describeBias, describeRange, fmtMW, fmtPct, fmtSignedMW, fmtClock, shiftDay } from "../format";

describe("format helpers", () => {
  it("formats megawatts with thousands separators", () => {
    expect(fmtMW(12345.6)).toBe("12,346 MW");
    expect(fmtMW(null)).toBe("n/a");
  });

  it("always shows the sign for bias values", () => {
    expect(fmtSignedMW(1851.4)).toBe("+1,851 MW");
    expect(fmtSignedMW(-420)).toBe("-420 MW");
    expect(fmtSignedMW(0.2)).toBe("0 MW");
  });

  it("formats percentages", () => {
    expect(fmtPct(22.17)).toBe("22.2%");
    expect(fmtPct(undefined)).toBe("n/a");
  });

  it("shows UK local clock time", () => {
    expect(fmtClock("2026-01-14T09:30:00Z")).toBe("09:30");
    // British Summer Time is one hour ahead of UTC.
    expect(fmtClock("2026-07-14T08:30:00Z")).toBe("09:30");
  });

  it("describes bias direction in plain words", () => {
    expect(describeBias(1500)).toMatch(/above actual/);
    expect(describeBias(-900)).toMatch(/below actual/);
    expect(describeBias(10)).toMatch(/No consistent/);
  });

  it("moves between days across a month boundary", () => {
    expect(shiftDay("2026-01-31", 1)).toBe("2026-02-01");
    expect(shiftDay("2026-01-01", -1)).toBe("2025-12-31");
  });

  it("describes a range around the forecast in words", () => {
    expect(describeRange(-4306, 426)).toBe("between 4,306 MW below and 426 MW above the forecast");
  });
});
