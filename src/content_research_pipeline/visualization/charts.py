"""
Chart generation and visualization data preparation.
"""

import asyncio
from typing import List, Dict, Any, Optional
import base64
from io import BytesIO

from ..config.logging import get_logger
from ..data.models import (
    AnalysisResult,
    VisualizationData,
    Entity,
    Relationship,
    TimelineEvent,
    Topic
)

logger = get_logger(__name__)


class ChartGenerator:
    """Generator for visualization data structures."""
    
    def __init__(self):
        """Initialize the chart generator."""
        pass
    
    async def generate_visualization_data(
        self,
        analysis: AnalysisResult
    ) -> VisualizationData:
        """
        Generate all visualization data from analysis results.
        
        Args:
            analysis: Analysis result to visualize
            
        Returns:
            VisualizationData with all chart data
        """
        logger.info("Generating visualization data")
        
        try:
            # Generate different visualizations in parallel
            graph_task = asyncio.create_task(
                self._generate_entity_graph(analysis.entities, analysis.relationships)
            )
            timeline_task = asyncio.create_task(
                self._generate_timeline_data(analysis.timeline)
            )
            wordcloud_task = asyncio.create_task(
                self._generate_wordcloud(analysis)
            )
            treemap_task = asyncio.create_task(
                self._generate_topic_treemap(analysis.topics)
            )
            
            # Wait for all generations
            results = await asyncio.gather(
                graph_task,
                timeline_task,
                wordcloud_task,
                treemap_task,
                return_exceptions=True
            )
            
            # Unpack results
            nodes, edges = results[0] if not isinstance(results[0], Exception) else ([], [])
            timeline_dates, timeline_events = results[1] if not isinstance(results[1], Exception) else ([], [])
            wordcloud_data = results[2] if not isinstance(results[2], Exception) else None
            treemap_labels, treemap_parents, treemap_values = results[3] if not isinstance(results[3], Exception) else ([], [], [])
            
            # Create visualization data
            viz_data = VisualizationData(
                nodes=nodes,
                edges=edges,
                timeline_dates=timeline_dates,
                timeline_events=timeline_events,
                word_cloud=wordcloud_data,
                treemap_labels=treemap_labels,
                treemap_parents=treemap_parents,
                treemap_values=treemap_values
            )
            
            logger.info(
                f"Visualization data generated: {len(nodes)} nodes, "
                f"{len(edges)} edges, {len(timeline_dates)} timeline events"
            )
            
            return viz_data
            
        except Exception as e:
            logger.error(f"Failed to generate visualization data: {e}")
            return VisualizationData()
    
    async def _generate_entity_graph(
        self,
        entities: List[Entity],
        relationships: List[Relationship]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generate entity relationship graph data.
        
        Args:
            entities: List of entities
            relationships: List of relationships
            
        Returns:
            Tuple of (nodes, edges)
        """
        logger.info("Generating entity relationship graph")
        
        # Create nodes from entities
        nodes = []
        entity_map = {}
        
        for i, entity in enumerate(entities[:50]):  # Limit to 50 entities
            node = {
                'id': i,
                'label': entity.text,
                'type': entity.label.value,
                'confidence': entity.confidence or 0.5
            }
            nodes.append(node)
            entity_map[entity.text.lower()] = i
        
        # Create edges from relationships
        edges = []
        for relationship in relationships[:100]:  # Limit to 100 relationships
            from_id = entity_map.get(relationship.from_entity.lower())
            to_id = entity_map.get(relationship.to_entity.lower())
            
            if from_id is not None and to_id is not None:
                edge = {
                    'from': from_id,
                    'to': to_id,
                    'type': relationship.relationship_type,
                    'confidence': relationship.confidence or 0.5
                }
                edges.append(edge)
        
        logger.info(f"Generated {len(nodes)} nodes and {len(edges)} edges")
        return nodes, edges
    
    async def _generate_timeline_data(
        self,
        timeline: List[TimelineEvent]
    ) -> tuple[List[str], List[str]]:
        """
        Generate timeline data.
        
        Args:
            timeline: List of timeline events
            
        Returns:
            Tuple of (dates, events)
        """
        logger.info("Generating timeline data")
        
        dates = []
        events = []
        
        # Sort timeline by date (simple sort by string)
        sorted_timeline = sorted(timeline, key=lambda x: x.date)
        
        for event in sorted_timeline[:20]:  # Limit to 20 events
            dates.append(event.date)
            events.append(event.event)
        
        logger.info(f"Generated timeline with {len(dates)} events")
        return dates, events
    
    async def _generate_wordcloud(
        self,
        analysis: AnalysisResult
    ) -> Optional[str]:
        """
        Generate word cloud from analysis.
        
        Args:
            analysis: Analysis result
            
        Returns:
            Base64 encoded word cloud image or None
        """
        try:
            logger.info("Generating word cloud")
            
            # Import wordcloud in thread pool
            from wordcloud import WordCloud
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            
            # Combine text from summary and topics
            text_parts = [analysis.summary]
            for topic in analysis.topics:
                text_parts.extend(topic.words)
            
            text = " ".join(text_parts)
            
            if not text or len(text) < 10:
                logger.warning("Insufficient text for word cloud")
                return None
            
            # Generate word cloud in thread pool
            def _generate():
                wordcloud = WordCloud(
                    width=800,
                    height=400,
                    background_color='white',
                    colormap='viridis',
                    max_words=100
                ).generate(text)
                
                # Create figure
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis('off')
                
                # Save to bytes
                buffer = BytesIO()
                plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
                plt.close(fig)
                buffer.seek(0)
                
                # Encode to base64
                image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
                return f"data:image/png;base64,{image_base64}"
            
            wordcloud_data = await asyncio.to_thread(_generate)
            logger.info("Word cloud generated successfully")
            return wordcloud_data
            
        except Exception as e:
            logger.warning(f"Failed to generate word cloud: {e}")
            return None
    
    async def _generate_topic_treemap(
        self,
        topics: List[Topic]
    ) -> tuple[List[str], List[str], List[float]]:
        """
        Generate treemap data for topics.
        
        Args:
            topics: List of topics
            
        Returns:
            Tuple of (labels, parents, values)
        """
        logger.info("Generating topic treemap")
        
        labels = ["Topics"]  # Root node
        parents = [""]
        values = [0.0]
        
        for topic in topics:
            # Add topic node
            labels.append(topic.label)
            parents.append("Topics")
            values.append(topic.weight)
            
            # Add keyword nodes
            for word in topic.words[:3]:  # Limit to 3 keywords per topic
                labels.append(word)
                parents.append(topic.label)
                values.append(topic.weight / len(topic.words))
        
        logger.info(f"Generated treemap with {len(labels)} nodes")
        return labels, parents, values


# Global chart generator instance
chart_generator = ChartGenerator()
