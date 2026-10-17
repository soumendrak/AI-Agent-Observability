const FIELDS = ["origin", "destination", "date"] as const;
const IATA = /^[A-Z]{3}$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function obj(value: unknown): Record<string, unknown> {
  if (typeof value === "string") {
    try {
      value = JSON.parse(value);
    } catch {
      return {};
    }
  }
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function clean(record: Record<string, unknown>, field: string): [string | null, string | null] {
  const raw = record[field];
  if (typeof raw !== "string" || raw.trim() === "") return [null, "missing"];
  const value = raw.trim().toUpperCase();
  if (field === "date") {
    if (!ISO_DATE.test(value)) return [null, "invalid"];
    const [y, m, d] = value.split("-").map(Number);
    const dt = new Date(Date.UTC(y, m - 1, d));
    if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) {
      return [null, "invalid"];
    }
  } else if (!IATA.test(value)) {
    return [null, "invalid"];
  }
  return [value, null];
}

function evaluate({ observation: { input, output } }: EvaluationContext): EvaluationResult {
  const sides: Record<string, Record<string, unknown>> = {
    requested: obj(obj(input)["requested"]),
    booking: obj(obj(output)["booking"]),
  };
  const values: Record<string, string | null> = {};
  const problems: string[] = [];
  for (const side of Object.keys(sides)) {
    for (const field of FIELDS) {
      const [value, error] = clean(sides[side], field);
      if (error) problems.push(`${error} field: ${side}.${field}`);
      values[`${side}.${field}`] = value;
    }
  }
  let ok: boolean;
  let comment: string;
  if (problems.length) {
    ok = false;
    comment = problems.join("; ");
  } else {
    const wrong = FIELDS.filter((f) => values[`requested.${f}`] !== values[`booking.${f}`]);
    ok = wrong.length === 0;
    comment = ok
      ? "all fields match"
      : "mismatch: " +
        wrong
          .map((f) => `${f} requested=${values[`requested.${f}`]} booked=${values[`booking.${f}`]}`)
          .join(", ");
  }
  return { scores: [{ name: "booking_matches_request", value: ok, dataType: "BOOLEAN", comment }] };
}
