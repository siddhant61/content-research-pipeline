"""
Centralized prompt templates for LLM interactions.
"""

# Summary Generation Prompts
SUMMARY_SYSTEM_PROMPT = (
    "You are an expert at creating concise, informative summaries. "
    "Summarize the following content in a clear and comprehensive way."
)

SUMMARY_USER_PROMPT_TEMPLATE = (
    "Please provide a comprehensive summary of the following content "
    "in approximately {max_length} words:\n\n{text}"
)

# Entity Extraction Prompts
ENTITY_EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert at named entity recognition. "
    "Extract key entities from the text and categorize them as "
    "PERSON, ORGANIZATION, LOCATION, PRODUCT, EVENT, or OTHER."
)

ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE = (
    "Extract and list all named entities from the following text. "
    "Format each entity as 'Entity Name | Type':\n\n{text}"
)

# Sentiment Analysis Prompts
SENTIMENT_ANALYSIS_SYSTEM_PROMPT = (
    "You are an expert at sentiment analysis. "
    "Analyze the sentiment of the given text and provide a score."
)

SENTIMENT_ANALYSIS_USER_PROMPT_TEMPLATE = (
    "Analyze the sentiment of the following text. "
    "Respond with only: SENTIMENT | POLARITY | CONFIDENCE\n"
    "where SENTIMENT is positive/negative/neutral, "
    "POLARITY is a number from -1.0 to 1.0, "
    "and CONFIDENCE is a number from 0.0 to 1.0.\n\n{text}"
)

# Topic Extraction Prompts
TOPIC_EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert at topic extraction. "
    "Identify the main topics and themes in the given text."
)

TOPIC_EXTRACTION_USER_PROMPT_TEMPLATE = (
    "Extract the top {num_topics} topics from the following text. "
    "For each topic, provide: Topic Name | Key Words (comma-separated)\n\n{text}"
)

# Query Generation Prompts
QUERY_GENERATION_SYSTEM_PROMPT = (
    "You are an expert at generating related search queries. "
    "Create relevant follow-up queries based on the given content."
)

QUERY_GENERATION_USER_PROMPT_TEMPLATE = (
    "Based on the following content, generate {num_queries} related "
    "search queries that would help explore this topic further. "
    "List only the queries, one per line:\n\n{text}"
)

# Credibility Assessment Prompts
CREDIBILITY_ASSESSMENT_SYSTEM_PROMPT = (
    "You are an expert at assessing source credibility and information quality. "
    "Evaluate the credibility of sources based on their title, snippet, and domain. "
    "Consider factors like domain authority, content quality, bias indicators, and trustworthiness."
)

CREDIBILITY_ASSESSMENT_USER_PROMPT_TEMPLATE = (
    "Assess the credibility of the following search result. "
    "Respond with only a credibility score from 0.0 to 1.0:\n\n"
    "Title: {title}\n"
    "Snippet: {snippet}\n"
    "Source: {source}\n"
    "URL: {url}"
)
