"""
GCO Golf League Statistics Dashboard
A comprehensive Streamlit application for displaying golf league statistics
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from io import StringIO
import re

# Page configuration
st.set_page_config(
    page_title="GCO Golf League 2025",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .tournament-header {
        font-size: 1.5rem;
        color: #1f77b4;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_gco_data():
    """Load data from Google Sheets"""
    try:
        # Convert Google Sheets view URL to CSV export URL
        sheet_id = "1ZvtWd8zHMI0k2GQGMWhtFHl5xuDbciOW"
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
        
        # Read the CSV data
        response = requests.get(csv_url)
        response.raise_for_status()
        
        # Parse CSV content
        csv_content = StringIO(response.text)
        df = pd.read_csv(csv_content)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        # Return sample data for demonstration
        return create_sample_data()

def create_sample_data():
    """Create sample data structure based on the actual GCO league format"""
    players = ['刘北南', 'Jacky', '赵鲲', '杨子初', 'Neo', '徐峥', '杨明', 
               '曹振波', '李扬', '王文龙', '曾诚', 'Justin']
    
    # Sample tournament data
    tournaments = {
        '提提卡卡杯': {'period': '01/04 - 31/05', 'games': ['Game 1', 'Game 2', 'Game 3', 'Game 4']},
        '暖男杯': {'period': '01/06 - 31/07', 'games': ['Game 5', 'Game 6', 'Game 7', 'Game 8']},
        '凯尔特人杯': {'period': '01/08 - 15/09', 'games': ['Game 9', 'Game 10', 'Game 11', 'Game 12']}
    }
    
    data = []
    for player in players:
        for tournament in tournaments:
            for game in tournaments[tournament]['games']:
                data.append({
                    'Player': player,
                    'Tournament': tournament,
                    'Game': game,
                    'Net_Score': np.random.randint(-15, 20),
                    'Birdies': np.random.randint(0, 5),
                    'Pars': np.random.randint(5, 15),
                    'Bogeys': np.random.randint(0, 8),
                    'Double_Bogeys': np.random.randint(0, 4)
                })
    
    return pd.DataFrame(data)

def calculate_player_stats(df, player_name):
    """Calculate comprehensive statistics for a player"""
    player_data = df[df['Player'] == player_name]
    
    if player_data.empty:
        return None
    
    stats = {
        'total_games': len(player_data),
        'avg_net_score': player_data['Net_Score'].mean(),
        'best_score': player_data['Net_Score'].min(),
        'worst_score': player_data['Net_Score'].max(),
        'total_birdies': player_data['Birdies'].sum(),
        'total_pars': player_data['Pars'].sum(),
        'total_bogeys': player_data['Bogeys'].sum(),
        'total_double_bogeys': player_data['Double_Bogeys'].sum(),
        'birdie_rate': player_data['Birdies'].mean(),
        'consistency': player_data['Net_Score'].std()
    }
    
    return stats

def create_player_performance_chart(df, player_name):
    """Create a performance chart for a specific player"""
    player_data = df[df['Player'] == player_name].copy()
    player_data = player_data.sort_values('Game')
    
    fig = go.Figure()
    
    # Add net score line
    fig.add_trace(go.Scatter(
        x=player_data['Game'],
        y=player_data['Net_Score'],
        mode='lines+markers',
        name='Net Score',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8)
    ))
    
    # Add zero line for reference
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Par")
    
    fig.update_layout(
        title=f"{player_name} - Performance Trend",
        xaxis_title="Game",
        yaxis_title="Net Score",
        hovermode='x unified',
        template="plotly_white"
    )
    
    return fig

def create_tournament_leaderboard(df, tournament_name):
    """Create leaderboard for a specific tournament"""
    tournament_data = df[df['Tournament'] == tournament_name]
    
    leaderboard = tournament_data.groupby('Player').agg({
        'Net_Score': ['sum', 'mean', 'count'],
        'Birdies': 'sum',
        'Pars': 'sum',
        'Bogeys': 'sum',
        'Double_Bogeys': 'sum'
    }).round(2)
    
    # Flatten column names
    leaderboard.columns = ['Total_Score', 'Avg_Score', 'Games_Played', 
                          'Total_Birdies', 'Total_Pars', 'Total_Bogeys', 'Total_Double_Bogeys']
    
    leaderboard = leaderboard.sort_values('Total_Score')
    leaderboard.reset_index(inplace=True)
    leaderboard['Rank'] = range(1, len(leaderboard) + 1)
    
    return leaderboard

def create_comparison_chart(df, players_to_compare):
    """Create comparison chart for multiple players"""
    comparison_data = []
    
    for player in players_to_compare:
        stats = calculate_player_stats(df, player)
        if stats:
            comparison_data.append({
                'Player': player,
                'Avg_Net_Score': stats['avg_net_score'],
                'Total_Birdies': stats['total_birdies'],
                'Birdie_Rate': stats['birdie_rate'],
                'Consistency': stats['consistency']
            })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Average Net Score', 'Total Birdies', 'Birdie Rate per Game', 'Consistency (Lower is Better)'),
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Add traces
    fig.add_trace(go.Bar(x=comparison_df['Player'], y=comparison_df['Avg_Net_Score'], 
                        name='Avg Net Score', marker_color='lightblue'), row=1, col=1)
    fig.add_trace(go.Bar(x=comparison_df['Player'], y=comparison_df['Total_Birdies'], 
                        name='Total Birdies', marker_color='lightgreen'), row=1, col=2)
    fig.add_trace(go.Bar(x=comparison_df['Player'], y=comparison_df['Birdie_Rate'], 
                        name='Birdie Rate', marker_color='orange'), row=2, col=1)
    fig.add_trace(go.Bar(x=comparison_df['Player'], y=comparison_df['Consistency'], 
                        name='Consistency', marker_color='lightcoral'), row=2, col=2)
    
    fig.update_layout(height=600, showlegend=False, template="plotly_white")
    
    return fig

def main():
    """Main application function"""
    
    # Header
    st.markdown('<h1 class="main-header">⛳ GCO Golf League 2025 Statistics</h1>', 
                unsafe_allow_html=True)
    
    # Load data
    with st.spinner("Loading league data..."):
        df = load_gco_data()
    
    if df.empty:
        st.error("No data available. Please check the Google Sheets connection.")
        return
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a view:",
        ["Overview", "Player Statistics", "Tournament Analysis", "Player Comparison", "Live Data"]
    )
    
    if page == "Overview":
        st.header("League Overview")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_players = df['Player'].nunique()
            st.metric("Total Players", total_players)
        
        with col2:
            total_games = df['Game'].nunique()
            st.metric("Total Games", total_games)
        
        with col3:
            avg_score = df['Net_Score'].mean()
            st.metric("Average Net Score", f"{avg_score:.1f}")
        
        with col4:
            total_birdies = df['Birdies'].sum()
            st.metric("Total Birdies", total_birdies)
        
        # Tournament overview
        st.subheader("Tournament Status")
        tournaments = ['提提卡卡杯', '暖男杯', '凯尔特人杯']
        
        for tournament in tournaments:
            with st.expander(f"{tournament} Tournament"):
                leaderboard = create_tournament_leaderboard(df, tournament)
                st.dataframe(leaderboard, use_container_width=True)
    
    elif page == "Player Statistics":
        st.header("Individual Player Statistics")
        
        # Player selection
        players = sorted(df['Player'].unique())
        selected_player = st.selectbox("Select a player:", players)
        
        if selected_player:
            stats = calculate_player_stats(df, selected_player)
            
            if stats:
                # Display key metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Average Net Score", f"{stats['avg_net_score']:.1f}")
                
                with col2:
                    st.metric("Best Score", stats['best_score'])
                
                with col3:
                    st.metric("Total Birdies", stats['total_birdies'])
                
                with col4:
                    st.metric("Games Played", stats['total_games'])
                
                # Performance chart
                st.subheader(f"{selected_player} - Performance Trend")
                fig = create_player_performance_chart(df, selected_player)
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed statistics
                st.subheader("Detailed Statistics")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Scoring Statistics:**")
                    st.write(f"• Best Score: {stats['best_score']}")
                    st.write(f"• Worst Score: {stats['worst_score']}")
                    st.write(f"• Average: {stats['avg_net_score']:.1f}")
                    st.write(f"• Consistency (σ): {stats['consistency']:.1f}")
                
                with col2:
                    st.write("**Shot Statistics:**")
                    st.write(f"• Total Birdies: {stats['total_birdies']}")
                    st.write(f"• Total Pars: {stats['total_pars']}")
                    st.write(f"• Total Bogeys: {stats['total_bogeys']}")
                    st.write(f"• Birdie Rate: {stats['birdie_rate']:.1f} per game")
    
    elif page == "Tournament Analysis":
        st.header("Tournament Analysis")
        
        tournament = st.selectbox("Select Tournament:", 
                                ['提提卡卡杯', '暖男杯', '凯尔特人杯'])
        
        if tournament:
            st.subheader(f"{tournament} Leaderboard")
            leaderboard = create_tournament_leaderboard(df, tournament)
            
            # Display leaderboard
            st.dataframe(leaderboard, use_container_width=True)
            
            # Tournament statistics chart
            fig = px.bar(leaderboard.head(10), 
                        x='Player', y='Total_Score',
                        title=f"{tournament} - Top 10 Players by Total Score",
                        color='Total_Score',
                        color_continuous_scale='RdYlGn_r')
            
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    elif page == "Player Comparison":
        st.header("Player Comparison")
        
        players = sorted(df['Player'].unique())
        selected_players = st.multiselect(
            "Select players to compare (2-6 players):",
            players,
            default=players[:3] if len(players) >= 3 else players
        )
        
        if len(selected_players) >= 2:
            fig = create_comparison_chart(df, selected_players)
            st.plotly_chart(fig, use_container_width=True)
            
            # Comparison table
            st.subheader("Detailed Comparison")
            comparison_data = []
            
            for player in selected_players:
                stats = calculate_player_stats(df, player)
                if stats:
                    comparison_data.append({
                        'Player': player,
                        'Avg Score': f"{stats['avg_net_score']:.1f}",
                        'Best Score': stats['best_score'],
                        'Total Birdies': stats['total_birdies'],
                        'Birdie Rate': f"{stats['birdie_rate']:.1f}",
                        'Games Played': stats['total_games']
                    })
            
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True)
        else:
            st.info("Please select at least 2 players for comparison.")
    
    elif page == "Live Data":
        st.header("Live Data View")
        st.info("This page shows the raw data from the Google Sheets")
        
        # Display filters
        col1, col2 = st.columns(2)
        
        with col1:
            tournament_filter = st.multiselect(
                "Filter by Tournament:",
                df['Tournament'].unique(),
                default=df['Tournament'].unique()
            )
        
        with col2:
            player_filter = st.multiselect(
                "Filter by Player:",
                sorted(df['Player'].unique()),
                default=sorted(df['Player'].unique())
            )
        
        # Apply filters
        filtered_df = df[
            (df['Tournament'].isin(tournament_filter)) &
            (df['Player'].isin(player_filter))
        ]
        
        # Display filtered data
        st.dataframe(filtered_df, use_container_width=True)
        
        # Data export
        if st.button("Download Filtered Data as CSV"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="gco_golf_data.csv",
                mime="text/csv"
            )
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**GCO Golf League 2025** | "
        "[View Full Data](https://docs.google.com/spreadsheets/d/1ZvtWd8zHMI0k2GQGMWhtFHl5xuDbciOW/htmlview) | "
        "Made with ❤️ using Streamlit"
    )

if __name__ == "__main__":
    main()
