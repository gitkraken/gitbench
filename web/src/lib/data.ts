import fs from "node:fs";
import path from "node:path";
import type { GitBenchData } from "@/lib/types";

let _cache: GitBenchData | null = null;

export function loadDataSync(): GitBenchData {
  if (_cache) return _cache;
  const filePath = path.resolve(process.cwd(), "public/results.json");
  const raw = fs.readFileSync(filePath, "utf-8");
  _cache = JSON.parse(raw);
  return _cache!;
}
