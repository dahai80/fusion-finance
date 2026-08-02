from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EntityNode:
    id: str = ""
    name: str = ""
    entity_type: str = ""
    country: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityRelation:
    source_id: str = ""
    target_id: str = ""
    relation_type: str = ""
    weight: float = 1.0
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityGraph:
    nodes: dict[str, EntityNode] = field(default_factory=dict)
    edges: list[EntityRelation] = field(default_factory=list)

    def add_node(self, node: EntityNode) -> None:
        self.nodes[node.id] = node
        logger.debug("Added node: %s (%s)", node.id, node.name)

    def add_relation(self, relation: EntityRelation) -> None:
        self.edges.append(relation)
        logger.debug("Added relation: %s --%s--> %s", relation.source_id, relation.relation_type, relation.target_id)

    def get_node(self, node_id: str) -> EntityNode | None:
        return self.nodes.get(node_id)

    def get_relations(self, node_id: str) -> list[EntityRelation]:
        return [e for e in self.edges if e.source_id == node_id or e.target_id == node_id]

    def get_children(self, node_id: str) -> list[EntityNode]:
        child_ids = [e.target_id for e in self.edges if e.source_id == node_id]
        return [self.nodes[cid] for cid in child_ids if cid in self.nodes]

    def get_parents(self, node_id: str) -> list[EntityNode]:
        parent_ids = [e.source_id for e in self.edges if e.target_id == node_id]
        return [self.nodes[pid] for pid in parent_ids if pid in self.nodes]

    def to_dict(self) -> dict:
        return {
            "nodes": {
                k: {"id": v.id, "name": v.name, "type": v.entity_type, "country": v.country}
                for k, v in self.nodes.items()
            },
            "edges": [
                {"source": e.source_id, "target": e.target_id, "type": e.relation_type, "weight": e.weight}
                for e in self.edges
            ],
            "summary": {"node_count": len(self.nodes), "edge_count": len(self.edges)},
        }


class EntityResolver:
    def resolve_ubo(self, graph: EntityGraph, entity_id: str, threshold: float = 0.25) -> list[dict]:
        ubos = []
        visited = set()
        self._trace_ownership(graph, entity_id, 1.0, ubos, visited, threshold)
        ubos.sort(key=lambda x: x["ownership_pct"], reverse=True)
        logger.info("UBO resolution for %s: found %d UBOs", entity_id, len(ubos))
        return ubos

    def _trace_ownership(
        self,
        graph: EntityGraph,
        node_id: str,
        cum_weight: float,
        results: list[dict],
        visited: set[str],
        threshold: float,
    ) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        parents = graph.get_parents(node_id)
        if not parents:
            ownership_pct = cum_weight * 100
            if ownership_pct >= threshold * 100:
                node = graph.get_node(node_id)
                results.append(
                    {
                        "entity_id": node_id,
                        "name": node.name if node else node_id,
                        "type": node.entity_type if node else "",
                        "ownership_pct": round(ownership_pct, 2),
                        "is_ubo": True,
                    }
                )
            return
        for parent in parents:
            rels = [e for e in graph.edges if e.source_id == parent.id and e.target_id == node_id]
            weight = rels[0].weight if rels else 1.0
            self._trace_ownership(graph, parent.id, cum_weight * weight, results, visited, threshold)

    def find_pep_connections(self, graph: EntityGraph, pep_types: list[str] | None = None) -> list[dict]:
        pep_types = pep_types or ["politician", "government_official", "pep"]
        connections = []
        for edge in graph.edges:
            target = graph.get_node(edge.target_id)
            source = graph.get_node(edge.source_id)
            if target and target.entity_type.lower() in pep_types:
                connections.append(
                    {
                        "pep_id": target.id,
                        "pep_name": target.name,
                        "connected_entity": source.name if source else edge.source_id,
                        "relation": edge.relation_type,
                        "weight": edge.weight,
                    }
                )
            if source and source.entity_type.lower() in pep_types:
                connections.append(
                    {
                        "pep_id": source.id,
                        "pep_name": source.name,
                        "connected_entity": target.name if target else edge.target_id,
                        "relation": edge.relation_type,
                        "weight": edge.weight,
                    }
                )
        logger.info("PEP scan: found %d connections", len(connections))
        return connections

    def build_from_structure(self, structure: dict) -> EntityGraph:
        graph = EntityGraph()
        for node_data in structure.get("nodes", []):
            node = EntityNode(
                id=node_data.get("id", ""),
                name=node_data.get("name", ""),
                entity_type=node_data.get("type", "company"),
                country=node_data.get("country", ""),
                attributes=node_data.get("attributes", {}),
            )
            graph.add_node(node)
        for edge_data in structure.get("edges", []):
            rel = EntityRelation(
                source_id=edge_data.get("source", ""),
                target_id=edge_data.get("target", ""),
                relation_type=edge_data.get("type", "ownership"),
                weight=edge_data.get("weight", 1.0),
                attributes=edge_data.get("attributes", {}),
            )
            graph.add_relation(rel)
        logger.info("Built graph from structure: %d nodes, %d edges", len(graph.nodes), len(graph.edges))
        return graph
