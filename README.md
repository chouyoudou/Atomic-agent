# ASE MCP Server

<p align="center">
  <img src="https://img.shields.io/badge/ASE-Atomic%20Simulation%20Environment-blue.svg" alt="ASE"/>
  <img src="https://img.shields.io/badge/MCP-Model%20Context%20Protocol-green.svg" alt="MCP"/>
  <img src="https://img.shields.io/badge/React-18-blue.svg" alt="React"/>
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue.svg" alt="Python"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"/>
</p>

**A powerful MCP server for atomic structure creation, modification, and real-time 3D visualization.**

---

## ✨ Core Features

- 🧬 **Advanced Structure Operations** | 12+ modification operations for atomic structures
- 🤖 **Full MCP Protocol Support** | Compatible with AI agents (Claude, etc.)
- 🌐 **Real-time 3D Visualization** | Professional molecular visualization with 3Dmol.js
- 📡 **WebSocket Communication** | Real-time updates and notifications
- 🔄 **Session Management** | Multi-session support with operation history
- 🏗️ **Flexible Deployment** | Integrated or separated frontend/backend
- 📚 **Complete API** | RESTful API with auto-generated documentation
- ✅ **Production-Ready Validation** | 119 tests passing, LLM-optimized output ([docs](docs/validation/README.md))

## 🚀 Quick Start

### One-Click Launch

```bash
# Clone and start
git clone <repo-url>
cd ASE_MCP

# Interactive startup script
./scripts/start.sh
```

### Manual Setup

**Backend (API Server):**
```bash
pip install -r requirements.txt
python server/main.py --api-only
```

**Frontend (React App):**
```bash
cd client && npm install && npm start
```

**Access Points:**
- 🌐 Frontend: http://localhost:3000
- 📖 API Docs: http://localhost:8000/docs
- 🔗 WebSocket: ws://localhost:8001

## 📋 Requirements

- **Python:** 3.8+
- **Node.js:** 16+ (for frontend)
- **Redis:** Optional (has fallback)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LLM Clients   │    │  Web Frontend   │    │   API Clients   │
│  (Claude etc.)  │    │    (React)      │    │   (curl/SDK)    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │ MCP                  │ HTTP/WS              │ HTTP
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ASE MCP Server                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ MCP Handler │  │ Web Server  │  │    WebSocket Server     │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         └─────────────────┼─────────────────────┘                │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │                 ASE Core Engine                             │ │
│  │  • Structure Creation  • Modification  • Calculation       │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────▼─────────────┐
                │     Storage Layer         │
                │  Redis + File System     │
                └───────────────────────────┘
```

## 💎 Usage Examples

### Creating Structures

**Via API:**
```bash
curl -X POST http://localhost:8000/api/structures \
  -H "Content-Type: application/json" \
  -d '{
    "type": "bulk",
    "formula": "Cu",
    "structure": "fcc",
    "size": [2, 2, 2]
  }'
```

**Via MCP (Claude):**
```
Please create a 2x2x2 copper FCC structure using ASE
```

### Diamond ↔ Graphite Transformation

```bash
# 1. Create diamond
curl -X POST .../structures -d '{"type":"bulk","formula":"C","structure":"diamond"}'

# 2. Transform to graphite
curl -X POST .../structures/{session_id}/modify -d '{
  "operation": "replace_atoms",
  "parameters": {
    "symbols": ["C", "C", "C", "C"],
    "positions": [[0,0,0], [1.42,0,0], [0.71,1.23,0], [2.13,1.23,0]],
    "cell": [[2.84,0,0], [0,2.46,0], [0,0,3.35]]
  }
}'
```

## 🔧 Modification Operations

| Operation | Description | Parameters |
|-----------|-------------|------------|
| `rotate` | Rotate structure | `angle`, `axis` |
| `translate` | Move structure | `vector` |
| `scale` | Scale structure | `factor` |
| `supercell` | Create supercell | `size` |
| `modify_cell` | Change unit cell | `cell`, `scale_atoms` |
| `modify_positions` | Update atom positions | `positions`, `indices` |
| `replace_atoms` | Complete replacement | `symbols`, `positions`, `cell` |
| `add_atom` | Add single atom | `symbol`, `position` |
| `remove_atoms` | Remove atoms | `indices` |
| `change_species` | Change atom types | `indices`, `symbols` |
| `duplicate_atoms` | Copy atoms | `indices`, `offset` |
| `create_vacancy` | Create defects | `indices` |

## 📂 Project Structure

```
ASE_MCP/
├── docs/                    # 📚 Documentation
│   ├── API_REFERENCE.md     # Complete API reference
│   ├── LLM_TRAINING_GUIDE.md # LLM fine-tuning guide
│   ├── QUICK_START.md       # Quick start guide
│   └── ARCHITECTURE.md      # System architecture
├── examples/                # 💡 Usage examples
│   ├── api_examples/        # HTTP API examples
│   └── mcp_examples/        # MCP protocol examples
├── scripts/                 # 🛠️ Utility scripts
│   ├── start.sh            # Interactive startup
│   ├── start_backend.sh    # Backend only
│   └── start_frontend.sh   # Frontend only
├── server/                  # 🐍 Python backend
│   ├── core/               # Core ASE engine
│   ├── handlers/           # MCP & HTTP handlers
│   ├── models/             # Data models
│   └── utils/              # Utilities
├── client/                  # ⚛️ React frontend
│   └── src/
│       ├── components/     # React components
│       └── services/       # API services
├── docker/                  # 🐳 Docker configuration
│   ├── docker-compose.yml
│   ├── Dockerfile.server
│   └── Dockerfile.client
└── tests/                   # 🧪 Test suites
```

## 🔗 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/structures` | Create new structure |
| `GET` | `/api/structures/{id}` | Get structure info |
| `POST` | `/api/structures/{id}/modify` | Modify structure |
| `GET` | `/api/sessions` | List all sessions |
| `DELETE` | `/api/sessions/{id}` | Delete session |
| `GET` | `/docs` | API documentation |
| `GET` | `/health` | Health check |

## 🧑‍💻 For Developers

### Adding New Features

1. **Core Logic:** Add to `server/core/ase_engine.py`
2. **API Endpoint:** Add to `server/web_server.py`
3. **MCP Tool:** Add to `server/handlers/mcp_handler.py`
4. **Frontend:** Add to `client/src/components/`

### Running Examples

```bash
# Structure creation
python examples/api_examples/create_structures.py

# Structure modification
python examples/api_examples/modify_structures.py

# Crystal transformations
python examples/api_examples/transform_crystals.py
```

## 🤖 For LLM Training

See comprehensive guide: [`docs/LLM_TRAINING_GUIDE.md`](docs/LLM_TRAINING_GUIDE.md)

**Key Points:**
- Complete MCP tool specifications
- Training data formats
- System prompt templates
- Error handling patterns

## 🚢 Deployment

### Docker Compose

```bash
cd docker
docker-compose up -d
```

### Manual Deployment

**Production Backend:**
```bash
pip install -r requirements.txt
gunicorn server.main:app --bind 0.0.0.0:8000
```

**Production Frontend:**
```bash
cd client && npm run build
# Serve with nginx or your preferred web server
```

## 🐛 Troubleshooting

### Common Issues

**Port conflicts:**
```bash
# Kill existing processes
lsof -ti:8000,8001,3000 | xargs kill -9
```

**Redis connection failed:**
```bash
# System automatically falls back to memory storage
# Optional: Start Redis manually
redis-server
```

**Frontend can't connect to backend:**
```bash
# Check frontend configuration
cat client/.env
# Should contain:
# REACT_APP_API_BASE_URL=http://localhost:8000
# REACT_APP_WEBSOCKET_URL=ws://localhost:8001
```

## 📖 Documentation

- 📋 [Quick Start Guide](docs/QUICK_START.md) - Get running in 5 minutes
- 🔧 [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- 🤖 [LLM Training Guide](docs/LLM_TRAINING_GUIDE.md) - Fine-tune your AI models
- 🏗️ [Architecture Guide](docs/ARCHITECTURE.md) - System design details
- 💻 [Claude MCP Setup](docs/CLAUDE.md) - Configure Claude integration
- ✅ [Validation System](docs/validation/README.md) - Production-ready validation (119 tests ✅)

## ✅ Validation System

**Status**: 🚀 Production Ready | **Version**: 1.0.0 | **Tests**: 119/119 ✅

The ASE MCP Server includes a comprehensive validation system for crystal structure analysis and constraint checking, specifically optimized for LLM agent usage.

### Key Features

- **Geometric Analysis**: Dimensionality, coordination numbers, bond lengths/angles, symmetry detection
- **5 Constraint Validators**: Angle, Lattice, Symmetry, Freezing, Auto-suggester
- **3-Level Feedback**: passed/warning/violation with severity percentages
- **LLM-Optimized Output**: 2-3 decimal precision, actionable suggestions, clear categorization

### Test Coverage

| Phase | Tests | Status | Description |
|-------|-------|--------|-------------|
| Phase 0 | 13 | ✅ | Core geometric analysis (Robocrys integration) |
| Phase 1 | 16 | ✅ | Tolerance-based validation (3-level feedback) |
| Phase 2 | 9 | ✅ | Advanced constraints (5 validators) |
| Phase 3 | 59 | ✅ | Corner cases and edge structures |
| Phase 3.5 | 22 | ✅ | LLM usability validation |
| **Total** | **119** | **✅** | **100% passing** |

### Quick Example

```python
from server.core.validators import GeometryAnalyzer, ConstraintSuggester

# Analyze structure
analyzer = GeometryAnalyzer()
result = analyzer.analyze_structure(atoms)

# Auto-generate constraints
suggester = ConstraintSuggester()
suggestions = suggester.suggest_constraints(atoms, result["observations"])

print(suggestions["constraints"])  # Recommended constraints
print(suggestions["rationale"])    # Why these constraints
```

### Documentation

- **📊 [Validation Summary](docs/validation/VALIDATION_SUMMARY.md)** - Comprehensive overview
- **📚 [Validation Index](docs/validation/README.md)** - Complete documentation index
- **🧪 [Test Instructions](docs/validation/TEST_INSTRUCTIONS.md)** - How to run tests

**Key Achievements**:
- ✅ 119/119 tests passing (100% success rate)
- ✅ LLM-friendly output (numeric precision, actionable feedback)
- ✅ Real-world validation (Materials Project structures, BaTiO3 phase transitions)
- ✅ 0 crashes on edge cases (robust error handling)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [ASE (Atomic Simulation Environment)](https://wiki.fysik.dtu.dk/ase/) - Core atomic simulation library
- [3Dmol.js](https://3dmol.csb.pitt.edu/) - 3D molecular visualization
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [React](https://reactjs.org/) - Frontend framework

---

<p align="center">
  <b>Built with ❤️ for the atomic simulation community</b><br>
  🧬 Create • 🔧 Modify • 👁️ Visualize • 🚀 Deploy
</p>