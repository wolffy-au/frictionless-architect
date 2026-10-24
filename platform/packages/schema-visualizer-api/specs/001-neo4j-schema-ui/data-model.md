# Data Model for Neo4j Schema Visualiser

## ModelDefinition
- **Description:** Represents the ArchiMate model defined by each schema file pair (archimate3_Model.xsd, archimate3_View.xsd, etc.). The visualiser treats this as the top-level container for elements, relationships, diagrams, and views.  
- **Fields:** `identifier` (string, matches schema `name`), `name` (display-friendly), `namespace` (XSD target namespace), `schema_files` (list of filenames), `sample_source` (path, e.g., `sample-data/sample-00/Test Model Full.xml`), `loaded_at` (ISO timestamp).  
- **Validation:** Must match the ArchiMate XSD `model` definition and include at least one schema file reference.

## ElementType
- **Description:** Schema-defined node type (e.g., ValueStream).  
- **Fields:** `identifier` (schema ID), `type` (ArchiMate element category), `label`, `documentation` (optional), `allowed_properties` (map of property name → type), `source_file` (XSD filename), `sample_instances` (list of SampleElement IDs).  
- **Relationships:** `ElementType` may have `HAS_SAMPLE` links to `SampleElement` entries; used to compute coverage and highlight missing samples.

## RelationshipType
- **Description:** Schema-defined relationship (e.g., Association).  
- **Fields:** `identifier`, `directionality` (enum: `directed`/`undirected`), `source_restriction`, `target_restriction`, `documentation`, `source_file`, `sample_instances` (list of SampleRelationship IDs).  
- **Validation:** Relationship is flagged if no sample instance exists or if a sample violates restrictions.

## SampleElement
- **Description:** Concrete node extracted from `Test Model Full.xml` used to illustrate how a schema element behaves.  
- **Fields:** `identifier`, `name`, `element_type_id`, `properties` (map), `diagram_node` (reference to DiagramNode), `source_node_id` (Neo4j element identifier if ingested), `sample_file_position` (optional location info).  
- **Transition:** Moves from `pending` (sample source not loaded) to `verified` (confirmed in Neo4j) to ensure warnings surface when coverage gaps exist.

## SampleRelationship
- **Description:** Concrete relationship from the sample file with `source`, `target`, and schema relationship type metadata.  
- **Fields:** `identifier`, `relationship_type_id`, `source_element_id`, `target_element_id`, `labels`, `sample_file_position`.  
- **Validation:** Relationship must only render if both `source_element_id` and `target_element_id` exist; otherwise mark with warning color in the diagram view.

## ViewDiagram
- **Description:** Contains layout metadata (x/y/width/height) derived from `archimate3_View.xsd` and used to sketch the diagram preview.  
- **Fields:** `identifier`, `name`, `viewpoint`, `diagram_nodes` (list of DiagramNode), `connections` (list of DiagramConnection), `source_file`.  

## DiagramNode
- **Fields:** `element_id`, `bounds` (`x`, `y`, `width`, `height`), `style` map (colors, fonts), `sequence`.  
- **Relationships:** Links back to `SampleElement` and is rendered both in the cytoscape view and tabular overlay for cross-platform consistency.

## VisualiserPayload
- **Description:** Aggregated JSON contract served to the front-end.  
- **Fields:** `model` (ModelDefinition), `elements` (list of ElementType + summary of sample coverage), `relationships`, `views` (ViewDiagram), `warnings` (list of strings describing missing sample data or Neo4j connectivity issues), `latency_ms` (timing data for performance tracking).  
- **Usage:** Shared between the diagram and table views so both render the same dataset, satisfying Principle IX.
