import { useState, useEffect, useRef } from 'react';
import type { GitBenchData, ModelInfo } from '@/lib/types';
import { loadData } from '@/lib/load-data';
import { Badge } from '@/components/ui/badge';
import { MultiSelect } from '@/components/ui/multi-select';
import ProviderIcon from '@/components/ProviderIcon';

interface ModelSelectorProps {
  initialSelected?: string[];
  onChange?: (selected: string[]) => void;
}

function getPassColor(passRate: number): string {
  if (passRate >= 0.8) return 'text-[var(--color-pass)]';
  if (passRate >= 0.5) return 'text-[var(--color-warn)]';
  return 'text-[var(--color-fail)]';
}

export default function ModelSelector({ initialSelected, onChange }: ModelSelectorProps) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const dataRef = useRef<GitBenchData | null>(null);

  useEffect(() => {
    loadData().then(data => {
      dataRef.current = data;
      setModels(data.models);
      if (!initialSelected || initialSelected.length === 0) {
        setSelected(data.models.map(m => m.name));
      }
    });
  }, []);

  useEffect(() => {
    if (initialSelected && initialSelected.length > 0) {
      setSelected(initialSelected);
    }
  }, [initialSelected?.join(',')]);

  // Listen for external selection changes from other ModelSelector instances
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as string[];
      if (Array.isArray(detail)) {
        setSelected(detail);
      }
    };
    window.addEventListener('model-selection-changed', handler);
    return () => window.removeEventListener('model-selection-changed', handler);
  }, []);

  const options = models.map(m => ({
    value: m.name,
    label: m.name,
  }));

  return (
    <MultiSelect
      options={options}
      value={selected}
      onChange={(vals) => {
        setSelected(vals);
        localStorage.setItem('gitbench-model-selection', JSON.stringify(vals));
        window.dispatchEvent(new CustomEvent('model-selection-changed', { detail: vals }));
        onChange?.(vals);
      }}
      placeholder="Select models..."
      searchPlaceholder="Search models..."
      emptyMessage="No models found."
      renderItemStart={(option) => {
        const modelInfo = dataRef.current?.models.find(m => m.name === option.value);
        if (!modelInfo) return null;
        return (
          <span className="inline-flex mr-1.5 align-middle">
            <ProviderIcon provider={modelInfo.provider} size={14} />
          </span>
        );
      }}
      renderItemEnd={(option) => {
        const summary = dataRef.current?.model_summaries[option.value];
        const passRate = summary ? Math.round(summary.pass_at_k * 1000) / 10 : 0;
        return (
          <Badge
            variant="outline"
            className={`font-mono text-[0.6rem] shrink-0 ${getPassColor(dataRef.current?.model_summaries[option.value]?.pass_at_k ?? 0)}`}
          >
            {passRate}%
          </Badge>
        );
      }}
    />
  );
}
