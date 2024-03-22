import numpy as np
import zmq
import time

class GameStimulationEncoder:
    """
    Encodes game metadata and actions into stimulation patterns.
    """
    def __init__(self):
        # ZeroMQ setup for publishing stimulation patterns
        self.context = zmq.Context()
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind("tcp://*:5556")  # Bind to port 5556

    def encode_game_metadata(self, metadata):
        """
        Encodes the game metadata, including distances and player's actions, into a packet.
        This function is simplified to demonstrate encoding a few aspects.
        """
        # Encoding distance and player force into the packet
        distance_to_target = int(metadata['distance_to_target']) % 256
        player_force = int(metadata['player_force']) % 256
        
        # Combine encoded data into a single packet (here, just a tuple for simplicity)
        packet = (distance_to_target, player_force)
        return packet

    def create_stimulation_pattern(self, packet):
        """
        Creates an optical stimulation pattern from the encoded packet.
        The pattern's complexity reflects the game state and player actions.
        """
        pattern_size = 256  # Define pattern size
        stimulation_pattern = np.zeros((pattern_size, pattern_size), dtype=np.uint8)

        # Use distance to target for vertical pattern intensity
        distance_intensity = packet[0]
        stimulation_pattern[:, :distance_intensity] = 128  # Half intensity
        
        # Use player force for a horizontal pattern overlay
        force_intensity = packet[1]
        stimulation_pattern[:force_intensity, :] += 127  # Additive intensity to make it stand out
        stimulation_pattern[stimulation_pattern > 255] = 255  # Ensure max intensity isn't exceeded

        return stimulation_pattern

    def publish_stimulation_pattern(self, pattern):
        """
        Publishes the optical stimulation pattern over ZeroMQ.
        """
        # Convert pattern to string or a format suitable for sending
        encoded_pattern = np.array2string(pattern)
        self.publisher.send_string(encoded_pattern)

    def process_game_metadata(self, metadata):
        """
        Processes game metadata, encodes it, and generates stimulation patterns.
        """
        packet = self.encode_game_metadata(metadata)
        pattern = self.create_stimulation_pattern(packet)
        self.publish_stimulation_pattern(pattern)

# Example usage
if __name__ == "__main__":
    encoder = GameStimulationEncoder()
    metadata_example = {
        "distance_to_target": 50,  # Example distance to target
        "player_force": 120,  # Example player force applied
        # Additional metadata fields can be added as needed
    }

    while True:
        encoder.process_game_metadata(metadata_example)
        time.sleep(1)  # Loop with delay for demonstration purposes
