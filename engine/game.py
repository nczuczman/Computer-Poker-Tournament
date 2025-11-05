from bots.randomBot import RandomBot
from engine.dealer import Dealer
from engine.player import Player
from treys import Card, Evaluator
from engine.brain import Brain

class PokerGame:
    def __init__(self, players, starting_stack=1000, verbose=True):
        self.verbose = verbose
        self.dealer = Dealer()
        self.players = []
        self.round = 0
        self.pot = 0
        self.current_bet = 0
        self.small_blind = 10
        self.big_blind = 20
        self.ante = 0
        self.starting_stack = starting_stack
        self.game_state = {}
        self.button_position = 0
        self.hand_number = 0
        self.current_street = None
        
        # Initialize players
        for player in players:
            self.players.append(player)

    
    def play_game(self):
        """Play hands until only one player has chips"""
        self.hand_number = 0
        
        while self.get_active_player_count() > 1:
            self.hand_number += 1
            if self.verbose:
                print(f"\n{'='*50}")
                print(f"HAND #{self.hand_number}")
                print(f"{'='*50}")
                print(f"Active players: {self.get_active_player_count()}/{len(self.players)}")
            
            # Remove players with no chips
            self.eliminate_broke_players()
            
            if self.get_active_player_count() <= 1:
                break
            
            # Play one hand
            self.play_hand()
            
            # Move button
            self.button_position = (self.button_position + 1) % len(self.players)
            
            # Increase blinds every 10 hands
            if self.hand_number % 10 == 0:
                self.increase_blinds()
        
        # Announce winner
        #self.announce_tournament_winner()
    
    def get_active_player_count(self):
        """Count players with chips remaining"""
        return sum(1 for p in self.players if p.stack > 0)
    
    def eliminate_broke_players(self):
        """Remove players who have no chips"""
        remaining = []
        for player in self.players:
            if player.stack > 0:
                remaining.append(player)
            else:
                if self.verbose:
                    print(f"*** {player.name} has been eliminated! ***\n")
        
        self.players = remaining
        
        # Adjust button position if needed
        if self.button_position >= len(self.players):
            self.button_position = 0
    
    def increase_blinds(self):
        """Increase blind levels"""
        self.small_blind = int(self.small_blind * 1.5)
        self.big_blind = int(self.big_blind * 1.5)
        if self.verbose:
            print(f"\n*** BLINDS INCREASED: {self.small_blind}/{self.big_blind} ***\n")
    
    def announce_tournament_winner(self):
        """Announce the tournament winner"""
        print("\n" + "="*50)
        print("GAME COMPLETE!")
        print("="*50)
        
        if self.players:
            for player in self.players:
                if player.stack > 0:
                    winner = player
                    player.wins += 1
                    break
            print(f"WINNER: {winner.name}")
        else:
            print("No winner (all players eliminated)")
        print("="*50 + "\n")

    def play_hand(self):
        """Play a single hand of poker"""
        # Reset for new hand
        self.dealer = Dealer()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.current_street = None
        
        # Reset all players for new hand
        for player in self.players:
            player.is_active = True
            player.hand = []
            player.current_bet = 0
            player.has_acted = False
        
        # Post blinds
        if not self.post_blinds():
            return
        
        # Deal hole cards
        self.dealer.deal_hole_cards(self.players)
        self.print_game_state()
        
        # Pre-flop betting
        self.current_street = "pre-flop"
        if self.betting_round("Pre-flop"):
            # Deal flop
            self.community_cards += self.dealer.deal_flop()
            self.print_game_state()
            
            self.current_street = "flop"
            if self.betting_round("Flop"):
                # Deal turn
                self.community_cards.append(self.dealer.deal_turn_or_river())
                self.print_game_state()
                
                self.current_street = "turn"
                if self.betting_round("Turn"):
                    # Deal river
                    self.community_cards.append(self.dealer.deal_turn_or_river())
                    self.print_game_state()
                    
                    self.current_street = "river"
                    self.betting_round("River")
        
        # Showdown and distribute pot
        self.showdown()

    def post_blinds(self):
        """Post small and big blinds"""
        if len(self.players) < 2:
            return False
        
        # Determine blind positions
        sb_pos = self.button_position
        bb_pos = (self.button_position + 1) % len(self.players)
        
        # Post small blind
        sb_player = self.players[sb_pos]
        sb_amount = min(self.small_blind, sb_player.stack)
        sb_player.stack -= sb_amount
        sb_player.current_bet = sb_amount
        self.pot += sb_amount
        if self.verbose:
            print(f"{sb_player.name} posts small blind: {sb_amount}")
        
        # Post big blind
        bb_player = self.players[bb_pos]
        bb_amount = min(self.big_blind, bb_player.stack)
        bb_player.stack -= bb_amount
        bb_player.current_bet = bb_amount
        self.pot += bb_amount
        self.current_bet = bb_amount
        if self.verbose:
            print(f"{bb_player.name} posts big blind: {bb_amount}\n")
        
        return True

    def showdown(self):
        """Determine winner(s) and distribute pot"""
        evaluator = Evaluator()
        active_players = [p for p in self.players if p.is_active]

        if not active_players:
            if self.verbose:
                print("No active players remaining!")
            return []
        
        # If only one player remains, they win
        if len(active_players) == 1:
            winner = active_players[0]
            winner.stack += self.pot
            if self.verbose:
                print(f"\n{winner.name} wins {self.pot} chips (all others folded)!\n")
            return [winner]

        # Evaluate each active player's hand
        scores = {}
        for player in active_players:
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

        # Distribute pot (split if tie)
        winnings_per_player = self.pot // len(winners)
        remainder = self.pot % len(winners)
        
        # Print results
        if self.verbose:
            print("="*40)
            print("SHOWDOWN RESULTS")
        for i, player in enumerate(winners):
            hole_str = ' '.join([Card.int_to_pretty_str(c) for c in player.hand])
            hand_class = evaluator.class_to_string(evaluator.get_rank_class(scores[player]))
            winnings = winnings_per_player + (1 if i < remainder else 0)
            player.stack += winnings
            if self.verbose:
                print(f"Winner: {player.name} | Hand: {hole_str} | {hand_class} | Wins: {winnings}")
        if self.verbose:
            print("="*40 + "\n")

        return winners

    def betting_round(self, street_name):
        """
        Handle a complete betting round with player actions.
        Returns True if hand should continue, False if only one player remains.
        """
        if self.verbose:
            print(f"--- {street_name} Betting ---")
        
        # Reset for new betting round
        for player in self.players:
            player.has_acted = False
        
        # Determine action order (left of button, or left of big blind preflop)
        if street_name == "Pre-flop":
            # Action starts left of big blind
            start_pos = (self.button_position + 2) % len(self.players)
        else:
            # Action starts left of button
            start_pos = (self.button_position + 1) % len(self.players)
        
        action_complete = False
        current_aggressor = None  # Track who made the last raise
        
        while not action_complete:
            action_complete = True
            
            for i in range(len(self.players)):
                player_idx = (start_pos + i) % len(self.players)
                player = self.players[player_idx]
                
                # Skip if player is not active or has no chips
                if not player.is_active or player.stack == 0:
                    continue
                
                # Check if this player needs to act
                needs_to_act = (
                    not player.has_acted or 
                    (player.current_bet < self.current_bet and player.stack > 0)
                )
                
                if not needs_to_act:
                    continue
                
                # Player needs to act
                action_complete = False
                
                # Build game state for this player
                game_state = self.build_game_state(player)
                
                # Get action from player
                action_dict = player.brain.get_action(game_state)
                action_type = action_dict.get("action", "fold").lower()
                amount = action_dict.get("amount", 0)
                
                # Process the action
                self.process_action(player, action_type, amount)
                player.has_acted = True
                
                # Track if this was a raise
                if action_type == "raise":
                    current_aggressor = player
                    action_complete = False  # Everyone needs to act again
                    # Reset has_acted for all other active players
                    for p in self.players:
                        if p != player and p.is_active and p.stack > 0:
                            p.has_acted = False
                
                # Check if only one player remains
                active_count = sum(1 for p in self.players if p.is_active)
                if active_count <= 1:
                    if self.verbose:
                        print()
                    return False
            
            # After a full round, check if everyone has acted and matched the bet
            all_matched = True
            for player in self.players:
                if player.is_active and player.stack > 0:
                    if player.current_bet < self.current_bet:
                        all_matched = False
                        break
            
            if all_matched:
                action_complete = True
        
        # Reset current bets for next round
        for player in self.players:
            player.current_bet = 0
        self.current_bet = 0
        if self.verbose:
            print()
        return True

    def process_action(self, player, action_type, amount):
        """Process a player's action"""
        
        if action_type == "fold":
            player.is_active = False
            if self.verbose:
                print(f"{player.name}: Fold")
        
        elif action_type == "check":
            if player.current_bet == self.current_bet:
                if self.verbose:
                    print(f"{player.name}: Check")
            else:
                # Can't check if there's a bet to call - force fold
                if self.verbose:
                    print(f"{player.name}: Attempted to check but must call - Folding")
                player.is_active = False
        
        elif action_type == "call":
            amount_to_call = self.current_bet - player.current_bet
            
            if amount_to_call == 0:
                # Nothing to call, treat as check
                if self.verbose:
                    print(f"{player.name}: Check")
            elif player.stack >= amount_to_call:
                # Normal call
                player.stack -= amount_to_call
                player.current_bet += amount_to_call
                self.pot += amount_to_call
                if self.verbose:
                    print(f"{player.name}: Call {amount_to_call}")
            else:
                # All-in call
                all_in_amount = player.stack
                player.current_bet += all_in_amount
                self.pot += all_in_amount
                player.stack = 0
                if self.verbose:
                    print(f"{player.name}: All-in (call) {all_in_amount}")
        
        elif action_type == "raise":
            amount_to_call = self.current_bet - player.current_bet
            total_bet_amount = amount_to_call + amount
            
            if player.stack >= total_bet_amount:
                # Valid raise
                player.stack -= total_bet_amount
                player.current_bet += total_bet_amount
                self.pot += total_bet_amount
                self.current_bet = player.current_bet
                if self.verbose:
                    print(f"{player.name}: Raise {amount} (total bet: {player.current_bet})")
            elif player.stack > amount_to_call:
                # All-in raise (but not enough for full raise amount)
                all_in_amount = player.stack
                player.current_bet += all_in_amount
                self.pot += all_in_amount
                self.current_bet = max(self.current_bet, player.current_bet)
                player.stack = 0
                if self.verbose:
                    print(f"{player.name}: All-in (raise) {all_in_amount}")
            else:
                # Can't raise, try to call instead
                all_in_amount = player.stack
                player.current_bet += all_in_amount
                self.pot += all_in_amount
                player.stack = 0
                if self.verbose:
                    print(f"{player.name}: All-in (attempted raise, not enough chips) {all_in_amount}")
        
        elif action_type == "bet":
            # Bet (when there's no current bet)
            if self.current_bet == 0:
                if player.stack >= amount:
                    player.stack -= amount
                    player.current_bet = amount
                    self.pot += amount
                    self.current_bet = amount
                    if self.verbose:
                        print(f"{player.name}: Bet {amount}")
                else:
                    # All-in bet
                    all_in_amount = player.stack
                    player.current_bet = all_in_amount
                    self.pot += all_in_amount
                    self.current_bet = all_in_amount
                    player.stack = 0
                    if self.verbose:
                        print(f"{player.name}: All-in (bet) {all_in_amount}")
            else:
                # There's already a bet, treat as raise
                self.process_action(player, "raise", amount)
        
        else:
            # Unknown action, default to fold
            if self.verbose:
                print(f"{player.name}: Unknown action '{action_type}' - Folding")
            player.is_active = False

    def build_game_state(self, current_player):
        """
        Build a comprehensive game state dictionary for a player to make decisions.
        
        Args:
            current_player: The player who needs to make a decision
            
        Returns:
            Dictionary containing all relevant game information
        """
        # Build list of opponent information
        opponents = []
        for player in self.players:
            if player != current_player:
                opponent_info = {
                    "name": player.name,
                    "stack": player.stack,
                    "current_bet": player.current_bet,
                    "is_active": player.is_active,
                    "position": self.players.index(player),
                    "is_all_in": player.stack == 0 and player.is_active
                }
                opponents.append(opponent_info)
        
        # Calculate pot odds
        amount_to_call = self.current_bet - current_player.current_bet
        if amount_to_call > 0:
            pot_odds = amount_to_call / (self.pot + amount_to_call)
        else:
            pot_odds = 0
        
        # Determine valid actions
        valid_actions = self.get_valid_actions(current_player)
        
        # Build the complete game state
        game_state = {
            # Player's own information
            "player": {
                "name": current_player.name,
                "hand": current_player.hand.copy() if current_player.hand else [],
                "stack": current_player.stack,
                "current_bet": current_player.current_bet,
                "position": self.players.index(current_player),
                "is_button": self.players.index(current_player) == self.button_position,
                "is_small_blind": self.players.index(current_player) == self.button_position,
                "is_big_blind": self.players.index(current_player) == (self.button_position + 1) % len(self.players)
            },
            
            # Community cards
            "community_cards": self.community_cards.copy() if self.community_cards else [],
            "num_community_cards": len(self.community_cards),
            
            # Pot information
            "pot": self.pot,
            "current_bet": self.current_bet,
            "amount_to_call": amount_to_call,
            "pot_odds": pot_odds,
            
            # Street information
            "street": self.current_street,
            
            # Blind information
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "ante": self.ante,
            
            # Tournament information
            "hand_number": self.hand_number,
            "button_position": self.button_position,
            
            # Table information
            "num_players": len(self.players),
            "num_active_players": sum(1 for p in self.players if p.is_active),
            "opponents": opponents,
            
            # Valid actions for this player
            "valid_actions": valid_actions,
            
            # Min/max bet amounts
            "min_raise": self.big_blind if self.current_bet == 0 else self.current_bet * 2,
            "max_raise": current_player.stack
        }
        
        return game_state
    
    def get_valid_actions(self, player):
        """
        Determine which actions are valid for a player.
        
        Returns:
            List of valid action strings
        """
        valid = []
        amount_to_call = self.current_bet - player.current_bet
        
        # Can always fold
        valid.append("fold")
        
        # Check if can check
        if amount_to_call == 0:
            valid.append("check")
            valid.append("bet")
        
        # Can call if there's a bet and player has chips
        if amount_to_call > 0 and player.stack > 0:
            valid.append("call")
        
        # Can raise/bet if player has chips beyond the call amount
        if player.stack > amount_to_call:
            if self.current_bet > 0:
                valid.append("raise")
            else:
                valid.append("bet")
        
        return valid

    def print_game_state(self):
        if self.verbose:
            print("="*40)
            print("CURRENT GAME STATE")
            print("="*40)

        if self.community_cards:
            community_str = ' '.join([Card.int_to_pretty_str(c) for c in self.community_cards])
        else:
            community_str = "No community cards yet"
        if self.verbose:
            print(f"Community Cards: {community_str}")
            print(f"Pot Size: {self.pot}")
            print(f"Current Bet: {self.current_bet}\n")

        for player in self.players:
            hole_str = ' '.join([Card.int_to_pretty_str(c) for c in player.hand]) if player.hand else "No cards yet"
            status = "IN HAND" if player.is_active else "FOLDED"
            if self.verbose:
                print(f"{player.name}: {hole_str} | Stack: {player.stack} | Current Bet: {player.current_bet} | Status: {status}")
        if self.verbose:
            print("="*40 + "\n")