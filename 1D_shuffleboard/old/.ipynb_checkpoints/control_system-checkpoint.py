from neural_interface import NeuralInterface
from game_logic import shuffleboard_game
from game_state import GameState

class ControlSystem:
    def __init__(self, target_distance):
        self.organoid_interface = OrganoidInterface()
        self.game_state = GameState(target_distance)  # Initialize with a target distance

    def play_round(self):
        signal = self.organoid_interface.decode_signals()
        action = self.organoid_interface.encode_game_action(signal)
        result = shuffleboard_game(action, self.game_state.target_distance)
        self.game_state.update_state(action, result)  # Pass action as well
        metadata = self.game_state.generate_metadata()
        self.process_metadata(metadata)

    def process_metadata(self, metadata):
        # Process and handle the metadata
        print(f"Metadata: {metadata}")

# Example usage
control_system = ControlSystem()
control_system.play_round()
