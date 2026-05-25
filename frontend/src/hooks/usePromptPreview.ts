import { createResource } from "solid-js";
import { fetchPromptPreview } from "~/lib/promptPreview";
import type { ClassificationResult } from "~/types/classifier";

type PreviewInput = {
  metadata: ClassificationResult["metadata"];
  headConfidences: ClassificationResult["headConfidences"];
};

export function usePromptPreview(getResult: () => ClassificationResult | null | undefined) {
  const [systemPrompt, { refetch, mutate }] = createResource(
    () => {
      const result = getResult();
      if (!result) {
        return null;
      }
      const input: PreviewInput = {
        metadata: result.metadata,
        headConfidences: result.headConfidences,
      };
      return input;
    },
    async (input) => {
      if (!input) {
        return null;
      }
      return fetchPromptPreview(input.metadata, input.headConfidences);
    },
  );

  return { systemPrompt, refetch, mutate };
}
