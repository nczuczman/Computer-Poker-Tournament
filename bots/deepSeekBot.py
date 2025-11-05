from engine.brain import Brain
import time
import random
import json
from treys import Card, Evaluator, Deck
import math

class DeepSeekBot(Brain):
    def __init__(self):
        super().__init__()
        self.evaluator = Evaluator()
        self.hand_history = []
        self.opponent_stats = {}
        self.last_action = None
        
    def get_action(self, game_state):
        valid_actions = game_state["valid_actions"]
        player = game_state["player"]
        hand = player["hand"]
        board = game_state.get("community_cards", [])
        street = game_state.get("street", "")
        
        # Update opponent statistics
        self._update_opponent_stats(game_state)
        
        # Calculate comprehensive hand strength with Monte Carlo
        hand_strength, hand_equity = self._calculate_hand_strength(hand, board, game_state)
        
        # Calculate position advantage
        position_advantage = self._calculate_position_advantage(game_state)
        
        # Calculate dynamic aggression factor
        aggression = self._calculate_aggression_factor(game_state, hand_strength)
        
        # Get opponent tendencies
        opponent_tendencies = self._get_opponent_tendencies(game_state)
        
        # --- PRE-FLOP STRATEGY ---
        if street.lower() == "pre-flop":
            action = self._pre_flop_strategy(game_state, hand_strength, position_advantage, hand_equity)
        
        # --- POST-FLOP STRATEGY ---
        else:
            action = self._post_flop_strategy(game_state, hand_strength, position_advantage, 
                                            aggression, opponent_tendencies, hand_equity)
        
        self.last_action = action
        return action
    
    def _calculate_hand_strength(self, hand, board, game_state):
        """Calculate hand strength with iterative Monte Carlo simulation"""
        if len(board) == 0:
            equity = self._evaluate_pre_flop_hand(hand)
            return equity, equity
        
        # Use Monte Carlo for post-flop equity calculation
        equity = self._monte_carlo_equity(hand, board, game_state["num_active_players"] - 1, 200)
        
        # Calculate current hand strength
        current_score = self.evaluator.evaluate(board, hand)
        current_strength = 1 - (current_score / 7462.0)
        
        # For drawing hands, weight potential higher
        if current_strength < 0.7 and equity > current_strength + 0.2:
            # Drawing hand with good potential
            combined_strength = 0.4 * current_strength + 0.6 * equity
        else:
            # Made hand
            combined_strength = 0.7 * current_strength + 0.3 * equity
            
        return min(1.0, combined_strength), equity
    
    def _monte_carlo_equity(self, hand, board, num_opponents, iterations=200):
        """Iterative Monte Carlo equity calculation"""
        if len(board) == 5:  # River - no more cards to come
            return self._evaluate_river_equity(hand, board, num_opponents, iterations)
        
        wins = 0
        total_trials = 0
        
        for _ in range(iterations):
            deck = Deck()
            
            # Remove known cards
            known_cards = hand + board
            for card in known_cards:
                if card in deck.cards:
                    deck.cards.remove(card)
            
            # Deal remaining board cards
            remaining_cards = 5 - len(board)
            if remaining_cards > 0:
                try:
                    new_board_cards = deck.draw(remaining_cards)
                    test_board = board + new_board_cards
                except:
                    # Fallback if draw fails
                    test_board = board
            else:
                test_board = board
            
            # Simulate opponents' hands and determine winner
            trial_wins = self._simulate_showdown(hand, test_board, num_opponents, deck)
            wins += trial_wins
            total_trials += num_opponents
            
        return wins / total_trials if total_trials > 0 else 0.5
    
    def _simulate_showdown(self, my_hand, board, num_opponents, deck):
        """Simulate a single showdown iteration"""
        if len(deck.cards) < num_opponents * 2:
            return 0.5  # Not enough cards, return neutral equity
            
        my_score = self.evaluator.evaluate(board, my_hand)
        wins = 0
        
        for i in range(num_opponents):
            if len(deck.cards) >= 2:
                opp_hand = deck.draw(2)
                opp_score = self.evaluator.evaluate(board, opp_hand)
                
                if my_score < opp_score:
                    wins += 1  # I win
                elif my_score == opp_score:
                    wins += 0.5  # Tie
                # else: opp wins (0 points)
        
        return wins
    
    def _evaluate_river_equity(self, hand, board, num_opponents, iterations=100):
        """Evaluate equity on river with random opponent hands"""
        wins = 0
        total = 0
        
        for _ in range(iterations):
            deck = Deck()
            known_cards = hand + board
            for card in known_cards:
                if card in deck.cards:
                    deck.cards.remove(card)
            
            my_score = self.evaluator.evaluate(board, hand)
            round_wins = 0
            
            for i in range(num_opponents):
                if len(deck.cards) >= 2:
                    opp_hand = deck.draw(2)
                    opp_score = self.evaluator.evaluate(board, opp_hand)
                    
                    if my_score < opp_score:
                        round_wins += 1
                    elif my_score == opp_score:
                        round_wins += 0.5
            
            wins += round_wins
            total += num_opponents
            
        return wins / total if total > 0 else 0.5
    
    def _evaluate_pre_flop_hand(self, hand):
        """Advanced pre-flop hand evaluation with card removal effects"""
        card1 = hand[0]
        card2 = hand[1]
        
        rank1 = Card.get_rank_int(card1)
        rank2 = Card.get_rank_int(card2)
        suited = Card.get_suit_int(card1) == Card.get_suit_int(card2)
        
        # Premium hands
        if rank1 == rank2:  # Pocket pairs
            if rank1 >= 12:  # AA
                return 0.98
            elif rank1 >= 10:  # KK, QQ
                return 0.95
            elif rank1 >= 8:  # JJ, TT
                return 0.85
            elif rank1 >= 6:  # 99, 88, 77
                return 0.70
            else:  # 22-66
                return 0.55
                
        # Ace hands
        if rank1 == 12 or rank2 == 12:
            other_rank = rank2 if rank1 == 12 else rank1
            if suited:
                if other_rank >= 10:  # AKs, AQs
                    return 0.92
                elif other_rank >= 8:  # AJs, ATs
                    return 0.80
                else:  # A9s-A2s
                    return 0.65
            else:
                if other_rank >= 10:  # AKo, AQo
                    return 0.88
                elif other_rank >= 8:  # AJo, ATo
                    return 0.70
                else:  # A9o-A2o
                    return 0.50
        
        # Broadway cards
        if rank1 >= 8 and rank2 >= 8:
            rank_diff = abs(rank1 - rank2)
            if suited:
                if rank_diff == 1:  # KQs, QJs, JTs
                    return 0.75
                elif rank_diff == 2:  # KJs, QTs
                    return 0.65
                else:  # KTs, Q9s, etc.
                    return 0.55
            else:
                if rank_diff == 1:  # KQo, QJo, JTo
                    return 0.65
                else:
                    return 0.50
        
        # Suited connectors
        rank_diff = abs(rank1 - rank2)
        if suited and rank_diff <= 2:
            if max(rank1, rank2) >= 9:  # T9s, 98s
                return 0.60
            elif max(rank1, rank2) >= 7:  # 87s, 76s
                return 0.50
            else:  # 65s, 54s, etc.
                return 0.40
                
        # Pocket pairs 22-66 already handled, so remaining are weak hands
        return 0.25
    
    def _calculate_position_advantage(self, game_state):
        """Calculate position advantage with table dynamics"""
        player_pos = game_state["player"]["position"]
        button_pos = game_state["button_position"]
        num_players = game_state["num_players"]
        
        positions_after_button = (player_pos - button_pos) % num_players
        
        # More nuanced position weights
        if positions_after_button == 0:  # Button
            return 1.0
        elif positions_after_button == 1:  # Cutoff
            return 0.85
        elif positions_after_button == 2:  # Hijack
            return 0.70
        elif positions_after_button == 3:  # Lojack
            return 0.55
        elif positions_after_button <= num_players // 2:
            return 0.35  # Middle positions
        else:
            return 0.15  # Early positions
    
    def _calculate_aggression_factor(self, game_state, hand_strength):
        """Dynamic aggression based on game state and hand strength"""
        aggression = 0.5
        
        # Stack size adjustments
        stack = game_state["player"]["stack"]
        big_blind = game_state["big_blind"]
        bb_ratio = stack / big_blind
        
        if bb_ratio < 15:  # Short stack - push or fold
            aggression += 0.3
        elif bb_ratio > 80:  # Deep stack - more speculative
            aggression += 0.2
        
        # Table dynamics
        num_active = game_state["num_active_players"]
        if num_active <= 2:
            aggression += 0.4  # Very aggressive heads-up
        elif num_active <= 4:
            aggression += 0.2  # Aggressive short-handed
        
        # Hand strength influence
        aggression += (hand_strength - 0.5) * 0.3
        
        # Position influence
        position_adv = self._calculate_position_advantage(game_state)
        aggression += (position_adv - 0.5) * 0.2
        
        return max(0.1, min(0.95, aggression))
    
    def _update_opponent_stats(self, game_state):
        """Track opponent statistics for player profiling"""
        for opp in game_state["opponents"]:
            name = opp["name"]
            if name not in self.opponent_stats:
                self.opponent_stats[name] = {
                    "hands_observed": 0,
                    "preflop_raises": 0,
                    "postflop_aggression": 0,
                    "fold_to_cbet": 0,
                    "cbet_opportunities": 0
                }
    
    def _get_opponent_tendencies(self, game_state):
        """Calculate opponent tendencies for adaptive play"""
        if not self.opponent_stats:
            return {
                "avg_aggression": 0.5,
                "fold_frequency": 0.3,
                "tightness": 0.5
            }
        
        total_aggression = 0
        total_fold_freq = 0
        count = len(self.opponent_stats)
        
        for stats in self.opponent_stats.values():
            total_aggression += stats.get("postflop_aggression", 0.5)
            if stats.get("cbet_opportunities", 0) > 0:
                total_fold_freq += stats.get("fold_to_cbet", 0) / stats.get("cbet_opportunities", 1)
        
        return {
            "avg_aggression": total_aggression / count,
            "fold_frequency": total_fold_freq / count if count > 0 else 0.3,
            "tightness": 0.6  # Default to slightly tight
        }
    
    def _pre_flop_strategy(self, game_state, hand_strength, position_advantage, equity):
        """Comprehensive pre-flop strategy with gap concept"""
        valid_actions = game_state["valid_actions"]
        amount_to_call = game_state["amount_to_call"]
        big_blind = game_state["big_blind"]
        stack = game_state["player"]["stack"]
        pot = game_state["pot"]
        
        # Adjust for position and previous action
        adjusted_strength = hand_strength * (0.6 + 0.4 * position_advantage)
        
        # Calculate pot odds
        pot_odds = amount_to_call / (pot + amount_to_call) if amount_to_call > 0 else 0
        
        # Premium hands: always raise/3-bet
        if adjusted_strength > 0.90:
            if "raise" in valid_actions:
                raise_size = min(stack, max(game_state["min_raise"], big_blind * 3))
                return {"action": "raise", "amount": raise_size}
            elif "call" in valid_actions:
                return {"action": "call"}
        
        # Strong raising hands
        if adjusted_strength > 0.75:
            if position_advantage > 0.4 and "raise" in valid_actions:
                raise_size = min(stack, max(game_state["min_raise"], big_blind * 2.5))
                return {"action": "raise", "amount": raise_size}
            elif "call" in valid_actions and amount_to_call <= big_blind * 2:
                return {"action": "call"}
        
        # Speculative hands with good implied odds
        if adjusted_strength > 0.45:
            # Good pot odds or late position
            if pot_odds < 0.25 or position_advantage > 0.7:
                if "call" in valid_actions and amount_to_call <= big_blind * 3:
                    return {"action": "call"}
        
        # Blind defense
        if (game_state["player"]["is_small_blind"] or game_state["player"]["is_big_blind"]):
            if amount_to_call <= big_blind and "call" in valid_actions:
                return {"action": "call"}
            elif "check" in valid_actions:
                return {"action": "check"}
        
        # Default to fold for weak hands
        if "fold" in valid_actions:
            return {"action": "fold"}
        elif "check" in valid_actions:
            return {"action": "check"}
        else:
            return {"action": "fold"}
    
    def _post_flop_strategy(self, game_state, hand_strength, position_advantage, 
                          aggression, opponent_tendencies, equity):
        """Advanced post-flop strategy with balanced play"""
        valid_actions = game_state["valid_actions"]
        street = game_state["street"]
        amount_to_call = game_state["amount_to_call"]
        pot = game_state["pot"]
        stack = game_state["player"]["stack"]
        
        # Calculate pot odds and implied odds
        pot_odds = amount_to_call / (pot + amount_to_call) if amount_to_call > 0 else 0
        
        # Adjust strategy based on opponent tendencies
        opp_aggression = opponent_tendencies["avg_aggression"]
        opp_fold_freq = opponent_tendencies["fold_frequency"]
        
        # Very strong hands (top 5%)
        if hand_strength > 0.95:
            # Value bet heavily
            if "bet" in valid_actions:
                # Size up against calling stations, down against nits
                bet_size = min(stack, int(pot * (0.6 + 0.2 * (1 - opp_fold_freq))))
                return {"action": "bet", "amount": bet_size}
            elif "raise" in valid_actions:
                raise_size = min(stack, int(game_state["min_raise"] * (1.5 + opp_aggression)))
                return {"action": "raise", "amount": raise_size}
        
        # Strong value hands (top 15%)
        elif hand_strength > 0.85:
            if "bet" in valid_actions:
                bet_size = min(stack, int(pot * 0.5))
                return {"action": "bet", "amount": bet_size}
            elif "raise" in valid_actions and amount_to_call <= pot * 0.25:
                return {"action": "raise", "amount": min(stack, game_state["min_raise"] * 2)}
            elif "call" in valid_actions and pot_odds < 0.2:
                return {"action": "call"}
        
        # Medium strength with good equity
        elif hand_strength > 0.65 or equity > 0.5:
            # Check-call or bet for protection
            if amount_to_call == 0 and "check" in valid_actions:
                return {"action": "check"}
            elif "call" in valid_actions and pot_odds < 0.25:
                return {"action": "call"}
            elif "bet" in valid_actions and position_advantage > 0.6:
                # Bluff/semi-bluff with equity
                if random.random() < aggression * 0.4:
                    bet_size = min(stack, int(pot * 0.4))
                    return {"action": "bet", "amount": bet_size}
        
        # Drawing hands with good odds
        elif equity > 0.3:
            if pot_odds < 0.15:  # Good direct odds
                if "call" in valid_actions:
                    return {"action": "call"}
            elif pot_odds < 0.25 and position_advantage > 0.7:  # Good implied odds
                if "call" in valid_actions:
                    return {"action": "call"}
            elif "check" in valid_actions:
                return {"action": "check"}
        
        # Weak hands - fold without good odds
        if pot_odds > 0.33:  # Poor pot odds
            if "fold" in valid_actions:
                return {"action": "fold"}
        elif "check" in valid_actions:
            return {"action": "check"}
        
        # Final fallback
        if "check" in valid_actions:
            return {"action": "check"}
        elif "call" in valid_actions and amount_to_call == 0:
            return {"action": "call"}
        elif "fold" in valid_actions:
            return {"action": "fold"}
        else:
            return {"action": "check"}