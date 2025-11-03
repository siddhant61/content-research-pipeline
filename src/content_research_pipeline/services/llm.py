"""
LLM service for language model interactions using OpenAI.
"""

import asyncio
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from ..config.settings import settings
from ..config.logging import get_logger
from ..config import prompts

logger = get_logger(__name__)


class LLMService:
    """Service for handling language model interactions."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the LLM service.
        
        Args:
            openai_api_key: Optional OpenAI API key to override settings
        """
        self.api_key = openai_api_key or settings.openai_api_key
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.max_tokens,
            api_key=self.api_key
        )
        logger.info(f"LLM service initialized with model: {settings.llm_model}")
    
    async def generate_summary(
        self,
        text: str,
        max_length: int = 500
    ) -> str:
        """
        Generate a summary of the given text.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            
        Returns:
            Summary text
        """
        try:
            logger.info("Generating summary")
            
            # Prepare messages
            system_message = SystemMessage(content=prompts.SUMMARY_SYSTEM_PROMPT)
            
            # Truncate text if too long
            if len(text) > 10000:
                text = text[:10000] + "..."
            
            user_message = HumanMessage(
                content=prompts.SUMMARY_USER_PROMPT_TEMPLATE.format(
                    max_length=max_length,
                    text=text
                )
            )
            
            # Generate summary in thread pool
            response = await asyncio.to_thread(
                self.llm.invoke,
                [system_message, user_message]
            )
            
            summary = response.content.strip()
            logger.info(f"Generated summary of {len(summary)} characters")
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return "Summary generation failed."
    
    async def extract_entities(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """
        Extract named entities from text using LLM.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of entities with their types
        """
        try:
            logger.info("Extracting entities with LLM")
            
            # Prepare messages
            system_message = SystemMessage(content=prompts.ENTITY_EXTRACTION_SYSTEM_PROMPT)
            
            # Truncate text if too long
            if len(text) > 8000:
                text = text[:8000] + "..."
            
            user_message = HumanMessage(
                content=prompts.ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE.format(text=text)
            )
            
            # Extract entities in thread pool
            response = await asyncio.to_thread(
                self.llm.invoke,
                [system_message, user_message]
            )
            
            # Parse response
            entities = []
            lines = response.content.strip().split('\n')
            for line in lines:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        entity_text = parts[0].strip().strip('-').strip('*').strip()
                        entity_type = parts[1].strip().upper()
                        
                        if entity_text:
                            entities.append({
                                'text': entity_text,
                                'label': entity_type,
                                'confidence': 0.8
                            })
            
            logger.info(f"Extracted {len(entities)} entities")
            return entities
            
        except Exception as e:
            logger.error(f"Failed to extract entities: {e}")
            return []
    
    async def analyze_sentiment(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of the text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment analysis results
        """
        try:
            logger.info("Analyzing sentiment")
            
            # Prepare messages
            system_message = SystemMessage(content=prompts.SENTIMENT_ANALYSIS_SYSTEM_PROMPT)
            
            # Truncate text if too long
            if len(text) > 5000:
                text = text[:5000] + "..."
            
            user_message = HumanMessage(
                content=prompts.SENTIMENT_ANALYSIS_USER_PROMPT_TEMPLATE.format(text=text)
            )
            
            # Analyze sentiment in thread pool
            response = await asyncio.to_thread(
                self.llm.invoke,
                [system_message, user_message]
            )
            
            # Parse response
            parts = response.content.strip().split('|')
            if len(parts) >= 3:
                sentiment = parts[0].strip().lower()
                polarity = float(parts[1].strip())
                confidence = float(parts[2].strip())
            else:
                # Default values if parsing fails
                sentiment = "neutral"
                polarity = 0.0
                confidence = 0.5
            
            result = {
                'classification': sentiment,
                'polarity': polarity,
                'confidence': confidence,
                'subjectivity': 0.5  # LLM doesn't provide this, use default
            }
            
            logger.info(f"Sentiment analysis: {sentiment} (polarity: {polarity})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze sentiment: {e}")
            return {
                'classification': 'neutral',
                'polarity': 0.0,
                'confidence': 0.0,
                'subjectivity': 0.5
            }
    
    async def extract_topics(
        self,
        text: str,
        num_topics: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extract main topics from text.
        
        Args:
            text: Text to extract topics from
            num_topics: Number of topics to extract
            
        Returns:
            List of topics with keywords
        """
        try:
            logger.info(f"Extracting {num_topics} topics")
            
            # Prepare messages
            system_message = SystemMessage(content=prompts.TOPIC_EXTRACTION_SYSTEM_PROMPT)
            
            # Truncate text if too long
            if len(text) > 8000:
                text = text[:8000] + "..."
            
            user_message = HumanMessage(
                content=prompts.TOPIC_EXTRACTION_USER_PROMPT_TEMPLATE.format(
                    num_topics=num_topics,
                    text=text
                )
            )
            
            # Extract topics in thread pool
            response = await asyncio.to_thread(
                self.llm.invoke,
                [system_message, user_message]
            )
            
            # Parse response
            topics = []
            lines = response.content.strip().split('\n')
            for i, line in enumerate(lines[:num_topics]):
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        topic_label = parts[0].strip().strip('-').strip('*').strip()
                        keywords = [kw.strip() for kw in parts[1].split(',')]
                        
                        topics.append({
                            'id': i,
                            'label': topic_label,
                            'words': keywords[:5],  # Limit to 5 keywords
                            'weight': 1.0 - (i * 0.15)  # Decreasing weight
                        })
            
            logger.info(f"Extracted {len(topics)} topics")
            return topics
            
        except Exception as e:
            logger.error(f"Failed to extract topics: {e}")
            return []
    
    async def generate_queries(
        self,
        text: str,
        num_queries: int = 5
    ) -> List[str]:
        """
        Generate related search queries based on the text.
        
        Args:
            text: Text to analyze
            num_queries: Number of queries to generate
            
        Returns:
            List of related query strings
        """
        try:
            logger.info(f"Generating {num_queries} related queries")
            
            # Prepare messages
            system_message = SystemMessage(content=prompts.QUERY_GENERATION_SYSTEM_PROMPT)
            
            # Truncate text if too long
            if len(text) > 5000:
                text = text[:5000] + "..."
            
            user_message = HumanMessage(
                content=prompts.QUERY_GENERATION_USER_PROMPT_TEMPLATE.format(
                    num_queries=num_queries,
                    text=text
                )
            )
            
            # Generate queries in thread pool
            response = await asyncio.to_thread(
                self.llm.invoke,
                [system_message, user_message]
            )
            
            # Parse response
            queries = []
            lines = response.content.strip().split('\n')
            for line in lines[:num_queries]:
                query = line.strip().strip('-').strip('*').strip()
                if query and len(query) > 3:
                    queries.append(query)
            
            logger.info(f"Generated {len(queries)} queries")
            return queries
            
        except Exception as e:
            logger.error(f"Failed to generate queries: {e}")
            return []
    
    async def assess_credibility(
        self,
        title: str,
        snippet: str,
        source: str,
        url: str
    ) -> float:
        """
        Assess the credibility of a search result using LLM.
        
        Args:
            title: Title of the search result
            snippet: Description/snippet of the result
            source: Source domain
            url: Full URL of the result
            
        Returns:
            Credibility score between 0.0 and 1.0
        """
        try:
            logger.info(f"Assessing credibility for: {source}")
            
            # Prepare messages
            system_message = SystemMessage(content=prompts.CREDIBILITY_ASSESSMENT_SYSTEM_PROMPT)
            
            user_message = HumanMessage(
                content=prompts.CREDIBILITY_ASSESSMENT_USER_PROMPT_TEMPLATE.format(
                    title=title,
                    snippet=snippet,
                    source=source,
                    url=url
                )
            )
            
            # Get credibility assessment in thread pool
            response = await asyncio.to_thread(
                self.llm.invoke,
                [system_message, user_message]
            )
            
            # Parse response - expecting a float between 0.0 and 1.0
            try:
                score = float(response.content.strip())
                # Ensure score is within valid range
                score = max(0.0, min(1.0, score))
            except ValueError:
                logger.warning(f"Failed to parse credibility score, using default: 0.5")
                score = 0.5
            
            logger.info(f"Credibility score for {source}: {score}")
            return score
            
        except Exception as e:
            logger.error(f"Failed to assess credibility: {e}")
            return 0.5  # Default to neutral credibility on error


# Global LLM service instance
llm_service = LLMService()
