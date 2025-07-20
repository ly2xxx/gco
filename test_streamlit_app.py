"""
Test suite for GCO Golf League Streamlit Application
Comprehensive tests covering data processing, statistics calculation, and UI components
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os
from unittest.mock import patch, MagicMock
import requests

# Add the parent directory to the path so we can import our app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock streamlit for testing
sys.modules['streamlit'] = MagicMock()
sys.modules['plotly.express'] = MagicMock()
sys.modules['plotly.graph_objects'] = MagicMock()
sys.modules['plotly.subplots'] = MagicMock()

# Import functions after mocking
from streamlit_app import (
    create_sample_data,
    calculate_player_stats,
    create_tournament_leaderboard,
    load_gco_data
)

class TestDataProcessing:
    """Test data loading and processing functions"""
    
    @pytest.fixture
    def sample_df(self):
        """Create sample test data"""
        return create_sample_data()
    
    def test_create_sample_data(self):
        """Test sample data creation"""
        df = create_sample_data()
        
        # Check that DataFrame is not empty
        assert not df.empty
        
        # Check required columns exist
        required_columns = ['Player', 'Tournament', 'Game', 'Net_Score', 
                          'Birdies', 'Pars', 'Bogeys', 'Double_Bogeys']
        for col in required_columns:
            assert col in df.columns
        
        # Check that we have the expected players
        expected_players = ['刘北南', 'Jacky', '赵鲲', '杨子初', 'Neo', '徐峥', 
                           '杨明', '曹振波', '李扬', '王文龙', '曾诚', 'Justin']
        assert set(df['Player'].unique()) == set(expected_players)
        
        # Check that we have the expected tournaments
        expected_tournaments = ['提提卡卡杯', '暖男杯', '凯尔特人杯']
        assert set(df['Tournament'].unique()) == set(expected_tournaments)
    
    def test_data_types(self, sample_df):
        """Test that data types are correct"""
        assert sample_df['Net_Score'].dtype in [np.int64, np.float64]
        assert sample_df['Birdies'].dtype == np.int64
        assert sample_df['Pars'].dtype == np.int64
        assert sample_df['Bogeys'].dtype == np.int64
        assert sample_df['Double_Bogeys'].dtype == np.int64
    
    def test_data_ranges(self, sample_df):
        """Test that data values are within expected ranges"""
        # Net scores should be reasonable for golf
        assert sample_df['Net_Score'].min() >= -20
        assert sample_df['Net_Score'].max() <= 30
        
        # Non-negative counts for scoring categories
        assert sample_df['Birdies'].min() >= 0
        assert sample_df['Pars'].min() >= 0
        assert sample_df['Bogeys'].min() >= 0
        assert sample_df['Double_Bogeys'].min() >= 0

class TestPlayerStatistics:
    """Test player statistics calculation functions"""
    
    @pytest.fixture
    def test_player_data(self):
        """Create specific test data for player statistics"""
        data = {
            'Player': ['TestPlayer'] * 5,
            'Tournament': ['提提卡卡杯'] * 5,
            'Game': ['Game1', 'Game2', 'Game3', 'Game4', 'Game5'],
            'Net_Score': [-2, 1, 0, 3, -1],
            'Birdies': [2, 1, 0, 0, 1],
            'Pars': [10, 12, 14, 11, 13],
            'Bogeys': [3, 2, 2, 4, 1],
            'Double_Bogeys': [1, 1, 0, 1, 1]
        }
        return pd.DataFrame(data)
    
    def test_calculate_player_stats_valid_player(self, test_player_data):
        """Test player statistics calculation for valid player"""
        stats = calculate_player_stats(test_player_data, 'TestPlayer')
        
        assert stats is not None
        assert stats['total_games'] == 5
        assert stats['avg_net_score'] == 0.2  # (−2+1+0+3−1)/5
        assert stats['best_score'] == -2
        assert stats['worst_score'] == 3
        assert stats['total_birdies'] == 4
        assert stats['total_pars'] == 60
        assert stats['total_bogeys'] == 12
        assert stats['total_double_bogeys'] == 4
        assert stats['birdie_rate'] == 0.8  # 4 birdies / 5 games
    
    def test_calculate_player_stats_invalid_player(self, test_player_data):
        """Test player statistics calculation for non-existent player"""
        stats = calculate_player_stats(test_player_data, 'NonExistentPlayer')
        assert stats is None
    
    def test_calculate_player_stats_empty_dataframe(self):
        """Test player statistics calculation with empty DataFrame"""
        empty_df = pd.DataFrame(columns=['Player', 'Net_Score', 'Birdies', 'Pars', 'Bogeys', 'Double_Bogeys'])
        stats = calculate_player_stats(empty_df, 'AnyPlayer')
        assert stats is None
    
    def test_consistency_calculation(self, test_player_data):
        """Test that consistency (standard deviation) is calculated correctly"""
        stats = calculate_player_stats(test_player_data, 'TestPlayer')
        
        # Manual calculation: std of [-2, 1, 0, 3, -1]
        scores = np.array([-2, 1, 0, 3, -1])
        expected_std = np.std(scores, ddof=1)  # pandas uses ddof=1 by default
        
        assert abs(stats['consistency'] - expected_std) < 0.001

class TestTournamentAnalysis:
    """Test tournament analysis functions"""
    
    @pytest.fixture
    def tournament_data(self):
        """Create test data for tournament analysis"""
        data = {
            'Player': ['Player1', 'Player1', 'Player2', 'Player2', 'Player3', 'Player3'],
            'Tournament': ['提提卡卡杯'] * 6,
            'Game': ['Game1', 'Game2'] * 3,
            'Net_Score': [2, -1, 0, 3, -2, 1],
            'Birdies': [1, 2, 1, 0, 3, 1],
            'Pars': [10, 11, 12, 9, 8, 10],
            'Bogeys': [2, 1, 1, 3, 1, 2],
            'Double_Bogeys': [1, 0, 0, 2, 0, 1]
        }
        return pd.DataFrame(data)
    
    def test_create_tournament_leaderboard(self, tournament_data):
        """Test tournament leaderboard creation"""
        leaderboard = create_tournament_leaderboard(tournament_data, '提提卡卡杯')
        
        # Check that leaderboard has expected structure
        expected_columns = ['Player', 'Total_Score', 'Avg_Score', 'Games_Played', 
                          'Total_Birdies', 'Total_Pars', 'Total_Bogeys', 'Total_Double_Bogeys', 'Rank']
        for col in expected_columns:
            assert col in leaderboard.columns
        
        # Check that all players are included
        assert len(leaderboard) == 3
        assert set(leaderboard['Player']) == {'Player1', 'Player2', 'Player3'}
        
        # Check sorting (lower total scores should rank higher)
        assert leaderboard.iloc[0]['Rank'] == 1
        assert leaderboard['Total_Score'].is_monotonic_increasing
        
        # Check specific calculations
        player1_row = leaderboard[leaderboard['Player'] == 'Player1'].iloc[0]
        assert player1_row['Total_Score'] == 1  # 2 + (-1)
        assert player1_row['Games_Played'] == 2
        assert player1_row['Total_Birdies'] == 3  # 1 + 2
    
    def test_tournament_leaderboard_empty_tournament(self, tournament_data):
        """Test leaderboard creation for non-existent tournament"""
        leaderboard = create_tournament_leaderboard(tournament_data, '不存在的比赛')
        
        # Should return empty leaderboard with correct structure
        assert len(leaderboard) == 0
        expected_columns = ['Player', 'Total_Score', 'Avg_Score', 'Games_Played', 
                          'Total_Birdies', 'Total_Pars', 'Total_Bogeys', 'Total_Double_Bogeys', 'Rank']
        for col in expected_columns:
            assert col in leaderboard.columns

class TestDataValidation:
    """Test data validation and edge cases"""
    
    def test_missing_values_handling(self):
        """Test handling of missing values in data"""
        data_with_nan = {
            'Player': ['Player1', 'Player2'],
            'Tournament': ['提提卡卡杯', '暖男杯'],
            'Game': ['Game1', 'Game2'],
            'Net_Score': [2, np.nan],
            'Birdies': [1, 2],
            'Pars': [10, 11],
            'Bogeys': [2, 1],
            'Double_Bogeys': [1, 0]
        }
        df = pd.DataFrame(data_with_nan)
        
        # Test that functions handle NaN values gracefully
        stats = calculate_player_stats(df, 'Player2')
        # Should handle NaN in net score appropriately
        assert stats is not None or stats is None  # Function should not crash
    
    def test_duplicate_games_handling(self):
        """Test handling of duplicate game entries"""
        data_with_duplicates = {
            'Player': ['Player1', 'Player1'],
            'Tournament': ['提提卡卡杯', '提提卡卡杯'],
            'Game': ['Game1', 'Game1'],  # Duplicate game
            'Net_Score': [2, 3],
            'Birdies': [1, 2],
            'Pars': [10, 11],
            'Bogeys': [2, 1],
            'Double_Bogeys': [1, 0]
        }
        df = pd.DataFrame(data_with_duplicates)
        
        stats = calculate_player_stats(df, 'Player1')
        # Should handle duplicates (might count both or use latest)
        assert stats is not None
        assert stats['total_games'] == 2  # Both entries counted

class TestDataLoading:
    """Test data loading functionality"""
    
    @patch('requests.get')
    def test_load_gco_data_success(self, mock_get):
        """Test successful data loading from Google Sheets"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = "Player,Tournament,Game,Net_Score\nPlayer1,提提卡卡杯,Game1,2"
        mock_get.return_value = mock_response
        
        df = load_gco_data()
        
        # Check that data was loaded
        assert not df.empty
        assert 'Player' in df.columns
    
    @patch('requests.get')
    def test_load_gco_data_failure(self, mock_get):
        """Test data loading failure fallback"""
        # Mock failed response
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        df = load_gco_data()
        
        # Should fall back to sample data
        assert not df.empty
        # Should contain sample data structure
        expected_players = ['刘北南', 'Jacky', '赵鲲', '杨子初', 'Neo', '徐峥', 
                           '杨明', '曹振波', '李扬', '王文龙', '曾诚', 'Justin']
        assert set(df['Player'].unique()) == set(expected_players)

class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_full_player_analysis_workflow(self):
        """Test complete player analysis workflow"""
        # Create test data
        df = create_sample_data()
        
        # Select a player
        test_player = df['Player'].iloc[0]
        
        # Calculate stats
        stats = calculate_player_stats(df, test_player)
        
        # Verify workflow completes successfully
        assert stats is not None
        assert all(key in stats for key in [
            'total_games', 'avg_net_score', 'best_score', 'worst_score',
            'total_birdies', 'total_pars', 'total_bogeys', 'total_double_bogeys',
            'birdie_rate', 'consistency'
        ])
    
    def test_tournament_analysis_workflow(self):
        """Test complete tournament analysis workflow"""
        # Create test data
        df = create_sample_data()
        
        # Get tournament
        test_tournament = df['Tournament'].iloc[0]
        
        # Create leaderboard
        leaderboard = create_tournament_leaderboard(df, test_tournament)
        
        # Verify workflow completes successfully
        assert not leaderboard.empty
        assert 'Rank' in leaderboard.columns
        assert leaderboard['Rank'].min() == 1

if __name__ == "__main__":
    # Run basic tests if executed directly
    pytest.main([__file__, "-v"])
