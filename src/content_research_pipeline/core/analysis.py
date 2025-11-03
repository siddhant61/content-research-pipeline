"""
Core analysis module for content analysis using NLP and LLM.
"""

import asyncio
from typing import List, Optional
from datetime import datetime
import re

from ..config.settings import settings
from ..config.logging import get_logger
from ..data.models import (
    ScrapedContent,
    AnalysisResult,
    Entity,
    EntityType,
    SentimentAnalysis,
    Topic,
    TimelineEvent,
    RelatedQuery,
    Relationship
)
from ..services.llm import llm_service

logger = get_logger(__name__)


class AnalysisProcessor:
    """Processor for analyzing scraped content."""
    
    def __init__(self):
        """Initialize the analysis processor."""
        self.spacy_nlp = None
        self._load_spacy_model()
    
    def _load_spacy_model(self):
        """Load spaCy model for NLP processing."""
        try:
            import spacy
            self.spacy_nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {e}")
            self.spacy_nlp = None
    
    async def analyze(
        self,
        query: str,
        scraped_contents: List[ScrapedContent]
    ) -> AnalysisResult:
        """
        Perform comprehensive analysis on scraped content.
        
        Args:
            query: Original search query
            scraped_contents: List of scraped content to analyze
            
        Returns:
            AnalysisResult with all analysis data
        """
        logger.info(f"Starting analysis for query: {query}")
        
        try:
            # Combine all text content
            combined_text = self._combine_texts(scraped_contents)
            
            if not combined_text or len(combined_text.strip()) < 100:
                logger.warning("Insufficient text content for analysis")
                return self._create_empty_result(query)
            
            # Run analyses in parallel
            summary_task = asyncio.create_task(
                llm_service.generate_summary(combined_text)
            )
            entities_task = asyncio.create_task(
                self._extract_entities(combined_text)
            )
            sentiment_task = asyncio.create_task(
                self._analyze_sentiment(combined_text)
            )
            topics_task = asyncio.create_task(
                self._extract_topics(combined_text)
            )
            timeline_task = asyncio.create_task(
                self._extract_timeline(combined_text, scraped_contents)
            )
            queries_task = asyncio.create_task(
                self._generate_related_queries(combined_text, scraped_contents)
            )
            
            # Wait for all analyses to complete
            results = await asyncio.gather(
                summary_task,
                entities_task,
                sentiment_task,
                topics_task,
                timeline_task,
                queries_task,
                return_exceptions=True
            )
            
            # Unpack results with error handling
            summary = results[0] if not isinstance(results[0], Exception) else "Analysis summary unavailable."
            entities = results[1] if not isinstance(results[1], Exception) else []
            sentiment_dict = results[2] if not isinstance(results[2], Exception) else {}
            topics = results[3] if not isinstance(results[3], Exception) else []
            timeline = results[4] if not isinstance(results[4], Exception) else []
            related_queries = results[5] if not isinstance(results[5], Exception) else []
            
            # Create sentiment analysis object
            sentiment = SentimentAnalysis(
                polarity=sentiment_dict.get('polarity', 0.0),
                subjectivity=sentiment_dict.get('subjectivity', 0.5),
                classification=sentiment_dict.get('classification', 'neutral'),
                confidence=sentiment_dict.get('confidence', 0.5)
            )
            
            # Extract relationships between entities
            relationships = self._extract_relationships(entities, combined_text)
            
            # Create and return result
            result = AnalysisResult(
                query=query,
                summary=summary,
                entities=entities,
                relationships=relationships,
                topics=topics,
                sentiment=sentiment,
                timeline=timeline,
                related_queries=related_queries,
                analyzed_at=datetime.now()
            )
            
            logger.info(
                f"Analysis completed: {len(entities)} entities, "
                f"{len(topics)} topics, {len(timeline)} timeline events"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return self._create_empty_result(query)
    
    def _combine_texts(self, scraped_contents: List[ScrapedContent]) -> str:
        """
        Combine text from all scraped contents.
        
        Args:
            scraped_contents: List of scraped content
            
        Returns:
            Combined text string
        """
        texts = []
        for content in scraped_contents:
            if content.text_content and len(content.text_content.strip()) > 50:
                texts.append(content.text_content)
        
        combined = "\n\n".join(texts)
        
        # Limit total text length
        max_length = 50000
        if len(combined) > max_length:
            combined = combined[:max_length]
        
        return combined
    
    async def _extract_entities(self, text: str) -> List[Entity]:
        """
        Extract entities using both spaCy and LLM.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of Entity objects
        """
        entities_dict = {}
        
        # Extract using LLM
        llm_entities = await llm_service.extract_entities(text)
        for ent in llm_entities:
            key = (ent['text'].lower(), ent['label'])
            if key not in entities_dict:
                try:
                    entity_type = EntityType[ent['label']] if ent['label'] in EntityType.__members__ else EntityType.PERSON
                    entities_dict[key] = Entity(
                        text=ent['text'],
                        label=entity_type,
                        confidence=ent.get('confidence', 0.8)
                    )
                except:
                    pass
        
        # Extract using spaCy if available
        if self.spacy_nlp:
            try:
                doc = self.spacy_nlp(text[:10000])  # Limit text for spaCy
                for ent in doc.ents:
                    key = (ent.text.lower(), ent.label_)
                    if key not in entities_dict:
                        try:
                            entity_type = EntityType[ent.label_] if ent.label_ in EntityType.__members__ else EntityType.PERSON
                            entities_dict[key] = Entity(
                                text=ent.text,
                                label=entity_type,
                                confidence=0.9,
                                start=ent.start_char,
                                end=ent.end_char
                            )
                        except:
                            pass
            except Exception as e:
                logger.warning(f"spaCy entity extraction failed: {e}")
        
        # Return unique entities
        return list(entities_dict.values())
    
    async def _analyze_sentiment(self, text: str) -> dict:
        """
        Analyze sentiment using TextBlob and LLM.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment metrics
        """
        # Use LLM for sentiment analysis
        llm_sentiment = await llm_service.analyze_sentiment(text)
        
        # Try TextBlob as well
        try:
            from textblob import TextBlob
            blob = TextBlob(text[:5000])
            
            # Combine both analyses
            sentiment = {
                'polarity': (llm_sentiment['polarity'] + blob.sentiment.polarity) / 2,
                'subjectivity': blob.sentiment.subjectivity,
                'confidence': llm_sentiment['confidence'],
                'classification': llm_sentiment['classification']
            }
        except Exception as e:
            logger.warning(f"TextBlob sentiment analysis failed: {e}")
            sentiment = llm_sentiment
        
        return sentiment
    
    async def _extract_topics(self, text: str) -> List[Topic]:
        """
        Extract topics using LLM.
        
        Args:
            text: Text to extract topics from
            
        Returns:
            List of Topic objects
        """
        llm_topics = await llm_service.extract_topics(
            text,
            num_topics=settings.max_topics
        )
        
        topics = []
        for topic_data in llm_topics:
            try:
                topic = Topic(
                    id=topic_data['id'],
                    label=topic_data['label'],
                    words=topic_data['words'],
                    weight=topic_data['weight']
                )
                topics.append(topic)
            except Exception as e:
                logger.warning(f"Failed to create topic: {e}")
        
        return topics
    
    async def _extract_timeline(
        self,
        text: str,
        scraped_contents: List[ScrapedContent]
    ) -> List[TimelineEvent]:
        """
        Extract timeline events from text.
        
        Args:
            text: Text to extract events from
            scraped_contents: Original scraped contents for sources
            
        Returns:
            List of TimelineEvent objects
        """
        timeline_events = []
        
        # Use regex to find date patterns
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b'
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                date_str = match.group()
                # Get context around the date
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()
                
                # Create timeline event
                event = TimelineEvent(
                    date=date_str,
                    event=context[:200],  # Limit event description
                    source=scraped_contents[0].url if scraped_contents else "Unknown",
                    confidence=0.6
                )
                timeline_events.append(event)
                
                # Limit number of events
                if len(timeline_events) >= 10:
                    break
            
            if len(timeline_events) >= 10:
                break
        
        return timeline_events
    
    async def _generate_related_queries(
        self,
        text: str,
        scraped_contents: List[ScrapedContent]
    ) -> List[RelatedQuery]:
        """
        Generate related queries using LLM.
        
        Args:
            text: Text to base queries on
            scraped_contents: Original scraped contents
            
        Returns:
            List of RelatedQuery objects
        """
        query_strings = await llm_service.generate_queries(text, num_queries=5)
        
        related_queries = []
        for query_str in query_strings:
            try:
                # Use first scraped content URL as source
                source = scraped_contents[0].url if scraped_contents else "http://example.com"
                
                related_query = RelatedQuery(
                    query=query_str,
                    source=source,
                    relevance=0.8
                )
                related_queries.append(related_query)
            except Exception as e:
                logger.warning(f"Failed to create related query: {e}")
        
        return related_queries
    
    def _extract_relationships(
        self,
        entities: List[Entity],
        text: str
    ) -> List[Relationship]:
        """
        Extract relationships between entities.
        
        Args:
            entities: List of extracted entities
            text: Original text
            
        Returns:
            List of Relationship objects
        """
        relationships = []
        
        # Simple co-occurrence based relationships
        entity_texts = [e.text.lower() for e in entities]
        
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Check if entities co-occur in text
                pattern = rf'\b{re.escape(entity1.text)}\b.*?\b{re.escape(entity2.text)}\b'
                if re.search(pattern, text, re.IGNORECASE):
                    relationship = Relationship(
                        from_entity=entity1.text,
                        to_entity=entity2.text,
                        relationship_type="related_to",
                        confidence=0.7
                    )
                    relationships.append(relationship)
                    
                    # Limit relationships
                    if len(relationships) >= 20:
                        return relationships
        
        return relationships
    
    def _create_empty_result(self, query: str) -> AnalysisResult:
        """
        Create an empty analysis result for error cases.
        
        Args:
            query: Original query
            
        Returns:
            Empty AnalysisResult
        """
        return AnalysisResult(
            query=query,
            summary="Analysis could not be completed due to insufficient data.",
            entities=[],
            relationships=[],
            topics=[],
            sentiment=SentimentAnalysis(
                polarity=0.0,
                subjectivity=0.5,
                classification="neutral",
                confidence=0.0
            ),
            timeline=[],
            related_queries=[],
            analyzed_at=datetime.now()
        )


# Global analysis processor instance
analysis_processor = AnalysisProcessor()
