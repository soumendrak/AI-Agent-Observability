type EvaluationContext = {
  observation: { input: unknown; output: unknown; metadata?: unknown };
  experiment?: unknown;
};

type EvaluationResult = {
  scores: { name: string; value: boolean; dataType: "BOOLEAN"; comment?: string }[];
};
