from engine.game import PokerGame
from engine.player import Player
from engine.brain import Brain
from bots.randomBot import RandomBot
from collections import defaultdict
import time

class TournamentSimulator:
    def __init__(self, player_configs, starting_stack=3000):
        """
        Initialize the tournament simulator.
        
        Args:
            player_configs: List of tuples (name, brain_instance)
            starting_stack: Starting chips for each player
        """
        self.player_configs = player_configs
        self.starting_stack = starting_stack
        self.stats = defaultdict(lambda: {
            'wins': 0,
            'games_played': 0,
            'win_rate': 0.0
        })
    
    def create_players(self):
        """Create fresh player instances for a new game."""
        players = []
        for name, brain in self.player_configs:
            player = Player(name, brain, self.starting_stack)
            players.append(player)
        return players
    
    def run_tournament(self, num_games, verbose=False, summary_frequency=10):
        """
        Run multiple poker games and track statistics.
        
        Args:
            num_games: Number of games to simulate
            verbose: Whether to print game details (False for faster simulation)
            summary_frequency: Print summary every N games
        """
        print(f"\n{'='*60}")
        print(f"STARTING TOURNAMENT: {num_games} GAMES")
        print(f"{'='*60}")
        print(f"Players: {', '.join([name for name, _ in self.player_configs])}")
        print(f"Starting Stack: {self.starting_stack}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        for game_num in range(1, num_games + 1):
            # Create fresh players for each game
            players = self.create_players()
            
            # Run the game
            game = PokerGame(players, starting_stack=self.starting_stack, verbose=verbose)
            game.play_game()
            
            # Update statistics
            for player in players:
                self.stats[player.name]['games_played'] += 1
                if player.stack > 0:  # Winner is the player with chips remaining
                    self.stats[player.name]['wins'] += 1
            
            # Print periodic summary
            if game_num % summary_frequency == 0 or game_num == num_games:
                self.print_summary(game_num, start_time)
        
        elapsed_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"TOURNAMENT COMPLETE!")
        print(f"Total Time: {elapsed_time:.2f} seconds")
        print(f"Games per Second: {num_games/elapsed_time:.2f}")
        print(f"{'='*60}\n")
        
        self.print_final_results()
    
    def print_summary(self, games_completed, start_time):
        """Print a summary of current standings."""
        print(f"\n{'='*60}")
        print(f"SUMMARY AFTER {games_completed} GAMES")
        print(f"{'='*60}")
        
        # Calculate win rates
        for name in self.stats:
            games = self.stats[name]['games_played']
            wins = self.stats[name]['wins']
            self.stats[name]['win_rate'] = (wins / games * 100) if games > 0 else 0
        
        # Sort by win rate
        sorted_players = sorted(
            self.stats.items(), 
            key=lambda x: x[1]['win_rate'], 
            reverse=True
        )
        
        # Print standings
        print(f"{'Rank':<6} {'Player':<20} {'Wins':<10} {'Games':<10} {'Win Rate':<10}")
        print("-" * 60)
        
        for rank, (name, stats) in enumerate(sorted_players, 1):
            print(f"{rank:<6} {name:<20} {stats['wins']:<10} {stats['games_played']:<10} {stats['win_rate']:.2f}%")
        
        elapsed = time.time() - start_time
        print(f"\nElapsed Time: {elapsed:.2f}s | Games/sec: {games_completed/elapsed:.2f}")
        print(f"{'='*60}\n")
    
    def print_final_results(self):
        """Print detailed final tournament results."""
        print(f"\n{'='*60}")
        print(f"FINAL TOURNAMENT RESULTS")
        print(f"{'='*60}\n")
        
        # Sort by win rate
        sorted_players = sorted(
            self.stats.items(), 
            key=lambda x: x[1]['win_rate'], 
            reverse=True
        )
        
        # Print detailed results
        for rank, (name, stats) in enumerate(sorted_players, 1):
            print(f"Rank #{rank}: {name}")
            print(f"  Wins: {stats['wins']}/{stats['games_played']}")
            print(f"  Win Rate: {stats['win_rate']:.2f}%")
            print()
        
        # Determine winner
        winner_name = sorted_players[0][0]
        winner_stats = sorted_players[0][1]
        
        print(f"{'='*60}")
        print(f"TOURNAMENT CHAMPION: {winner_name}")
        print(f"Win Rate: {winner_stats['win_rate']:.2f}%")
        print(f"{'='*60}\n")


