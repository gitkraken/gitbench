import type { GitBenchData } from "../../lib/types.ts";
import {
  deriveModelGroups,
  sanitizeGroupSelection,
  visibleOutputModes,
  type ConcreteOutputMode,
  type MetricExtractor,
  type OutputMode,
} from "./model-groups.ts";

export interface QuadrantMetricDefinition {
  better: "higher" | "lower";
  extractor: MetricExtractor;
}

export interface QuadrantPoint {
  id: string;
  pairId: string;
  provider: string;
  baseModel: string;
  modelName: string;
  reasoningLevel: string | null;
  outputMode: ConcreteOutputMode;
  x: number;
  y: number;
  xRaw: number;
  yRaw: number;
  xScore: number;
  yScore: number;
  compositeScore: number;
}

export interface QuadrantPointPair {
  id: string;
  provider: string;
  baseModel: string;
  text?: QuadrantPoint;
  json?: QuadrantPoint;
  coincident: boolean;
}

function normalize(
  value: number,
  min: number,
  max: number,
  better: QuadrantMetricDefinition["better"]
) {
  if (max === min) return 0.5;
  const ratio = (value - min) / (max - min);
  return better === "higher" ? ratio : 1 - ratio;
}

export function areQuadrantPointsCoincident(
  text: QuadrantPoint | undefined,
  json: QuadrantPoint | undefined
): boolean {
  return text != null && json != null && text.x === json.x && text.y === json.y;
}

export function pairQuadrantPoints(
  points: QuadrantPoint[]
): QuadrantPointPair[] {
  const pairs = new Map<string, QuadrantPointPair>();
  for (const point of points) {
    const pair = pairs.get(point.pairId) ?? {
      id: point.pairId,
      provider: point.provider,
      baseModel: point.baseModel,
      coincident: false,
    };
    if (point.outputMode === "text") {
      pair.text = point;
    } else {
      pair.json = point;
    }
    pair.coincident = areQuadrantPointsCoincident(pair.text, pair.json);
    pairs.set(point.pairId, pair);
  }
  return Array.from(pairs.values());
}

export function quadrantPairForPoint(
  pairs: QuadrantPointPair[],
  point: Pick<QuadrantPoint, "pairId">
): QuadrantPointPair | undefined {
  return pairs.find((pair) => pair.id === point.pairId);
}

export function rankQuadrantPoints(
  points: QuadrantPoint[],
  limit = 6
): QuadrantPoint[] {
  return [...points]
    .sort(
      (a, b) =>
        b.compositeScore - a.compositeScore ||
        a.pairId.localeCompare(b.pairId) ||
        a.outputMode.localeCompare(b.outputMode)
    )
    .slice(0, limit);
}

export function buildQuadrantPoints(
  data: GitBenchData,
  selectedGroups: string[],
  xMetric: QuadrantMetricDefinition,
  yMetric: QuadrantMetricDefinition,
  outputMode: OutputMode
): QuadrantPoint[] {
  const groups = deriveModelGroups(data);
  const selected = new Set(sanitizeGroupSelection(selectedGroups, groups));
  const visibleModes = new Set(visibleOutputModes(outputMode));
  const candidates = groups
    .filter((group) => selected.has(group.id))
    .flatMap((group) =>
      group.efforts
        .filter((effort) =>
          visibleModes.has(effort.outputMode as ConcreteOutputMode)
        )
        .map((effort) => {
          const x = xMetric.extractor(effort, data);
          const y = yMetric.extractor(effort, data);
          if (!x || !y) return null;
          return {
            pairId: group.id,
            provider: group.provider,
            baseModel: group.baseModel,
            modelName: effort.modelName,
            reasoningLevel: effort.reasoningLevel,
            outputMode: effort.outputMode as ConcreteOutputMode,
            xRaw: x.value,
            yRaw: y.value,
          };
        })
        .filter(
          (
            point
          ): point is Omit<
            QuadrantPoint,
            "id" | "x" | "y" | "xScore" | "yScore" | "compositeScore"
          > => point !== null
        )
    );

  if (candidates.length === 0) return [];

  const xValues = candidates.map((point) => point.xRaw);
  const yValues = candidates.map((point) => point.yRaw);
  const xMin = Math.min(...xValues);
  const xMax = Math.max(...xValues);
  const yMin = Math.min(...yValues);
  const yMax = Math.max(...yValues);
  const bestByPairAndMode = new Map<string, QuadrantPoint>();

  for (const candidate of candidates) {
    const xScore = normalize(candidate.xRaw, xMin, xMax, xMetric.better);
    const yScore = normalize(candidate.yRaw, yMin, yMax, yMetric.better);
    const point: QuadrantPoint = {
      ...candidate,
      id: `${candidate.pairId}::${candidate.outputMode}`,
      x: candidate.xRaw,
      y: candidate.yRaw,
      xScore,
      yScore,
      compositeScore: (xScore + yScore) / 2,
    };
    const selectionKey = point.id;
    const previous = bestByPairAndMode.get(selectionKey);
    if (!previous || point.compositeScore > previous.compositeScore) {
      bestByPairAndMode.set(selectionKey, point);
    }
  }

  return rankQuadrantPoints(Array.from(bestByPairAndMode.values()), Infinity);
}
