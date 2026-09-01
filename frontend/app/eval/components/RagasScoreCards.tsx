import ScoreBar from "@/components/ui/ScoreBar";
import type { RagasScores } from "@/lib/types";

export default function RagasScoreCards({ scores }: { scores: RagasScores }) {
  return (
    <div className="grid grid-cols-1 gap-4 rounded-lg border border-zinc-200 bg-white p-4 sm:grid-cols-2">
      <ScoreBar label="Faithfulness" value={scores.faithfulness} />
      <ScoreBar label="Context precision" value={scores.context_precision} />
      <ScoreBar label="Context recall" value={scores.context_recall} />
      <ScoreBar label="Answer relevancy" value={scores.answer_relevancy} />
    </div>
  );
}
