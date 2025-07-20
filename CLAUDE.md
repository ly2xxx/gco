# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Streamlit-based golf league statistics dashboard** for the GCO Golf League 2025. The application displays comprehensive statistics, tournament analysis, and player comparisons for a 12-player golf league with three tournaments (提提卡卡杯, 暖男杯, 凯尔特人杯).

## Core Architecture

- **Single-file Streamlit app**: `streamlit_app.py` (420 lines) contains all application logic
- **Data source**: Google Sheets integration with fallback to sample data generation
- **Multi-page application**: Uses Streamlit selectbox navigation for 5 main sections:
  - Overview (league metrics, tournament status)
  - Player Statistics (individual performance analysis)
  - Tournament Analysis (leaderboards, rankings)
  - Player Comparison (multi-player analysis)
  - Live Data (raw data view with filtering)

## Essential Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application locally
streamlit run streamlit_app.py

# Run on custom port
streamlit run streamlit_app.py --server.port 8502

# Run comprehensive test suite
pytest test_streamlit_app.py -v

# Run tests with coverage
pytest test_streamlit_app.py --cov=streamlit_app --cov-report=html

# Lint code (as used in CI)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Test app syntax and imports
python -m py_compile streamlit_app.py
```

## Data Structure

The application expects DataFrame with columns:
- `Player`: Player names (12 total players including Chinese and English names)
- `Tournament`: Tournament names (提提卡卡杯, 暖男杯, 凯尔特人杯)
- `Game`: Individual game identifiers
- `Net_Score`: Golf net scores (integer, range typically -15 to +20)
- `Birdies`, `Pars`, `Bogeys`, `Double_Bogeys`: Shot statistics (non-negative integers)

## Key Functions

- `load_gco_data()`: Google Sheets integration with automatic fallback
- `create_sample_data()`: Generates test data for development
- `calculate_player_stats()`: Core statistics engine for individual players
- `create_tournament_leaderboard()`: Tournament ranking and aggregation
- `create_player_performance_chart()`: Plotly visualization for trends
- `create_comparison_chart()`: Multi-player comparison visualizations

## Testing Approach

Comprehensive test suite in `test_streamlit_app.py` with mocked Streamlit dependencies:
- **Data Processing Tests**: Sample data generation, data types, ranges
- **Player Statistics Tests**: Stats calculation, edge cases, missing data
- **Tournament Analysis Tests**: Leaderboard creation, ranking logic
- **Data Validation Tests**: NaN handling, duplicates, validation
- **Integration Tests**: Complete workflow testing
- **Mocked External Dependencies**: Streamlit, Plotly, requests for Google Sheets

## Configuration

- **Streamlit config**: `.streamlit/config.toml` with golf-themed colors (#2E8B57 primary)
- **CI/CD**: GitHub Actions testing on Python 3.8-3.11 with pytest, flake8, coverage
- **Dependencies**: Core stack is Streamlit, Pandas, Plotly, NumPy, Requests

## Development Notes

- The app gracefully handles Google Sheets connection failures by falling back to sample data
- All visualizations use Plotly for interactivity
- Caching is implemented with `@st.cache_data(ttl=300)` for data loading
- Chinese tournament names are used throughout - maintain this naming convention
- The app supports real-time data filtering and CSV export functionality