import type { GitBenchData } from "@/lib/types";
import ModelSelector from "@/components/charts/ModelSelector";
import OutputModeSelector from "@/components/charts/OutputModeSelector";
import type { OutputMode } from "@/components/charts/model-groups";

interface ModelOutputControlsProps {
  data: GitBenchData;
  selectedGroups: string[];
  onSelectedGroupsChange: (groups: string[]) => void;
  outputMode: OutputMode;
  onOutputModeChange: (mode: OutputMode) => void;
  availableOutputModes: Set<string>;
}

export default function ModelOutputControls({
  data,
  selectedGroups,
  onSelectedGroupsChange,
  outputMode,
  onOutputModeChange,
  availableOutputModes,
}: ModelOutputControlsProps) {
  return (
    <div className="mb-3 grid gap-3 lg:grid-cols-[2fr_minmax(16rem,24rem)]">
      <div />
      <div className="min-w-0 flex items-center gap-3">
        <div className="flex-1">
          <ModelSelector
            data={data}
            value={selectedGroups}
            onChange={onSelectedGroupsChange}
          />
        </div>
        <OutputModeSelector
          value={outputMode}
          onChange={onOutputModeChange}
          availableModes={availableOutputModes}
        />
      </div>
    </div>
  );
}
