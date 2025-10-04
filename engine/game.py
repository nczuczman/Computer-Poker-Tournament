from engine.dealer import Dealer
from engine.player import Player
from treys import Card, Evaluator

class PokerGame:
    def __init__(self):
        self.dealer = Dealer()
        self.players = []
        self.round = 0
        self.pot = 0
        self.blinds = 10
        self.small_blind = 10
        self.big_blind = 20
        self.ante = 0
        self.starting_stack = 1000
        self.game_state = None

    def play_hand(self):
        self.dealer = Dealer()
        self.community_cards = []
        self.pot = 0

        #Deal hole cards
        self.dealer.deal_hole_cards(self.players)
        self.print_game_state()

        #pre-flop betting
        self.betting_round()

        #deal flop
        self.community_cards += self.dealer.deal_flop()
        self.print_game_state()
        #flop betting
        self.betting_round()

        #deal turn
        self.community_cards.append(self.dealer.deal_turn_or_river())
        self.print_game_state()
        #turn betting
        self.betting_round()

        #deal river
        self.community_cards.append(self.dealer.deal_turn_or_river())
        self.print_game_state()
        self.betting_round()

        self.showdown()


    def showdown(self):
        evaluator = Evaluator()
        active_players = [p for p in self.players if p.is_active]

        if not active_players:
            print("No active players remaining!")
            return []

        # Evaluate each active player's hand
        scores = {}
        for player in active_players:
            # Ensure player has cards
            if not player.hand:
                continue
            hole = player.hand
            board = self.community_cards
            score = evaluator.evaluate(board, hole)
            scores[player] = score

        # Find the lowest score (best hand in Treys)
        best_score = min(scores.values())

        # Find all players with that score (handle ties)
        winners = [player for player, score in scores.items() if score == best_score]

        # Print results nicely
        print("="*40)
        print("SHOWDOWN RESULTS")
        for player in winners:
            hole_str = ' '.join([Card.int_to_pretty_str(c) for c in player.hand])
            hand_class = evaluator.class_to_string(evaluator.get_rank_class(scores[player]))
            print(f"Winner: {player.name} | Hand: {hole_str} | {hand_class}")
        print("="*40 + "\n")

        return winners


    def betting_round(self):
        for player in self.players:
            player.action  = player.brain.get_action(self.game_state)
            print(f"{player.name} {player.action}")
            


    def print_game_state(self):
   
        print("="*40)
        print("CURRENT GAME STATE")
        print("="*40)

        if self.community_cards:
            community_str = ' '.join([Card.int_to_pretty_str(c) for c in self.community_cards])
        else:
            community_str = "No community cards yet"
        print(f"Community Cards: {community_str}")
        print(f"Pot Size: {self.pot}\n")

        
        for player in self.players:
            hole_str = ' '.join([Card.int_to_pretty_str(c) for c in player.hand]) if player.hand else "No cards yet"
            status = "IN HAND" if player.is_active else "FOLDED"
            print(f"{player.name}: {hole_str} | Stack: {player.stack} | Status: {status}")

        print("="*40 + "\n")


    