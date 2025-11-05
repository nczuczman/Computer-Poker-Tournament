from engine.game import PokerGame
from engine.player import Player
from engine.brain import Brain
from engine.tournament import TournamentSimulator


if __name__ == "__main__":
    from bots.randomBot import RandomBot
    from bots.firstBot import FirstBot
    from bots.claudeBot import ClaudeBot
    from bots.deepSeekBot import DeepSeekBot
    from bots.chatGptBot import BestBot
    from bots.geminiBot import GeminiBot

    # Import your bot classes here
    # from bots.randomBot import RandomBot
    # from bots.aggressiveBot import AggressiveBot
    # from bots.conservativeBot import ConservativeBot
    
    # Define players (name, brain_instance)
    player_configs = [
        ("Phillip", RandomBot),
        ("Joey", RandomBot),
        ("Noah", FirstBot),
        #("ChatGPT", BestBot),
        ("Gemini", GeminiBot)
    ]
    
    # Create tournament
    tournament = TournamentSimulator(
        player_configs=player_configs,
        starting_stack=2500
    )
    
    # Run tournament
    # Set verbose=True to see individual game details
    # Set verbose=False for fast simulation
    tournament.run_tournament(
        num_games=100,
        verbose=False,
        summary_frequency=5
    )