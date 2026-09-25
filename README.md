DocuGen

A full-stack tool that crawls real GitHub repositories via the public API and uses OpenAI to generate validated, publication-ready installation and maintenance documentation for end-users.

## Features

- GitHub repository crawler that extracts file structures, dependency manifests, and README content to build a structured project profile fed into the AI pipeline.
- AI-powered documentation generator using OpenAI API to produce step-by-step installation guides, maintenance schedules, and troubleshooting procedures validated by an automated testing harness.
- End-user-facing documentation portal with search, versioning, and feedback collection, demonstrating cross-functional collaboration through requirement-driven content organization.

## Tech Stack

- Python (Flask)
- HTML/CSS/JavaScript
- OpenAI API
- GitHub REST API
- SQLite

## Setup

1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Set environment variables:
   - `OPENAI_API_KEY=your_openai_key`
   - `GITHUB_TOKEN=your_github_token` (optional)
4. Run the application: `python main.py`.
5. Open http://localhost:5000 in your browser.

## Usage

Enter a GitHub repository URL on the home page and click "Generate". The system will crawl the repository, generate installation and maintenance guides, and display them. You can view all generated guides from the /docs page.

## API Endpoints

- `GET /` - Home page with generation form.
- `POST /generate` - Accepts repository URL, generates docs, redirects to detail page.
- `GET /docs` - Lists all generated guides.
- `GET /docs/<id>` - Displays a specific guide.

## Database Schema

The application uses SQLite with a table `docs` containing columns: `id`, `repo_url`, `title`, `installation`, `maintenance`, `troubleshooting`, `created_at`.

## Contributing

Pull requests are welcome. Please ensure tests pass before submitting.

## License

MIT