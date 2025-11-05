from engine.brain import Brain
import random
import json
from treys import Card, Evaluator, Deck

class GeminiBot(Brain):
    """
    A poker bot that uses Monte Carlo simulation to estimate hand equity 
    and make decisions based on pot odds and value.
    """
    def __init__(self):
        super().__init__()
        self.evaluator = Evaluator()

    def calculate_equity(self, my_hand, board, num_opponents, num_sims=300):
        """
        Runs a Monte Carlo simulation to estimate win/tie equity.
        """
        # If no opponents, we have 100% equity
        if num_opponents == 0:
            return 1.0 

        known_cards = my_hand + board
        
        # Get a full list of 52 card integers
        full_deck = Deck().cards 
        
        # Remove known cards from the deck
        remaining_deck = [c for c in full_deck if c not in known_cards]
        
        wins = 0
        ties = 0
        cards_to_come = 5 - len(board)
        
        # Ensure there are enough cards left to run a simulation
        if len(remaining_deck) < (num_opponents * 2 + cards_to_come):
            return 0.0 # Not enough cards, something is wrong

        for _ in range(num_sims):
            # Shuffle a copy of the remaining deck for this simulation
            sim_deck = list(remaining_deck)
            random.shuffle(sim_deck)
            
            # Deal the rest of the board
            sim_board = board + sim_deck[:cards_to_come]
            deck_ptr = cards_to_come
            
            # Deal hands to all opponents
            opponent_hands = []
            for _ in range(num_opponents):
                opp_hand = sim_deck[deck_ptr : deck_ptr + 2]
                opponent_hands.append(opp_hand)
                deck_ptr += 2
                
            # Evaluate our hand
            my_score = self.evaluator.evaluate(sim_board, my_hand)
            
            # Evaluate all opponent hands and find the best one
            best_opp_score = 999999 # Lower score is better in 'treys'
            for opp_hand in opponent_hands:
                opp_score = self.evaluator.evaluate(sim_board, opp_hand)
                if opp_score < best_opp_score:
                    best_opp_score = opp_score
                    
            # Compare scores
            if my_score < best_opp_score:
                wins += 1
            elif my_score == best_opp_score:
                ties += 1
                
        # Return the win/tie equity
        return (wins + ties / 2) / num_sims

    def get_action(self, game_state):
        # --- 1. Parse Game State ---
        valid_actions = game_state["valid_actions"]
        player = game_state["player"]
        hand = player["hand"]
        stack = player["stack"]
        board = game_state.get("community_cards", [])
        street = game_state.get("street", "pre-flop")
        pot = game_state["pot"]
        amount_to_call = game_state["amount_to_call"]
        current_bet = game_state["current_bet"]
        min_raise = game_state.get("min_raise", 0)
        max_raise = game_state.get("max_raise", stack)
        big_blind = game_state["big_blind"]
        num_active_players = game_state["num_active_players"]
        
        # Opponents are active players minus ourselves
        num_opponents = num_active_players - 1

        # If we are the only one left, just check (shouldn't happen often)
        if num_opponents <= 0:
            return {"action": "check"} if "check" in valid_actions else {"action": "call"}

        # --- 2. Calculate Equity ---
        # Use fewer sims pre-flop (slower) and more post-flop (faster)
        num_sims = 300 if street == "pre-flop" else 500
        win_equity = self.calculate_equity(hand, board, num_opponents, num_sims)
        
        # Get pot odds (equity needed to call) from game state
        pot_odds = game_state.get("pot_odds", 0)
        if amount_to_call == 0:
            pot_odds = 0.0 # We need 0% equity to check

        # --- 3. Pre-flop Logic ---
        if street.lower() == "pre-flop":
            # Dynamic thresholds based on number of players
            # "Average" equity is 1 / num_active_players
            equity_threshold_raise = (1.0 / num_active_players) + 0.20 # Raise w/ top ~20%
            equity_threshold_call = (1.0 / num_active_players) + 0.10  # Call w/ top ~30%
            
            # A. Raise/Re-raise with strong hands
            if win_equity > equity_threshold_raise:
                # Standard open is 3x BB. Standard 3-bet is 3x current bet.
                raise_amount = max(big_blind * 3, current_bet * 3)
                raise_amount = max(raise_amount, min_raise) # Must be at least min_raise
                raise_amount = min(raise_amount, max_raise) # Clamp to our stack
                
                if "raise" in valid_actions:
                    return {"action": "raise", "amount": int(raise_amount)}

            # B. Call/Check with playable hands
            if win_equity > equity_threshold_call:
                if "call" in valid_actions and amount_to_call > 0:
                    # Only call if we are getting the right price
                    if win_equity > pot_odds:
                        return {"action": "call"}
                if "check" in valid_actions: # e.g., in Big Blind
                    return {"action": "check"}

            # C. Fold/Check weak hands
            if "check" in valid_actions: # Always check for free
                return {"action": "check"}
            return {"action": "fold"}

        # --- 4. Post-flop Logic ---
        
        # A. Monsters (e.g., >85% equity) - Bet/Raise for max value
        if win_equity > 0.85:
            if "raise" in valid_actions:
                # Raise pot-sized
                raise_amount = pot + amount_to_call 
                raise_amount = max(min_raise, raise_amount)
                raise_amount = min(max_raise, raise_amount)
                return {"action": "raise", "amount": int(raise_amount)}
            if "bet" in valid_actions:
                # Bet 3/4 pot
                bet_amount = pot * 0.75
                bet_amount = max(big_blind, bet_amount) # Bet at least 1 BB
                bet_amount = min(max_raise, bet_amount)
                return {"action": "bet", "amount": int(bet_amount)}

        # B. Strong Hands (e.g., >65% equity) - Bet for value, call raises
        if win_equity > 0.65:
            if "bet" in valid_actions:
                # Bet 1/2 pot
                bet_amount = pot * 0.5
                bet_amount = max(big_blind, bet_amount)
                bet_amount = min(max_raise, bet_amount)
                return {"action": "bet", "amount": int(bet_amount)}

        # C. Have Odds (equity > pot_odds) - Call or check
        # This covers draws, medium pairs, etc.
        if win_equity > pot_odds:
            if "call" in valid_actions:
                return {"action": "call"}
            if "check" in valid_actions:
                return {"action": "check"}
                
        # D. No Odds - Check if free, otherwise fold
        if "check" in valid_actions:
            return {"action": "check"}
        
        return {"action": "fold"}