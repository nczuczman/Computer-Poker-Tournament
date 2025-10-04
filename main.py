from engine.game import PokerGame
from engine.player import Player
from engine.brain import Brain

if __name__ == "__main__":
    players = [Player("Player 1", Brain("Player 1")), Player("Player 2", Brain("Player 2"))]
    game = PokerGame()
    game.players = players
    game.play_hand()