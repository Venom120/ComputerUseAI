# ComputerUseAI User Guide

## Getting Started

### First Launch

1. **Install Dependencies**
   - Install Tesseract OCR for your platform
   - Ensure Python 3.8+ is installed
   - Install required Python packages

2. **Download Models**
   ```bash
   python tools/model_setup.py
   ```
   This downloads:
   - Whisper model for speech recognition (~142MB)
   - Phi-3 Mini model for AI processing (~2.3GB)

3. **Launch Application**
   ```bash
   python -m src.main
   ```

### Initial Setup

1. **Grant Permissions**
   - Allow screen recording access
   - Allow microphone access
   - Allow accessibility permissions (for automation)

2. **Configure Settings**
   - Go to Settings tab
   - Adjust capture quality (default: 75%)
   - Set storage limits (default: 1GB)
   - Configure privacy settings

3. **Start Learning**
   - Click "Start Recording" in Dashboard
   - Perform your normal tasks
   - Let the AI observe and learn

## Core Features

### Dashboard

The main control center showing:
- **System Status**: Recording state and system health
- **Statistics**: Storage usage, learned workflows, capture count
- **Processing Progress**: Current AI analysis status
- **Quick Controls**: Start/stop recording, run workflows

### Workflows Tab

**Viewing Detected Workflows**:
- List of learned workflow patterns
- Success rate and confidence scores
- Last used timestamps
- Workflow descriptions

**Managing Workflows**:
- **Create New**: Manually define a workflow
- **Edit**: Modify existing workflow steps
- **Delete**: Remove unwanted workflows
- **Run**: Execute workflow manually

**Workflow Details**:
- Step-by-step breakdown
- Required applications
- Expected outcomes
- Automation settings

### Timeline Tab

**Activity History**:
- Chronological view of all captures
- Filter by date, application, or type
- Search through recorded sessions
- Export timeline data

**Session Management**:
- View detailed session information
- Playback screen recordings
- Listen to audio transcripts
- Analyze workflow patterns

### Automation Tab

**Automation Controls**:
- **Enable Automation**: Turn on automatic execution
- **Confidence Threshold**: Set minimum confidence (50-100%)
- **Execution Log**: Monitor automation activity
- **Error Handling**: Configure retry and fallback behavior

**Automation Settings**:
- **Auto-trigger**: Automatically run workflows when detected
- **Manual Approval**: Require user confirmation
- **Scheduling**: Set specific times for automation
- **Notifications**: Configure system notifications

### Settings Tab

**Capture Settings**:
- **FPS**: Frames per second (1-10, default: 3)
- **Quality**: Image compression (10-100%, default: 75%)
- **Storage Limit**: Maximum storage usage (100MB-10GB)
- **Resolution Cap**: Maximum capture resolution

**Privacy Settings**:
- **Excluded Apps**: Applications to never record
- **Sensitive Windows**: Window titles to exclude
- **Data Retention**: How long to keep recordings
- **Encryption**: Enable encrypted storage

**Performance Settings**:
- **Processing Priority**: CPU usage allocation
- **Memory Limits**: RAM usage limits
- **Background Processing**: When to run AI analysis
- **Model Selection**: Choose AI model size

## Learning Workflows

### How It Works

1. **Observation Phase**
   - Record your normal work patterns
   - AI analyzes screen content and actions
   - Identifies repetitive sequences
   - Builds pattern recognition models

2. **Learning Phase**
   - AI processes captured data
   - Extracts workflow patterns
   - Generates step-by-step descriptions
   - Calculates confidence scores

3. **Validation Phase**
   - Review detected workflows
   - Test automation manually
   - Provide feedback to improve accuracy
   - Enable automation for verified workflows

### Best Practices

**For Better Learning**:
- Perform tasks consistently
- Use clear, predictable patterns
- Avoid interruptions during recording
- Repeat workflows multiple times

**For Better Automation**:
- Test workflows manually first
- Start with simple, repetitive tasks
- Monitor automation execution
- Provide feedback when needed

### Workflow Types

**Data Entry Workflows**:
- Form filling
- Spreadsheet data entry
- Database record creation
- File organization

**Navigation Workflows**:
- Application switching
- Menu navigation
- File opening/saving
- Web browsing patterns

**Communication Workflows**:
- Email composition
- Message sending
- Document sharing
- Meeting scheduling

## Automation

### Enabling Automation

1. **Prerequisites**
   - At least one learned workflow
   - Confidence threshold set
   - Automation enabled in settings

2. **Activation**
   - Go to Automation tab
   - Check "Enable Automation"
   - Set confidence threshold (80% recommended)
   - Monitor execution log

### Automation Modes

**Automatic Mode**:
- AI detects workflow patterns
- Automatically executes when confident
- No user intervention required
- Best for highly repetitive tasks

**Semi-Automatic Mode**:
- AI detects patterns
- Asks for user confirmation
- User can approve or modify
- Good for variable workflows

**Manual Mode**:
- User triggers workflows manually
- Full control over execution
- Good for testing and learning
- Recommended for beginners

### Monitoring Automation

**Execution Log**:
- Real-time automation activity
- Success/failure notifications
- Error messages and solutions
- Performance metrics

**Intervention Options**:
- Pause automation
- Skip current step
- Modify workflow
- Stop execution

## Privacy & Security

### Data Protection

**Local Processing**:
- All AI processing on your device
- No data sent to external servers
- Models run completely offline
- No internet required for core functionality

**Data Storage**:
- Encrypted storage option
- Automatic data cleanup
- User-controlled retention
- One-click data deletion

### Privacy Controls

**Application Exclusion**:
- Blacklist sensitive applications
- Banking and financial apps
- Messaging and communication
- Personal document viewers

**Window Filtering**:
- Exclude specific window titles
- Password field detection
- Sensitive content recognition
- Custom privacy rules

**Data Management**:
- View all stored data
- Export personal information
- Delete specific recordings
- Complete data reset

## Troubleshooting

### Common Issues

**Application Won't Start**:
- Check Python version (3.8+ required)
- Verify all dependencies installed
- Check system permissions
- Review error logs

**Poor Workflow Detection**:
- Increase recording time
- Perform tasks more consistently
- Adjust confidence threshold
- Check privacy settings

**Automation Failures**:
- Verify application permissions
- Check UI element changes
- Update workflow steps
- Test manually first

**Performance Issues**:
- Reduce capture quality
- Lower FPS setting
- Increase storage limits
- Close other applications

### Getting Help

**Log Files**:
- Located in `data/logs/`
- Detailed error information
- Performance metrics
- Debug information

**Support Resources**:
- GitHub Issues for bugs
- GitHub Discussions for questions
- Wiki for documentation
- Community forums

**Diagnostic Tools**:
- System information collection
- Performance monitoring
- Error reporting tools
- Health check utilities

## Advanced Usage

### Custom Workflows

**Manual Creation**:
- Define step-by-step actions
- Set timing and delays
- Configure error handling
- Test and validate

**Workflow Templates**:
- Save common patterns
- Share with team members
- Version control
- Backup and restore

### Integration Options

**API Access**:
- REST API for external tools
- Webhook notifications
- Custom integrations
- Third-party plugins

**Export/Import**:
- Workflow sharing
- Settings backup
- Data migration
- Team collaboration

### Performance Tuning

**Resource Optimization**:
- CPU usage monitoring
- Memory management
- Storage optimization
- Network usage

**Model Configuration**:
- Model size selection
- Processing quality
- Speed vs accuracy
- Hardware utilization

## Tips & Tricks

### Efficiency Tips

**Better Recording**:
- Use consistent window sizes
- Avoid rapid clicking
- Clear desktop clutter
- Minimize distractions

**Faster Learning**:
- Repeat workflows 3-5 times
- Use descriptive file names
- Organize tasks logically
- Provide clear feedback

**Smoother Automation**:
- Test workflows thoroughly
- Start with simple tasks
- Monitor execution closely
- Adjust settings gradually

### Power User Features

**Keyboard Shortcuts**:
- Quick start/stop recording
- Toggle automation on/off
- Open specific tabs
- Run workflows instantly

**Advanced Settings**:
- Custom model configurations
- Fine-tuned parameters
- Experimental features
- Debugging options

**Automation Scripts**:
- Custom automation logic
- Conditional execution
- Complex workflows
- Integration with other tools
