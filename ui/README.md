# Content Research Pipeline - Web UI

This directory contains the frontend web interface for the Content Research Pipeline.

## Files

- **index.html** - Main HTML interface
- **style.css** - Styling and animations
- **app.js** - JavaScript client logic for API communication

## Features

- Settings modal for API key configuration
- Real-time research job status tracking
- Progress bar with visual feedback
- Automatic report link generation
- Toast notifications
- Responsive design for mobile and desktop

## Usage

The UI is automatically served by FastAPI when you run the application:

```bash
# Using Docker Compose
docker-compose up

# Access at http://localhost:8000
```

## Configuration

Click the "⚙️ Settings" button to configure:

1. **OpenAI API Key** (required) - For AI analysis
2. **Google API Key** (required) - For search
3. **Google CSE ID** (required) - For custom search
4. **Pipeline API Key** (optional) - For server authentication

Keys are stored in your browser's localStorage and sent with each research request.

## API Endpoints Used

- `POST /research` - Start a new research job
- `GET /status/{job_id}` - Get job status
- `GET /reports/{job_id}.html` - View generated report

## Development

To modify the UI:

1. Edit the HTML, CSS, or JS files
2. Refresh your browser (no build step required)
3. Changes are reflected immediately

The UI is served as static files by FastAPI and requires no build process.
