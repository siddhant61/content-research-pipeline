"""
HTML report generation using Jinja2 templates.
"""

import asyncio
from typing import Optional
from datetime import datetime
from jinja2 import Template

from ..config.logging import get_logger
from ..data.models import PipelineState, VisualizationData

logger = get_logger(__name__)


class ReportGenerator:
    """Generator for HTML reports."""
    
    def __init__(self):
        """Initialize the report generator."""
        self.template = self._get_template()
    
    def _get_template(self) -> Template:
        """
        Get the Jinja2 template for the HTML report.
        
        Returns:
            Jinja2 Template object
        """
        template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Research Report: {{ state.query }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }
        
        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        
        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
            font-size: 1.8em;
        }
        
        h3 {
            color: #555;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 1.3em;
        }
        
        .header {
            border-bottom: 3px solid #3498db;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .meta-info {
            display: flex;
            gap: 30px;
            margin-top: 15px;
            color: #666;
            font-size: 0.95em;
        }
        
        .meta-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .summary {
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
            border-left: 4px solid #3498db;
        }
        
        .section {
            margin: 30px 0;
        }
        
        .entity-list, .topic-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }
        
        .entity-badge, .topic-badge {
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            display: inline-block;
        }
        
        .entity-badge {
            background-color: #3498db;
            color: white;
        }
        
        .topic-badge {
            background-color: #2ecc71;
            color: white;
        }
        
        .sentiment {
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
        }
        
        .sentiment.positive {
            background-color: #d5f4e6;
            border-left: 4px solid #27ae60;
        }
        
        .sentiment.negative {
            background-color: #fadbd8;
            border-left: 4px solid #e74c3c;
        }
        
        .sentiment.neutral {
            background-color: #e8f4f8;
            border-left: 4px solid #3498db;
        }
        
        .timeline {
            margin-top: 20px;
        }
        
        .timeline-item {
            padding: 15px;
            margin: 10px 0;
            background-color: #f8f9fa;
            border-left: 3px solid #3498db;
            border-radius: 4px;
        }
        
        .timeline-date {
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }
        
        .related-queries {
            list-style: none;
            margin-top: 15px;
        }
        
        .related-queries li {
            padding: 10px;
            margin: 8px 0;
            background-color: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #9b59b6;
        }
        
        .graph-container, .wordcloud-container {
            margin: 20px 0;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 6px;
            text-align: center;
        }
        
        .wordcloud-img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .stat-card {
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 6px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }
        
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Content Research Report</h1>
            <h2 style="border: none; margin-top: 10px; color: #7f8c8d;">{{ state.query }}</h2>
            <div class="meta-info">
                <div class="meta-item">
                    <strong>Date:</strong> {{ state.created_at.strftime('%Y-%m-%d %H:%M') }}
                </div>
                <div class="meta-item">
                    <strong>Status:</strong> {{ state.status }}
                </div>
                {% if processing_time %}
                <div class="meta-item">
                    <strong>Processing Time:</strong> {{ "%.2f"|format(processing_time) }}s
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- Statistics -->
        <div class="section">
            <h2>Overview</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{{ state.search_results|length }}</div>
                    <div class="stat-label">Search Results</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ state.scraped_content|length }}</div>
                    <div class="stat-label">Pages Analyzed</div>
                </div>
                {% if state.analysis %}
                <div class="stat-card">
                    <div class="stat-number">{{ state.analysis.entities|length }}</div>
                    <div class="stat-label">Entities Found</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ state.analysis.topics|length }}</div>
                    <div class="stat-label">Topics Identified</div>
                </div>
                {% endif %}
            </div>
        </div>
        
        {% if state.analysis %}
        <!-- Summary -->
        <div class="section">
            <h2>Executive Summary</h2>
            <div class="summary">
                {{ state.analysis.summary }}
            </div>
        </div>
        
        <!-- Sentiment Analysis -->
        <div class="section">
            <h2>Sentiment Analysis</h2>
            <div class="sentiment {{ state.analysis.sentiment.classification }}">
                <strong>Overall Sentiment:</strong> {{ state.analysis.sentiment.classification.title() }}
                <br>
                <strong>Polarity:</strong> {{ "%.2f"|format(state.analysis.sentiment.polarity) }}
                <br>
                <strong>Confidence:</strong> {{ "%.0f"|format(state.analysis.sentiment.confidence * 100) }}%
            </div>
        </div>
        
        <!-- Entities -->
        <div class="section">
            <h2>Key Entities</h2>
            <div class="entity-list">
                {% for entity in state.analysis.entities[:30] %}
                <span class="entity-badge">{{ entity.text }} ({{ entity.label.value }})</span>
                {% endfor %}
            </div>
        </div>
        
        <!-- Topics -->
        <div class="section">
            <h2>Main Topics</h2>
            {% for topic in state.analysis.topics %}
            <div>
                <h3>{{ topic.label }}</h3>
                <div class="topic-list">
                    {% for word in topic.words %}
                    <span class="topic-badge">{{ word }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <!-- Word Cloud -->
        {% if visualization.word_cloud %}
        <div class="section">
            <h2>Word Cloud</h2>
            <div class="wordcloud-container">
                <img src="{{ visualization.word_cloud }}" alt="Word Cloud" class="wordcloud-img">
            </div>
        </div>
        {% endif %}
        
        <!-- Timeline -->
        {% if state.analysis.timeline %}
        <div class="section">
            <h2>Timeline</h2>
            <div class="timeline">
                {% for event in state.analysis.timeline[:10] %}
                <div class="timeline-item">
                    <div class="timeline-date">{{ event.date }}</div>
                    <div>{{ event.event }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <!-- Related Queries -->
        {% if state.analysis.related_queries %}
        <div class="section">
            <h2>Related Queries</h2>
            <ul class="related-queries">
                {% for query in state.analysis.related_queries %}
                <li>{{ query.query }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
        {% endif %}
        
        <!-- Source Links -->
        <div class="section">
            <h2>Sources</h2>
            <div style="margin-top: 15px;">
                {% for result in state.search_results[:10] %}
                <div style="margin: 10px 0; padding: 10px; background-color: #f8f9fa; border-radius: 4px;">
                    <a href="{{ result.link }}" target="_blank" style="color: #3498db; text-decoration: none; font-weight: bold;">
                        {{ result.title }}
                    </a>
                    <div style="color: #666; font-size: 0.9em; margin-top: 5px;">
                        {{ result.snippet }}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by Content Research Pipeline</p>
            <p>© {{ state.created_at.year }} - All Rights Reserved</p>
        </div>
    </div>
</body>
</html>
        """
        return Template(template_str)
    
    async def generate_report(
        self,
        state: PipelineState,
        visualization: VisualizationData,
        processing_time: Optional[float] = None
    ) -> str:
        """
        Generate HTML report from pipeline state and visualization data.
        
        Args:
            state: Pipeline state
            visualization: Visualization data
            processing_time: Total processing time in seconds
            
        Returns:
            HTML report string
        """
        logger.info("Generating HTML report")
        
        try:
            # Render template in thread pool
            html = await asyncio.to_thread(
                self.template.render,
                state=state,
                visualization=visualization,
                processing_time=processing_time
            )
            
            logger.info(f"HTML report generated: {len(html)} characters")
            return html
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            return self._generate_error_report(state.query, str(e))
    
    def _generate_error_report(self, query: str, error: str) -> str:
        """
        Generate a simple error report.
        
        Args:
            query: Original query
            error: Error message
            
        Returns:
            HTML error report
        """
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Error: {query}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }}
        .error {{
            background-color: #fee;
            border: 1px solid #fcc;
            padding: 20px;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <h1>Report Generation Error</h1>
    <div class="error">
        <h2>Query: {query}</h2>
        <p><strong>Error:</strong> {error}</p>
        <p>Please try again or contact support if the problem persists.</p>
    </div>
</body>
</html>
        """


# Global report generator instance
report_generator = ReportGenerator()
