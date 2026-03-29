# GCO Golf Club 2026

This repository tracks the scoring, announcements, and match management for the 2026 GCO Golf Season with a modern, multi-page Streamlit dashboard.

## 🎯 Live Dashboard

**📊 [Interactive Statistics Dashboard](http://localhost:8501)** - Run locally for full interactive experience

**📈 [Google Sheets Data](https://docs.google.com/spreadsheets/d/1ZvtWd8zHMI0k2GQGMWhtFHl5xuDbciOW/htmlview)** - View raw data

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (Recommended package manager)

### Installation & Setup (Recommended with uv)

1. **Clone the repository:**

```bash
git clone https://github.com/ly2xxx/gco.git
cd gco
```

2. **Run the application directly (uv handles everything):**

```bash
uv run streamlit run streamlit_app.py
```

3. **Access the dashboard:**
   - Open your browser and navigate to `http://localhost:8501`
   - The dashboard provides links to 📢 Announcements, 📅 Events, 🏆 League, 🥊 Cup, and 🤝 Team Match.

### Traditional Installation (pip)

### Alternative Installation (with virtual environment)

```bash
# Create virtual environment
python -m venv gco_env

# Activate virtual environment
# On Windows:
gco_env\Scripts\activate
# On macOS/Linux:
source gco_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run streamlit_app.py
```

## 📱 Dashboard Features

### 🏠 Overview Page

- **League Statistics**: Total players, games, average scores
- **Tournament Status**: Quick view of all tournament leaderboards
- **Key Metrics**: Real-time statistics dashboard

### 👤 Player Statistics

- **Individual Performance**: Detailed stats for each player
- **Performance Trends**: Interactive charts showing score progression
- **Detailed Metrics**: Scoring statistics, consistency analysis
- **Game History**: Complete record of all games played

### 🏆 Tournament Analysis

- **Tournament Leaderboards**: Rankings for each tournament
- **Interactive Charts**: Visual analysis of tournament performance
- **Comparative Analysis**: Top performers by tournament

### ⚖️ Player Comparison

- **Multi-Player Analysis**: Compare 2-6 players side by side
- **Performance Metrics**: Average scores, birdies, consistency
- **Visual Comparisons**: Interactive charts and tables

### 📊 Live Data View

- **Raw Data Access**: View and filter the complete dataset
- **Export Functionality**: Download filtered data as CSV
- **Real-time Updates**: Automatic refresh from Google Sheets

Run the comprehensive test suite:

```bash
# Run all tests using uv
uv run pytest test_streamlit_app.py -v

# Run with coverage report
uv run pytest test_streamlit_app.py --cov=streamlit_app --cov-report=html
```

### Test Coverage

- ✅ Data loading and processing
- ✅ Player statistics calculations
- ✅ Tournament analysis functions
- ✅ Data validation and edge cases
- ✅ Integration workflows

## 🏌️ League Information

### Current Season Tournaments

| Tournament                          | Period                  | Status      |
| ----------------------------------- | ----------------------- | ----------- |
| **提提卡卡杯 (Titicaca Cup)** | April 1 - May 31        | 🟢 Active   |
| **暖男杯 (Warm Man Cup)**     | June 1 - July 31        | 🟡 Upcoming |
| **凯尔特人杯 (Celtic Cup)**   | August 1 - September 15 | 🔴 Upcoming |

### Players (12 Total)

- 刘北南 | Jacky | 赵鲲 | 杨子初
- Neo | 徐峥 | 杨明 | 曹振波
- 李扬 | 王文龙 | 曾诚 | Justin

### Statistics Tracked

- **Scoring**: Net scores (+/-), best/worst rounds
- **Performance**: Birdies (B), Pars (P), Bogeys (BO), Double Bogeys (DB)
- **Analysis**: Consistency, trends, rankings
- **Competition**: Head-to-head matches, team results

## 🛠️ Technical Details

### Application Architecture

```
gco/
├── streamlit_app.py          # Main Dashboard Directory / Entrypoint
├── pages/                    # Multi-page dashboard modules
│   ├── 1_📢_Announcements.py
│   ├── 2_📅_Events.py
│   ├── 3_🏆_League.py
│   ├── 4_🥊_Cup.py
│   └── 5_🤝_Team.py
├── data/                     # Local JSON/CSV data storage
├── pyproject.toml            # uv project configuration
├── requirements.txt          # Shared dependencies
├── .streamlit/
│   └── config.toml           # Streamlit configuration
└── README.md                 # This file
```

### Dependencies

- **Streamlit**: Web application framework
- **Pandas**: Data manipulation and analysis
- **Plotly**: Interactive visualization
- **NumPy**: Numerical computing
- **Requests**: HTTP library for Google Sheets API
- **Pytest**: Testing framework

### Data Source

The application automatically fetches data from the Google Sheets document and provides fallback sample data for development/testing purposes.

## 🔧 Configuration

### Streamlit Configuration

The `.streamlit/config.toml` file contains:

- Custom theme colors (Golf green primary color)
- Server settings for optimal performance
- Browser configuration for security

### Environment Variables (Optional)

```bash
# Set custom port (default: 8501)
export STREAMLIT_PORT=8080

# Set server address (default: localhost)
export STREAMLIT_ADDRESS=0.0.0.0
```

## 🚨 Troubleshooting

### Common Issues

1. **Port already in use:**

```bash
streamlit run streamlit_app.py --server.port 8502
```

2. **Missing dependencies:**

```bash
pip install --upgrade -r requirements.txt
```

3. **Google Sheets access issues:**

   - Check internet connection
   - Verify Google Sheets URL is accessible
   - Application will use sample data as fallback
4. **Performance issues:**

   - Clear browser cache
   - Restart the Streamlit server
   - Check system resources

## 📈 Future Enhancements

- [ ] Real-time notifications for score updates
- [ ] Mobile-optimized responsive design
- [ ] Advanced analytics and predictions
- [ ] Export reports to PDF
- [ ] Integration with golf course APIs
- [ ] Player photo galleries
- [ ] Weather data correlation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues or questions:

- Create an issue in the GitHub repository
- Contact the development team
- Check the troubleshooting section above

Inspired by [Shaws Bar Golf Club Email](https://sh1.sendinblue.com/an3yjhki9xpfe.html?t=1774539231231)

---

**GCO Golf Club 2026** | Made with ❤️ using Streamlit & uv | Last updated: March 2026
