import type { FilingStage } from "@/lib/types";

/** Maps a filing stage to the Badge component's tone palette (§4 design tokens). */
export function stageTone(stage: FilingStage): "verified" | "pending" | "neutral" {
  if (stage === "filed" || stage === "completed") return "verified";
  return "pending";
}
