import { readFileSync } from "node:fs";
import { join } from "node:path";
import { runInNewContext } from "node:vm";

type ParityCase = { name: string; input: unknown; output: unknown; expect: boolean; comment: string };
type Evaluate = (ctx: EvaluationContext) => EvaluationResult;

const root = join(__dirname, "..", "..", "..");
const evaluate: Evaluate = runInNewContext(
  `${readFileSync(join(root, ".ts-build", "evals", "booking_matches.js"), "utf8")}\nevaluate;`,
  {},
);
const cases: ParityCase[] = JSON.parse(readFileSync(join(root, "tests", "eval_cases.json"), "utf8"));
const failures = cases.filter((c) => {
  const [score] = evaluate({ observation: { input: c.input, output: c.output } }).scores;
  return score.value !== c.expect || score.comment !== c.comment;
});
for (const c of failures) console.log(`TS parity mismatch: ${c.name}`);
console.log(`TS parity: ${cases.length - failures.length}/${cases.length} cases match`);
process.exitCode = failures.length ? 1 : 0;
