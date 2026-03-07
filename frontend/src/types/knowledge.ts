export interface Entity {
  id: string;
  name: string;
  type: string;
  description?: string;
  mention_count: number;
  first_seen: string;
  last_seen: string;
}

export interface Relationship {
  id: string;
  source_id: string;
  target_id: string;
  type: string;
  confidence: number;
}

export interface GraphData {
  nodes: Entity[];
  edges: Relationship[];
}

export interface KnowledgeResult {
  entity: Entity;
  score: number;
}
