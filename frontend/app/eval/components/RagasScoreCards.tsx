import ScoreBar from "@/components/ui/ScoreBar";
import Card from "@/components/ui/Card";
import type { RagasScores } from "@/lib/types";

export default function RagasScoreCards({ scores }: { scores: RagasScores }) {
  return (
    <Card className="flex flex-col gap-1">
      <h3 className="mb-1 text-sm font-semibold text-text">RAGAS scores</h3>
      <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
        <ScoreBar label="Faithfulness" value={scores.faithfulness} />
        <ScoreBar label="Context precision" value={scores.context_precision} />
        <ScoreBar label="Context recall" value={scores.context_recall} />
        <ScoreBar label="Answer relevancy" value={scores.answer_relevancy} />
      </div>
    </Card>
  );
}
