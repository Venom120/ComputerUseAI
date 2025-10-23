# ComputerUseAI Architecture

## Overview

ComputerUseAI is a desktop AI assistant that learns user workflows through observation and automates repetitive tasks. The system is designed with privacy-first principles, running entirely locally without cloud dependencies.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ComputerUseAI                            │
├─────────────────────────────────────────────────────────────────┤
│  User Interface Layer (PyQt6)                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   Dashboard │ │ Workflows   │ │  Timeline   │ │  Settings   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                System Tray Integration                      ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  Core Processing Pipeline                                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   Capture   │ │ Processing  │ │Intelligence │ │ Automation  ││
│  │             │ │             │ │             │ │             ││
│  │ • Screen    │ │ • STT       │ │ • LLM       │ │ • Executor  ││
│  │ • Audio     │ │ • OCR       │ │ • Patterns  │ │ • Computer  ││
│  │ • Events    │ │ • Analysis  │ │ • Learning  │ │ • Verify    ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  Data Storage Layer                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   SQLite    │ │ File Mgr    │ │  Cleanup    │ │  Models     ││
│  │             │ │             │ │             │ │             ││
│  │ • Captures  │ │ • Storage   │ │ • Policies  │ │ • Whisper   ││
│  │ • Workflows │ │ • Encrypt   │ │ • Auto-del  │ │ • Phi-3     ││
│  │ • Events    │ │ • Compress  │ │ • Limits    │ │ • Tesseract ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Capture Layer

**Purpose**: Record user activity with minimal performance impact

**Components**:
- **Screen Capture**: Frame differencing, WebP compression, multi-monitor support
- **Audio Capture**: VAD (Voice Activity Detection), segment-based recording
- **Event Tracker**: Mouse/keyboard events, active window detection

**Key Features**:
- Frame differencing reduces storage by 80-90%
- WebP compression for efficient storage
- Privacy controls (app exclusion)
- Real-time processing pipeline

### 2. Processing Layer

**Purpose**: Convert raw captures into structured, analyzable data

**Components**:
- **Speech-to-Text**: Whisper.cpp for offline transcription
- **OCR Engine**: Tesseract for text extraction from screenshots
- **Screen Analyzer**: Generate JSON descriptions of screen state
- **Pattern Recognition**: ML-based workflow similarity detection

**Key Features**:
- Offline processing (no cloud dependencies)
- Confidence scoring for accuracy
- Multi-language support
- Batch processing for efficiency

### 3. Intelligence Layer

**Purpose**: Understand user behavior and generate automation plans

**Components**:
- **Local LLM**: Phi-3 Mini for workflow understanding
- **Workflow Generator**: Convert patterns into executable steps
- **Learning Engine**: Continuous improvement from user feedback

**Key Features**:
- 3.8B parameter model (Phi-3 Mini)
- Context-aware workflow generation
- Similarity-based pattern matching
- Confidence-based automation triggers

### 4. Automation Layer

**Purpose**: Execute learned workflows with error handling

**Components**:
- **Computer Use**: PyAutoGUI-based input automation
- **Workflow Executor**: Step-by-step execution with retry logic
- **Verification**: OCR-based success confirmation

**Key Features**:
- Robust error handling and retry logic
- Visual verification of actions
- Graceful failure recovery
- User intervention support

### 5. Storage Layer

**Purpose**: Efficient data management with privacy controls

**Components**:
- **SQLite Database**: Structured storage for metadata
- **File Manager**: Compressed storage with encryption options
- **Cleanup Policies**: Automatic data lifecycle management

**Key Features**:
- Encrypted storage option
- Automatic cleanup (7-day retention)
- Size limits (1GB default)
- Export/import capabilities

## Data Flow

```
User Action → Capture → Processing → Intelligence → Automation
     ↑                                                    ↓
     └─────────────── Learning Loop ←─────────────────────┘
```

### Detailed Flow:

1. **Capture**: Screen/audio/events recorded with frame differencing
2. **Processing**: STT transcription, OCR text extraction, screen analysis
3. **Intelligence**: LLM analyzes patterns, generates workflow descriptions
4. **Storage**: Structured data stored in SQLite + compressed files
5. **Automation**: Learned workflows executed with verification
6. **Learning**: Feedback loop improves pattern recognition

## Performance Optimizations

### Capture Optimizations
- **Frame Differencing**: Only save changed regions (80-90% reduction)
- **WebP Compression**: 5-10x smaller than PNG
- **Resolution Capping**: Max 1080p to reduce processing load
- **FPS Control**: 2-5 FPS for efficiency

### Processing Optimizations
- **Batch Processing**: Process multiple items together
- **Caching**: Reuse OCR results for unchanged regions
- **Async Processing**: Non-blocking background processing
- **Model Quantization**: 4-bit models for 3x speed improvement

### Storage Optimizations
- **Compression**: WebP for images, FLAC for audio
- **Cleanup**: Automatic deletion of old data
- **Indexing**: Database indexes for fast queries
- **Deduplication**: Avoid storing duplicate content

## Security & Privacy

### Local Processing
- All AI models run on device
- No external API calls
- No telemetry or analytics
- Optional data encryption

### Privacy Controls
- Application exclusion lists
- Automatic password field detection
- User-controlled data retention
- One-click data deletion

### Security Measures
- Encrypted storage (AES-256)
- Secure model downloads
- No network dependencies
- Open source for audit

## Scalability Considerations

### Horizontal Scaling
- Modular component design
- Independent processing pipelines
- Configurable resource limits
- Plugin architecture for extensions

### Vertical Scaling
- Configurable model sizes
- Adjustable processing quality
- Memory usage optimization
- CPU/GPU utilization controls

## Error Handling

### Capture Errors
- Graceful degradation on capture failure
- Fallback to lower quality/rate
- User notification of issues
- Automatic retry mechanisms

### Processing Errors
- Skip failed items, continue processing
- Confidence-based filtering
- User feedback integration
- Error logging and reporting

### Automation Errors
- Retry with position adjustments
- Fallback to manual verification
- User intervention prompts
- Workflow learning from failures

## Future Enhancements

### Planned Features
- Multi-user support
- Cloud sync (optional)
- Advanced ML models
- Plugin ecosystem
- Mobile companion app

### Technical Improvements
- GPU acceleration
- Distributed processing
- Advanced compression
- Real-time collaboration
- Enhanced security

## Development Guidelines

### Code Organization
- Modular component design
- Clear separation of concerns
- Comprehensive error handling
- Extensive logging and monitoring

### Testing Strategy
- Unit tests for all components
- Integration tests for workflows
- Performance benchmarks
- User acceptance testing

### Documentation
- API documentation
- Architecture diagrams
- User guides
- Troubleshooting guides
