# MemoryBun Frontend 🎓

> Your AI-powered Oxbridge interview tutor with real-time feedback and transcription

A modern React-based frontend application for MemoryBun, providing an interactive interface for students to practice interview questions with AI-powered grading, real-time transcription, and comprehensive performance analytics.

[![React](https://img.shields.io/badge/React-18.2-blue?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?logo=vite)](https://vite.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-TBD-lightgrey)]()

## 📑 Table of Contents

- [Quick Start](#-quick-start)
- [Key Features](#-key-features)
- [Project Structure](#-project-structure)
- [Architecture](#%EF%B8%8F-architecture)
- [Configuration](#-configuration)
- [API Integration](#-api-integration)
- [Development Guidelines](#-development-guidelines)
- [Docker Commands](#-docker-commands-reference)
- [Troubleshooting](#-troubleshooting)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

## ✨ Tech Highlights

- 🎙️ **WebRTC Audio Recording** - Real-time audio capture with MediaRecorder API
- 🤖 **Whisper AI Integration** - OpenAI Whisper for accurate transcription
- 🧠 **LLM-Powered Grading** - Gemini/OpenAI for intelligent feedback
- 🎨 **Interactive Canvas** - HTML5 Canvas with screenshot capabilities
- 📐 **LaTeX Math Rendering** - KaTeX for beautiful mathematical expressions
- 🔄 **Async State Management** - Custom hooks for complex async flows
- 🐳 **Docker-Ready** - Multi-stage builds with Nginx production server
- ♿ **Accessible UI** - Radix UI primitives for WCAG compliance
- 📱 **Responsive Design** - Mobile-first approach with Tailwind CSS
- 🔒 **Type-Safe** - Full TypeScript with strict mode enabled

## 🎬 Quick Demo

```
┌─────────────────────────────────────────────────────────────┐
│  Question Menu → Select Question → Practice with AI         │
│       ↓              ↓                   ↓                   │
│   Browse Lists   → Question Page  → Get Instant Feedback    │
│                     (Record Audio)    (AI Grading)          │
│                     (Draw Diagrams)   (Transcription)       │
│                          ↓                                   │
│                   Summary Report ← View Performance         │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Option 1: Docker (Recommended for Production)

Run the entire MemoryBun stack (frontend + backend services) with Docker:

```bash
# From the project root directory
docker-compose up -d

# View logs
docker-compose logs -f frontend

# Stop all services
docker-compose down
```

**Access the frontend**: http://localhost:8080

> **Note**: The Docker setup uses port 8080 to avoid conflicts with the development server on port 3000.

### Option 2: Local Development

#### Prerequisites

- **Node.js** (v20 or higher) - [Download](https://nodejs.org/en/)
- **npm** (v10 or higher, comes with Node.js)
- Backend services running (see [backend/README.md](../backend/README.md))

#### Installation

1. **Install dependencies**:
```bash
cd frontend
npm install
```

2. **Configure environment** (optional):
Create a `.env` file in the `frontend/` directory:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_TRANSCRIPTION_API_URL=http://localhost:8001
VITE_GRADING_API_URL=http://localhost:8002
```

3. **Start the development server**:
```bash
npm run dev
```

4. **Open your browser** to [http://localhost:3000](http://localhost:3000)

#### Build for Production

```bash
npm run build
```

The production build will be output to the `dist/` directory.

## 📁 Project Structure

```
frontend/
├── .dockerignore          # Docker build optimization
├── .nginx.conf            # Production Nginx configuration
├── Dockerfile             # Multi-stage Docker build (Node.js → Nginx)
├── public/                # Static assets (images, logos)
│   ├── MemoryBun_logo_3.png
│   ├── MemoryBun_Logo_Square.png
│   └── MemoryBun-landscape-white.png
├── src/
│   ├── components/        # Reusable UI components
│   │   └── ui/           # Base UI components (Radix UI based)
│   │       ├── avatar.tsx
│   │       ├── button.tsx
│   │       ├── input.tsx
│   │       └── separator.tsx
│   ├── config/           # Configuration files
│   │   ├── questions.ts       # Question data configuration
│   │   └── summaryReport.ts   # Summary report data configuration
│   ├── hooks/            # Custom React hooks
│   │   ├── useAudioRecorder.ts           # MediaRecorder API wrapper
│   │   ├── useTranscriptionRecorder.ts   # Transcription orchestration
│   │   ├── useGradingFeedback.ts         # Grading result polling
│   │   ├── useQuestionListData.ts        # Question data loading
│   │   └── usePartState.ts               # Per-part state management
│   ├── lib/              # Utility functions
│   │   ├── mathUtils.tsx # LaTeX rendering utilities
│   │   ├── utils.ts      # General utilities (cn, classNames)
│   │   └── webmUtils.ts  # WebM audio processing utilities
│   ├── screens/          # Main application screens
│   │   ├── QuestionMenu/      # Question list/menu page
│   │   │   ├── index.ts
│   │   │   ├── QuestionMenu.tsx
│   │   │   └── sections/
│   │   │       ├── WelcomeBackSection.tsx
│   │   │       ├── QuestionListSection.tsx
│   │   │       └── QuestionListTable.tsx
│   │   ├── QuestionSample/    # Question practice page
│   │   │   ├── index.ts
│   │   │   ├── QuestionSample.tsx
│   │   │   ├── README.md      # Detailed documentation
│   │   │   └── sections/
│   │   │       ├── QuestionSidebar.tsx
│   │   │       ├── DrawingBoard.tsx
│   │   │       ├── DrawingToolbar.tsx
│   │   │       ├── PlotGrid.tsx
│   │   │       ├── PrepTimer.tsx
│   │   │       ├── RecordingControls.tsx
│   │   │       └── Hint.tsx
│   │   └── SummaryReport/     # Performance summary page
│   │       ├── index.ts
│   │       ├── SummaryReport.tsx
│   │       └── sections/
│   │           ├── SessionOverview.tsx
│   │           ├── PerformanceSummary.tsx
│   │           ├── FeedbackByQuestions.tsx
│   │           └── StrengthsAndImprovements.tsx
│   ├── services/         # API service layer
│   │   ├── api.ts                # Question Service API
│   │   ├── transcriptionApi.ts   # Transcription Service API
│   │   └── gradingApi.ts         # Grading Service API
│   ├── types/           # TypeScript type definitions
│   │   ├── api.ts       # API response types
│   │   └── react-katex.d.ts  # KaTeX type definitions
│   └── index.tsx        # Application entry point
├── package.json          # Dependencies and scripts
├── vite.config.ts        # Vite configuration
├── tailwind.config.js    # Tailwind CSS configuration
├── tailwind.css          # Tailwind base styles
└── tsconfig.json         # TypeScript configuration
```

## 🏗️ Architecture

### Tech Stack

- **React 18.2** - UI framework
- **TypeScript** - Type safety (strict mode)
- **Vite 6.0** - Build tool and dev server
- **React Router 6.8** - Client-side routing
- **Tailwind CSS 3.4** - Utility-first CSS framework
- **KaTeX 0.16** - Math rendering (LaTeX support)
- **Radix UI** - Accessible component primitives (Avatar, Separator, Slot)
- **Lucide React** - Icon library (450+ icons)
- **html2canvas 1.4** - Canvas screenshot capture for grading
- **class-variance-authority** - Composable component variants
- **Nginx (Docker)** - Production web server

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose Stack                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐   ┌─────────────────┐   ┌──────────────┐ │
│  │   Frontend   │   │ Question Service│   │ Transcription│ │
│  │  (Nginx)     │──▶│  (FastAPI)      │   │   Service    │ │
│  │  Port: 8080  │   │  Port: 8000     │   │  Port: 8001  │ │
│  └──────────────┘   └─────────────────┘   └──────────────┘ │
│         │                    │                      │        │
│         │                    │                      │        │
│         └────────────────────┼──────────────────────┘        │
│                              │                               │
│                    ┌─────────▼─────────┐                     │
│                    │ Grading Service   │                     │
│                    │   (FastAPI)       │                     │
│                    │   Port: 8002      │                     │
│                    └───────────────────┘                     │
│                              │                               │
│                    ┌─────────▼─────────┐                     │
│                    │      Redis        │                     │
│                    │   (Cache/Queue)   │                     │
│                    │   Port: 6379      │                     │
│                    └───────────────────┘                     │
│                                                               │
│  ┌──────────────┐   ┌─────────────────┐                     │
│  │  Prometheus  │   │    Grafana      │  (Monitoring)       │
│  │  Port: 9090  │   │   Port: 3001    │                     │
│  └──────────────┘   └─────────────────┘                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Production Build

The frontend uses a **multi-stage Docker build**:

1. **Build Stage** (Node.js 20 Alpine):
   - Installs dependencies with `npm ci`
   - Builds production assets with Vite
   - Outputs to `/app/dist`

2. **Production Stage** (Nginx Alpine):
   - Copies built assets to `/usr/share/nginx/html`
   - Serves with Nginx (optimized for SPA routing)
   - Health check endpoint at `/health`
   - Gzip compression enabled
   - Static asset caching (1 year)

### Key Patterns

#### Component Organization
- **Screens**: Top-level page components (`QuestionMenu`, `QuestionSample`, `SummaryReport`)
- **Sections**: Sub-components within screens (e.g., `QuestionSidebar`, `DrawingBoard`)
- **UI Components**: Reusable, generic components in `components/ui/`

#### Custom Hooks

The frontend uses a layered hook architecture for complex features:

```
Recording & Transcription Flow:
┌─────────────────────────────────────┐
│     useTranscriptionRecorder        │  ← Orchestration layer
│  (session, chunks, finalization)    │
├─────────────────────────────────────┤
│         useAudioRecorder            │  ← Low-level API layer
│      (MediaRecorder API)            │
└─────────────────────────────────────┘

Question Practice Flow:
┌─────────────────────────────────────┐
│      useQuestionListData            │  ← Data loading layer
│       (fetch questions)             │
├─────────────────────────────────────┤
│         usePartState                │  ← State management layer
│   (timers, per-part state)          │
├─────────────────────────────────────┤
│      useGradingFeedback             │  ← Feedback layer
│    (AI grading, polling)            │
└─────────────────────────────────────┘
```

| Hook | Purpose | Location |
|------|---------|----------|
| `useAudioRecorder` | Low-level MediaRecorder API wrapper for WebM/Opus audio | `hooks/useAudioRecorder.ts` |
| `useTranscriptionRecorder` | Orchestrates recording + transcription flow with Whisper | `hooks/useTranscriptionRecorder.ts` |
| `useGradingFeedback` | Polls grading service for AI feedback and results | `hooks/useGradingFeedback.ts` |
| `useQuestionListData` | Loads question data from backend with caching | `hooks/useQuestionListData.ts` |
| `usePartState` | Manages per-part state, timers, completion tracking | `hooks/usePartState.ts` |

See [`screens/QuestionSample/README.md`](src/screens/QuestionSample/README.md) for detailed hook documentation.

#### Data Management
- **Config Files**: Static/question-specific data in `config/` directory
- **API Services**: Backend communication via `services/api.ts`
- **Type Definitions**: Shared types in `types/api.ts`

#### State Management
- **Local State**: React hooks (`useState`, `useEffect`) for component-level state
- **Custom Hooks**: Complex stateful logic extracted into reusable hooks
- **URL State**: React Router for navigation and route parameters
- **No Global State**: Currently no Redux/Zustand (can be added if needed)


## 🎯 Key Features

### 📋 Question Menu (`/`)
**Browse and manage your interview practice**

- 📚 Browse available question lists with metadata
- 🔍 Filter by category, topic, or difficulty
- 📊 Sort by multiple criteria (category, difficulty, duration)
- ✅ Track completion status across questions
- ⭐ Star and bookmark favorite questions
- 📈 View progress and statistics
- 🎨 Clean, responsive table interface

### 🎤 Question Sample (`/question/:id`)
**Interactive question practice with AI feedback**

#### Core Features
- 📝 **Multi-part Question Support**: Navigate through question parts sequentially
- ⏱️ **Smart Timers**: Separate timers for prep time and recording time
- 🎙️ **Real-time Audio Recording**: WebM/Opus streaming to transcription service
- 📜 **Live Transcription**: Whisper AI converts speech to text in real-time
- 🤖 **AI-Powered Grading**: LLM-based evaluation with rubric scoring
- 💬 **Detailed Feedback**: Multi-criteria assessment with actionable insights

#### Drawing Board
- 🎨 **Canvas Tools**: Pen, eraser, and color selection
- 📐 **Plot Grid**: Mathematical function plotting with grid lines
- 📸 **Screenshot Capture**: html2canvas integration for visual grading
- 🖼️ **Visual Context**: Screenshots sent to grading service for comprehensive evaluation

#### Question Sidebar
- 📖 **Instructions & Hints**: Collapsible sections for guidance
- 🔢 **LaTeX Support**: KaTeX rendering for mathematical expressions
- 📑 **Multi-part Navigation**: Clear indication of current part
- ℹ️ **Question Metadata**: Duration, difficulty, topic

#### Recording Flow
1. **Prep Phase**: Review question, use drawing board, plan answer
2. **Recording Phase**: Answer while transcription runs in background
3. **Grading Phase**: AI evaluates transcription + screenshot
4. **Feedback Phase**: Receive detailed rubric-based assessment

### 📊 Summary Report (`/summary_report`)
**Comprehensive performance analytics**

- 📅 **Session Overview**: Date, question list, duration, completion
- 🎯 **Performance Summary**: Radar chart with multi-dimensional metrics
- 📸 **Feedback Carousel**: Question-by-question review with images
- 💡 **Strengths Analysis**: Areas where you excelled
- 🎓 **Improvement Areas**: Actionable suggestions for growth
- 📈 **Score Breakdown**: Detailed rubric scoring across criteria
- 🔄 **Multi-session Summaries**: Aggregate performance over multiple questions

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `frontend/` directory for local development:

```env
# Question Service (FastAPI)
VITE_API_BASE_URL=http://localhost:8000

# Transcription Service (Whisper API)
VITE_TRANSCRIPTION_API_URL=http://localhost:8001
VITE_TRANSCRIPTION_MODEL=base

# Grading Service (LLM-powered grading)
VITE_GRADING_API_URL=http://localhost:8002
```

#### Environment Variable Details

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Question Service endpoint (lists, questions, answers) |
| `VITE_TRANSCRIPTION_API_URL` | `http://localhost:8001` | Transcription Service endpoint (Whisper AI) |
| `VITE_TRANSCRIPTION_MODEL` | `base` | Whisper model (`tiny`, `base`, `small`, `medium`, `large`) |
| `VITE_GRADING_API_URL` | `http://localhost:8002` | Grading Service endpoint (AI feedback) |
| `VITE_MIN_RECORDING_DURATION` | `5` | Minimum recording duration in seconds (0 to disable) |
| `VITE_DEV_MODE` | `false` | Bypass minimum duration in development (`true`/`false`) |

> **Note**: In Docker deployment, API URLs are handled automatically by the internal network (`memorybun-network`).

#### Recording Configuration

The platform enforces a **minimum recording duration** to ensure quality answers:

- **Production**: Recordings must be ≥ 5 seconds (configurable)
- **Development**: Set `VITE_DEV_MODE=true` to bypass minimum duration for faster testing
- **Disable**: Set `VITE_MIN_RECORDING_DURATION=0` to accept any duration

See [RECORDING_DURATION.md](RECORDING_DURATION.md) for detailed configuration guide.

### Config Files

#### `config/questions.ts`
Contains question data structure and type definitions for question sets.

#### `config/summaryReport.ts`
Contains dynamic data for the summary report page:
- Session overview data
- Performance metrics
- Question feedback slides
- Strengths and improvements

**Note**: Static UI labels (like "Summary Report", "Session Overview") are hard-coded in components, while dynamic content comes from config files.

## 🔌 API Integration

The frontend communicates with three backend microservices via REST APIs:

### Question Service (`services/api.ts`)
Port: 8000 | Base URL: `VITE_API_BASE_URL`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/question-lists` | GET | Fetch all question lists with metadata |
| `/api/v1/question-lists/:id/questions` | GET | Fetch all questions in a specific list |
| `/api/v1/answers` | GET | Fetch answers by question IDs |

### Transcription Service (`services/transcriptionApi.ts`)
Port: 8001 | Base URL: `VITE_TRANSCRIPTION_API_URL`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/transcribe/session` | POST | Create a new transcription session |
| `/api/v1/transcribe/session/:id/audio/chunk` | POST | Upload audio chunk (WebM) |
| `/api/v1/transcribe/session/:id/audio/chunk/:idx/status` | GET | Check chunk processing status |
| `/api/v1/transcribe/session/:id/audio` | GET | Get accumulated transcription |
| `/api/v1/transcribe/session/:id/audio/finalize` | POST | Finalize session and trigger grading |
| `/api/v1/transcribe/session/:id/screenshot` | POST | Upload screenshot for visual grading |

**Features**:
- Streaming audio upload (chunks sent as recorded)
- Whisper AI model selection (`tiny`, `base`, `small`, `medium`, `large`)
- Real-time transcription polling
- Screenshot support for drawing board grading

### Grading Service (`services/gradingApi.ts`)
Port: 8002 | Base URL: `VITE_GRADING_API_URL`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/grading/session/:id/status` | GET | Check grading status (polling) |
| `/api/v1/grading/session/:id/result` | GET | Get full grading result |
| `/api/v1/grading/summarize` | POST | Generate summary for multiple sessions |
| `/api/v1/grading/summary/:id/status` | GET | Check summary generation status |
| `/api/v1/grading/summary/:id/result` | GET | Get final summary report |

**Features**:
- LLM-powered feedback (Gemini or OpenAI)
- Rubric-based grading
- Multi-criteria evaluation
- Session summary generation
- Polling with exponential backoff

### API Client Features

All API clients include:
- ✅ **AbortController** support for request cancellation
- ✅ **Error handling** with descriptive messages
- ✅ **Type-safe responses** with TypeScript interfaces
- ✅ **Polling utilities** for async operations
- ✅ **FormData** support for file uploads

## 🎨 Styling

### Tailwind CSS
- Utility-first CSS framework
- Responsive design with breakpoints (`sm`, `md`, `lg`, `xl`, `2xl`)
- Custom color palette (primary: `#0053FA`)
- Consistent spacing and typography

### Responsive Design
- Mobile-first approach
- Breakpoints:
  - `sm`: 640px
  - `md`: 768px
  - `lg`: 1024px
  - `xl`: 1280px
  - `2xl`: 1536px

## 📝 Development Guidelines

### Code Style
- **TypeScript**: Strict mode enabled
- **Components**: Functional components with TypeScript
- **Naming**: PascalCase for components, camelCase for functions/variables
- **Imports**: Absolute imports from `src/` root

### Component Patterns
- **Container/Presentational**: Separate data fetching from UI rendering
- **Props**: Explicit prop types with TypeScript interfaces
- **Hooks**: Use React hooks for state and side effects
- **Cleanup**: Always clean up timers and network requests in `useEffect`

### Best Practices
- ✅ Extract reusable logic into utility functions
- ✅ Keep components focused and single-purpose
- ✅ Use TypeScript for type safety
- ✅ Handle loading and error states
- ✅ Clean up async operations on unmount
- ❌ Avoid prop drilling (consider context if needed)
- ❌ Don't mutate state directly
- ❌ Don't forget to clean up timers/requests

## 🧪 Testing

*Testing setup to be added*

## 🐛 Troubleshooting

### Docker Issues

#### Port Already in Use (8080)
If port 8080 is in use:
```bash
# Stop all containers
docker-compose down

# Check what's using the port (Windows)
netstat -ano | findstr :8080

# Or change the port in docker-compose.yml:
# ports:
#   - "8081:80"  # Change host port to 8081
```

#### Frontend Shows Unhealthy in Docker
The frontend may show as "unhealthy" due to an IPv6 resolution quirk in Alpine Linux. **This is cosmetic** - if you can access http://localhost:8080, the service is working correctly.

#### Cannot Connect to Backend Services
```bash
# Check all services are running
docker-compose ps

# Check service logs
docker-compose logs -f frontend
docker-compose logs -f question-service

# Restart services
docker-compose restart
```

### Local Development Issues

#### Port 3000 Already in Use
If port 3000 is already in use, Vite will automatically try the next available port. Check the terminal output for the actual port, or set a custom port:

```bash
# In package.json, modify the dev script:
"dev": "vite --port 3001"
```

#### API Connection Issues
- Ensure all backend services are running:
  - Question Service: `http://localhost:8000`
  - Transcription Service: `http://localhost:8001`
  - Grading Service: `http://localhost:8002`
- Check browser console for CORS errors
- Verify network tab for failed requests
- Check `.env` file configuration

#### MediaRecorder Not Supported
The audio recording feature requires:
- Modern browser (Chrome 49+, Firefox 25+, Safari 14+)
- HTTPS or localhost (getUserMedia requirement)
- WebM/Opus codec support

### Recording Rejected (Too Short)
If recordings are being rejected:
- **Production**: Ensure recording is at least 5 seconds (or configured minimum)
- **Development**: Set `VITE_DEV_MODE=true` to bypass minimum duration
- **Testing**: Lower `VITE_MIN_RECORDING_DURATION` in staging environments
- See [RECORDING_DURATION.md](RECORDING_DURATION.md) for configuration details

#### Build Errors
```bash
# Clear node_modules and reinstall
rm -rf node_modules
npm install

# Clear Vite cache
rm -rf node_modules/.vite
rm -rf dist

# Check TypeScript errors
npx tsc --noEmit

# Rebuild
npm run build
```

### Performance Issues

#### Slow Build Times
```bash
# Use npm ci for faster clean installs
npm ci

# Clear cache
rm -rf node_modules/.vite
```

#### Large Bundle Size
The current bundle is ~762 KB (minified). To optimize:
- Use dynamic imports for route-based code splitting
- Check bundle analyzer: `npm run build -- --analyze`
- Consider lazy loading KaTeX (largest dependency)

## 🐳 Docker Commands Reference

### Building and Running

```bash
# Build and start all services
docker-compose up -d

# Build only frontend (with cache)
docker-compose build frontend

# Build frontend without cache (clean build)
docker-compose build --no-cache frontend

# Start only frontend
docker-compose up -d frontend

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Viewing Logs

```bash
# Follow all logs
docker-compose logs -f

# Follow frontend logs only
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail 100 frontend
```

### Debugging

```bash
# Check service status
docker-compose ps

# Execute command in container
docker exec -it memorybun-frontend sh

# Check nginx config
docker exec memorybun-frontend cat /etc/nginx/conf.d/default.conf

# Test health endpoint
curl http://localhost:8080/health
```

### Cleaning Up

```bash
# Remove stopped containers
docker-compose rm

# Remove all images
docker rmi $(docker images -q memorybun-*)

# Clean build cache
docker builder prune
```

## 📚 Additional Resources

### Documentation
- [React Documentation](https://react.dev/) - React 18 features and API
- [TypeScript Documentation](https://www.typescriptlang.org/) - TypeScript handbook
- [Vite Documentation](https://vite.dev/) - Build tool and dev server
- [Tailwind CSS Documentation](https://tailwindcss.com/) - Utility-first CSS
- [React Router Documentation](https://reactrouter.com/) - Client-side routing

### Component Libraries
- [Radix UI](https://www.radix-ui.com/) - Accessible component primitives
- [Lucide Icons](https://lucide.dev/) - Icon library
- [KaTeX](https://katex.org/) - Math rendering

### Backend Services
- [Backend README](../backend/README.md) - Backend microservices overview
- [Question Service](../backend/question_service/README.md) - Question API docs
- [Transcription Service](../backend/transcription_service/README.md) - Whisper AI integration
- [Grading Service](../backend/grading_service/README.md) - LLM grading pipeline

## 🚢 Deployment

### Production Checklist

Before deploying to production:

- [ ] Set proper environment variables (API URLs)
- [ ] Configure CORS on backend services
- [ ] Enable HTTPS/TLS
- [ ] Set up proper error tracking (e.g., Sentry)
- [ ] Configure CDN for static assets
- [ ] Set up monitoring (Prometheus + Grafana included)
- [ ] Review security headers in `.nginx.conf`
- [ ] Test on target browsers
- [ ] Optimize bundle size (code splitting)
- [ ] Set up backup/disaster recovery

### Docker Production Deployment

```bash
# Build production images
docker-compose build

# Start services with restart policy
docker-compose up -d

# Monitor with included Grafana
# Access: http://localhost:3001
# Default: admin / memorybun (change this!)
```

### Static Hosting (Alternative)

If you prefer to host the frontend separately:

```bash
# Build production bundle
npm run build

# Output directory: dist/
# Upload to: Vercel, Netlify, AWS S3, etc.
```

**Note**: Ensure backend services are accessible from the hosting environment.

## 🤝 Contributing

### Code Standards

1. **TypeScript First**
   - Use strict mode (`tsconfig.json`)
   - Define explicit types for props, state, and API responses
   - Avoid `any` types

2. **Component Guidelines**
   - Functional components with hooks (no class components)
   - Keep components under 300 lines
   - Extract complex logic into custom hooks
   - Use consistent naming: `PascalCase` for components, `camelCase` for functions

3. **Code Style**
   - Consistent formatting (consider adding Prettier)
   - Meaningful variable names
   - Comments for complex business logic
   - JSDoc for utility functions

4. **State Management**
   - Local state for UI-only concerns
   - Custom hooks for shared stateful logic
   - Consider Context API for deeply nested props
   - React Router for navigation state

5. **Testing** (to be implemented)
   - Unit tests for utilities and hooks
   - Integration tests for critical flows
   - E2E tests for key user journeys

### Contribution Workflow

1. Check existing issues or create a new one
2. Fork the repository
3. Create a feature branch: `git checkout -b feature/amazing-feature`
4. Make your changes
5. Test thoroughly (local + Docker)
6. Update documentation if needed
7. Commit: `git commit -m 'Add amazing feature'`
8. Push: `git push origin feature/amazing-feature`
9. Open a Pull Request

### Key Areas for Contribution

- 🧪 **Testing**: Add unit/integration tests
- ♿ **Accessibility**: Improve WCAG compliance
- 🎨 **UI/UX**: Enhance user experience
- 📱 **Mobile**: Improve mobile responsiveness
- ⚡ **Performance**: Optimize bundle size and load times
- 🌍 **i18n**: Add internationalization support
- 📊 **Analytics**: Add user behavior tracking

## 📄 License

*To be determined*

---

---

## 📞 Support & Contact

For questions, issues, or contributions:
- 🐛 **Issues**: Report bugs via GitHub Issues
- 💬 **Discussions**: Join community discussions
- 📧 **Email**: [Contact team for support]
- 📖 **Documentation**: See additional READMEs in service directories

## 🔗 Related Documentation

- [Backend Services Overview](../backend/README.md)
- [Question Service API](../backend/question_service/README.md)
- [Transcription Service](../backend/transcription_service/README.md)
- [Grading Service Pipeline](../backend/grading_service/README.md)
- [Question Sample Detailed Docs](src/screens/QuestionSample/README.md)
- [Recording Duration Configuration](RECORDING_DURATION.md) - **New!**

---

<div align="center">

**MemoryBun Frontend v1.0.0**  
*Built with ❤️ for aspiring Oxbridge students*

Last Updated: January 2026  
[Report Bug](../../issues) · [Request Feature](../../issues) · [View Backend](../backend/)

</div>
